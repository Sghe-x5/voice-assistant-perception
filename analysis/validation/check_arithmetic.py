"""Independent source-to-result audit; does not import or execute project analyses."""
from pathlib import Path
import hashlib, json
import numpy as np
import pandas as pd
from scipy.stats import norm, t as student_t
from sklearn.model_selection import KFold, GroupKFold, GridSearchCV
from sklearn.pipeline import make_pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import Ridge

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
ITEMS = [f'intelligence_{j}' for j in range(1, 6)] + [f'Credibility_{j}' for j in range(1, 6)]
SEED = 20261104

def load():
    frames = []
    for i in (1, 2):
        z = pd.read_csv(ROOT / f'data/raw/beyond_voice/experiment{i}.sav.csv')
        z['participant'] = [f'E{i}_{j:03d}' for j in range(len(z))]
        z['study'] = i
        z['partner'] = z.Social_Role.eq('Partner').astype(int)
        z['assertive'] = z.Speech_Style.eq('Assertive').astype(int) if i == 1 else 1
        z['first'] = z.priming.eq(1) if i == 1 else z.MP1final.eq(1)
        z['all_checks'] = z['first'] if i == 1 else z.MP1final.eq(1) & z.MP2final.eq(1)
        z['age_years'] = 2024 - z.age
        z['female'] = z.gen.eq(1).astype(int)
        z['diverse_gender'] = z.gen.eq(2).astype(int)
        z['owner'] = z.own.eq(1).astype(int)
        z['information_search'] = z[[f'frequency_use__{j}' for j in range(1, 6)]].mean(axis=1)
        assert np.allclose(z.intelligence, z[ITEMS[:5]].mean(axis=1))
        assert np.allclose(z.credibility, z[ITEMS[5:]].mean(axis=1))
        frames.append(z)
    return pd.concat(frames, ignore_index=True)

def htmt(r):
    tri = np.triu_indices(5, 1)
    return abs(r[:5, 5:]).mean() / np.sqrt(abs(r[:5, :5][tri]).mean() * abs(r[5:, 5:][tri]).mean())

def metrics(y, p):
    return dict(mae=float(np.mean(abs(y-p))), r2=float(1-np.sum((y-p)**2)/np.sum((y-y.mean())**2)))

def train(tr, te, grouped=False):
    user = ['age_years','female','diverse_gender','owner','information_search']
    cols = {'design_user':['partner','assertive']+user, 'credibility_only':['credibility']}
    folds = list(GroupKFold(5).split(tr, groups=tr.participant)) if grouped else list(KFold(5, shuffle=True, random_state=SEED).split(tr))
    if grouped:
        assert all(set(tr.iloc[a].participant).isdisjoint(tr.iloc[b].participant) for a,b in folds)
    p = {'mean': np.repeat(tr.intelligence.mean(), len(te))}
    alphas = {}
    for name, fields in cols.items():
        fit = GridSearchCV(make_pipeline(SimpleImputer(strategy='median',add_indicator=True),StandardScaler(),Ridge()),
                           {'ridge__alpha':[.1,1.,10.,100.,1000.]}, cv=folds, scoring='neg_mean_absolute_error', error_score='raise')
        fit.fit(tr[fields], tr.intelligence)
        p[name] = fit.predict(te[fields])
        alphas[name] = fit.best_params_['ridge__alpha']
    return p, alphas

def main():
    d = load(); checks = {}; rows = []; max_err = 0.
    stored = pd.read_csv(ROOT/'results/voice_measurement.csv').set_index('sample')
    fits = pd.read_csv(ROOT/'results/voice_cfa.csv')
    # Reconstruct implied covariance from parameter tables; directly evaluate ML discrepancy.
    for label,z in [('E1',d[d.study==1]),('E2',d[d.study==2]),('pooled',d)]:
        x = z[ITEMS].to_numpy(); r = np.corrcoef(x.T)
        assert np.isclose(htmt(r), stored.loc[label,'htmt'], atol=1e-12)
        for model in ['one_factor','two_factor']:
            p = pd.read_csv(ROOT/f'results/voice_cfa_{label}_{model}_parameters.csv')
            factors = ['G'] if model == 'one_factor' else ['Intelligence','Credibility']
            L = np.zeros((10,len(factors))); P = np.zeros((len(factors),len(factors))); T = np.zeros((10,10))
            for _,v in p.iterrows():
                if v.op == '~': L[ITEMS.index(v.lval),factors.index(v.rval)] = v.Estimate
                elif v.lval in factors:
                    a,b = factors.index(v.lval),factors.index(v.rval); P[a,b]=P[b,a]=v.Estimate
                else: T[ITEMS.index(v.lval),ITEMS.index(v.rval)] = v.Estimate
            S = np.cov(x.T,ddof=0); Sigma = L@P@L.T+T
            value = len(z)*(np.linalg.slogdet(Sigma)[1]+np.trace(np.linalg.solve(Sigma,S))-np.linalg.slogdet(S)[1]-10)
            expected = fits[(fits['sample']==label)&(fits.model==model)].iloc[0].chi2
            max_err = max(max_err, abs(value-expected))
            assert abs(value-expected)<1e-8
            rows.append({'sample':label,'model':model,'chi2_independent':value,'max_residual_correlation':float(abs((S-Sigma)/np.sqrt(np.outer(np.diag(S),np.diag(S))))[np.triu_indices(10,1)].max())})
    checks['cfa_max_chi2_error'] = max_err
    pd.DataFrame(rows).to_csv(OUT/'cfa_arithmetic.csv',index=False)
    # OLS and HC3 from matrix identities, without statsmodels.
    es = pd.read_csv(ROOT/'results/voice_effects.csv'); errors=[]
    for _,v in es.iterrows():
        z=d if v['sample']=='pooled' else d[d.study==int(v['sample'][1])]
        if v.selection != 'all-released': z=z[z['first' if v.selection=='first/only-MC-pass' else 'all_checks']]
        cols=[np.ones(len(z)),z.partner.to_numpy()]
        if z.study.nunique()>1: cols += [(z.study==2).to_numpy().astype(float)]
        if z.assertive.nunique()>1: cols += [z.assertive.to_numpy()]
        X=np.column_stack(cols); y=z[v.outcome].to_numpy(); inv=np.linalg.inv(X.T@X); beta=inv@X.T@y
        residual=y-X@beta; hat=np.sum((X@inv)*X,axis=1)
        cov=inv@((X.T*(residual/(1-hat))**2)@X)@inv
        se=np.sqrt(cov[1,1]); ci=beta[1]+np.array([-1,1])*norm.ppf(.975)*se
        errors += [abs(beta[1]-v.estimate),abs(se-v.se),abs(ci[0]-v.ci_low),abs(ci[1]-v.ci_high)]
    checks['selection_max_coefficient_se_ci_error']=float(max(errors)); assert max(errors)<1e-10
    checks['selection_counts']={'full':len(d),'first':int(d['first'].sum()),'all':int(d.all_checks.sum())}
    predictions=pd.read_csv(ROOT/'results/voice_predictions.csv'); draws=pd.read_csv(ROOT/'results/voice_retraining_bootstrap_draws.csv')
    baseline=[]; ref_errors=[]; draw_errors=[]
    seeds=np.random.SeedSequence(202611041).spawn(2)
    splits=[('E1_to_E2',d[d.study==1],d[d.study==2]),('E2_to_E1_assertive',d[d.study==2],d[(d.study==1)&(d.assertive==1)])]
    for (name,tr,te),seed in zip(splits,seeds):
        p,a=train(tr,te)
        for model,v in p.items():
            old=predictions[(predictions['split']==name)&(predictions.model==model)].set_index('participant').loc[te.participant].prediction.to_numpy()
            ref_errors.append(float(abs(v-old).max()))
        # MAE-optimal constant based exclusively on training responses.
        med=np.repeat(tr.intelligence.median(),len(te)); y=te.intelligence.to_numpy()
        delta=abs(y-p['design_user'])-abs(y-med)
        rng=np.random.default_rng(130719); boot=np.array([delta[rng.integers(len(te),size=len(te))].mean() for _ in range(4000)])
        baseline.append({'split':name,'train_mean':tr.intelligence.mean(),'train_median':tr.intelligence.median(),
                         'mae_mean':metrics(y,p['mean'])['mae'],'mae_median':metrics(y,med)['mae'],'mae_design_user':metrics(y,p['design_user'])['mae'],
                         'design_minus_median_mae':delta.mean(),'conditional_ci_low':np.quantile(boot,.025),'conditional_ci_high':np.quantile(boot,.975)})
        rng=np.random.default_rng(seed)
        bt=tr.iloc[rng.integers(len(tr),size=len(tr))].reset_index(drop=True)
        be=te.iloc[rng.integers(len(te),size=len(te))].reset_index(drop=True)
        bp,ba=train(bt,be,grouped=True); old=draws[(draws['split']==name)&(draws.draw==0)].iloc[0]
        for model,v in bp.items():
            for metric,value in metrics(be.intelligence.to_numpy(),v).items(): draw_errors.append(abs(value-old[f'{metric}_{model}']))
        assert all(ba[k]==old[f'alpha_{k}'] for k in ba)
    checks['independent_refit_max_prediction_error']=max(ref_errors)
    checks['independent_first_bootstrap_draw_each_direction_max_metric_error']=float(max(draw_errors))
    assert max(ref_errors)<1e-10 and max(draw_errors)<1e-10
    pd.DataFrame(baseline).to_csv(OUT/'median_baseline.csv',index=False)
    # Text-study point estimates from saved OOF rows, with the actual E4 comparator.
    text_errors=[]; incremental=[]
    cm=pd.read_csv(ROOT/'results/cocreation_prediction_metrics.csv')
    for split in ('participant','condition'):
        cp=pd.read_csv(ROOT/f'results/cocreation_predictions_{split}.csv')
        for _,row in cm[cm['split']==split].iterrows():
            met=metrics(cp.observed.to_numpy(),cp[row.model].to_numpy())
            text_errors.extend([abs(met['mae']-row.mae),abs(met['r2']-row.r2)])
        for model in ('telemetry','telemetry_adoption'):
            incremental.append({'split':split,'model':model,'comparator':'design_user',
                                'r2_gain':metrics(cp.observed.to_numpy(),cp[model].to_numpy())['r2']-metrics(cp.observed.to_numpy(),cp.design_user.to_numpy())['r2'],
                                'mae_reduction':float(np.mean(abs(cp.observed-cp.design_user)-abs(cp.observed-cp[model])))})
    pd.DataFrame(incremental).to_csv(OUT/'cocreation_increment_vs_design.csv',index=False)
    checks['cocreation_saved_prediction_max_metric_error']=float(max(text_errors)); assert max(text_errors)<1e-10
    # Source-level latency HC3 contrasts and Holm, independently of project formulas.
    raw=pd.read_csv(ROOT/'data/raw/tan2026/DATASET.csv')
    z=raw[raw.Rating_clarity.notna()]; assert z.ParticipantID.is_unique and len(z)==240
    task=z.TaskCondition.eq('Creation').to_numpy().astype(float)
    delay9=z.DelayCondition.eq('9_sec').to_numpy().astype(float); delay20=z.DelayCondition.eq('20_sec').to_numpy().astype(float)
    X=np.column_stack([np.ones(len(z)),delay9,delay20,task,task*delay9,task*delay20]); inv=np.linalg.inv(X.T@X)
    hat=np.sum((X@inv)*X,axis=1)
    cs={'9_minus_2':[0,1,0,0,.5,0],'20_minus_2':[0,0,1,0,0,.5],'long_minus_2':[0,.5,.5,0,.25,.25],'creation_minus_advice':[0,0,0,1,1/3,1/3]}
    lc=pd.read_csv(ROOT/'results/latency_contrasts.csv'); lerrors=[]; pvalues=[]
    for _,row in lc.iterrows():
        y=z[row.outcome].to_numpy(); beta=inv@X.T@y; resid=y-X@beta
        cov=inv@((X.T*(resid/(1-hat))**2)@X)@inv; c=np.array(cs[row.contrast]); effect=c@beta; se=np.sqrt(c@cov@c)
        pvalue=2*student_t.sf(abs(effect/se),len(z)-6); pvalues.append(pvalue)
        lerrors.extend([abs(effect-row.estimate),abs(se-row.se),abs(pvalue-row.p)])
    order=np.argsort(pvalues); adjusted=np.empty(len(order)); adjusted[order]=np.minimum(1,np.maximum.accumulate(np.array(pvalues)[order]*(len(order)-np.arange(len(order)))))
    lerrors.extend(abs(adjusted-lc.p_holm_28).tolist())
    checks['latency_raw_HC3_and_Holm_max_error']=float(max(lerrors)); assert max(lerrors)<1e-10
    checks['input_sha256']={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [ROOT/f'data/raw/beyond_voice/experiment{i}.sav.csv' for i in (1,2)]}
    (OUT/'arithmetic_checks.json').write_text(json.dumps(checks,indent=2))
    print(json.dumps(checks,indent=2)); print(pd.DataFrame(baseline).to_string(index=False))

if __name__=='__main__': main()
