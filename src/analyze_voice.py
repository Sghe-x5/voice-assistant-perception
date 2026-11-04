#!/usr/bin/env python3
"""Reanalysis of public Beyond Voice data. No synthetic observations.
Run from repository root: .venv/bin/python src/analyze_voice.py
"""
from pathlib import Path
import json, warnings, os
os.environ.setdefault("MPLCONFIGDIR", str(Path(__file__).resolve().parents[1]/"tmp"/"matplotlib"))
os.environ.setdefault("XDG_CACHE_HOME", str(Path(__file__).resolve().parents[1]/"tmp"/"cache"))
import numpy as np
import pandas as pd
from scipy import stats
import statsmodels.formula.api as smf
from statsmodels.miscmodels.ordinal_model import OrderedModel
from sklearn.pipeline import make_pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import Ridge
from sklearn.model_selection import GridSearchCV,KFold
from sklearn.metrics import mean_absolute_error,mean_squared_error,r2_score
import semopy
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results';FIG=ROOT/'figures';OUT.mkdir(exist_ok=True);FIG.mkdir(exist_ok=True)
SEED=20261104; B=2000
rng=np.random.default_rng(SEED)
I=[f'intelligence_{j}' for j in range(1,6)]
CR=[f'Credibility_{j}' for j in range(1,6)]

def load():
    frames=[]
    for study in [1,2]:
        d=pd.read_csv(ROOT/f'data/raw/beyond_voice/experiment{study}.sav.csv')
        d['study']=study;d['participant']= [f'E{study}_{j:03d}' for j in range(len(d))]
        d['partner']=(d.Social_Role=='Partner').astype(int)
        d['assertive']=(d.Speech_Style=='Assertive').astype(int) if study==1 else 1
        d['mc_pass']=(d.priming==1).astype(int) if study==1 else (d.MP1final==1).astype(int)
        d['mc_all_pass']=d['mc_pass'] if study==1 else ((d.MP1final==1)&(d.MP2final==1)).astype(int)
        d['age_years']=2024-d['age'] # reproduces source age2; NOT current age
        d['female']=(d.gen==1).astype(int);d['diverse_gender']=(d.gen==2).astype(int)
        d['owner']=(d.own==1).astype(int)
        # Only named services. Missing for nonowners is structural; retain NaN.
        d['information_search']=d[[f'frequency_use__{j}' for j in range(1,6)]].mean(axis=1)
        assert np.allclose(d[I].mean(axis=1),d.intelligence)
        assert np.allclose(d[CR].mean(axis=1),d.credibility)
        assert d[I+CR].notna().all().all()
        assert ((d[I+CR]>=1)&(d[I+CR]<=7)).all().all()
        frames.append(d)
    return pd.concat(frames,ignore_index=True)

def contrast(d,outcome='intelligence',selected=False,adjust_style=True):
    z=d[d.mc_pass==1] if selected else d
    terms=['partner']
    if z.study.nunique()>1:terms+=['C(study)']
    if adjust_style and z.assertive.nunique()>1:terms+=['assertive']
    m=smf.ols(f'{outcome} ~ '+ ' + '.join(terms),z).fit(cov_type='HC3')
    ci=m.conf_int().loc['partner']
    return dict(n=len(z),estimate=m.params['partner'],ci_low=ci.iloc[0],ci_high=ci.iloc[1],p=m.pvalues['partner'],se=m.bse['partner'],formula=m.model.formula)

def fast_beta(z,selected):
    if selected:z=z[z.mc_pass==1]
    cols=[np.ones(len(z)),z.partner.to_numpy()]
    if z.study.nunique()>1:cols.append((z.study.to_numpy()==2).astype(float))
    if z.assertive.nunique()>1:cols.append(z.assertive.to_numpy())
    return np.linalg.lstsq(np.column_stack(cols),z.intelligence.to_numpy(),rcond=None)[0][1]

def effects(d):
    rows=[];diags=[]
    for label,z in [('E1',d[d.study==1]),('E2',d[d.study==2]),('pooled',d)]:
        for outcome in ['intelligence','credibility']:
            for selected in [False,True]:
                rows.append({'sample':label,'outcome':outcome,'selection':'first/only-MC-pass' if selected else 'all-released',**contrast(z,outcome,selected)})
        # Paired participant bootstrap, stratified by original study and randomized role/style.
        strata=[g.index.to_numpy() for _,g in z.groupby(['study','partner','assertive'])]
        diffs=[]
        for b in range(B):
            zb=z.loc[np.concatenate([rng.choice(ix,len(ix),replace=True) for ix in strata])]
            diffs.append(fast_beta(zb,True)-fast_beta(zb,False))
        lo,hi=np.quantile(diffs,[.025,.975])
        diags.append({'sample':label,'selected_minus_full':fast_beta(z,True)-fast_beta(z,False),'ci_low':lo,'ci_high':hi,'bootstrap_B':B})
    # Add paper's all-check rule: experiment 1 final check; experiment 2 both checks.
    for label,z in [('E1',d[d.study==1]),('E2',d[d.study==2]),('pooled',d)]:
        z=z.copy();z['mc_pass']=z['mc_all_pass']
        for outcome in ['intelligence','credibility']:
            rows.append({'sample':label,'outcome':outcome,'selection':'all-MC-pass',**contrast(z,outcome,True)})
        if label!='E1':
            strata=[g.index.to_numpy() for _,g in z.groupby(['study','partner','assertive'])]
            diffs=[]
            for b in range(B):
                zb=z.loc[np.concatenate([rng.choice(ix,len(ix),replace=True) for ix in strata])]
                diffs.append(fast_beta(zb,True)-fast_beta(zb,False))
            lo,hi=np.quantile(diffs,[.025,.975])
            diags.append({'sample':label,'selection':'all-MC-pass','selected_minus_full':fast_beta(z,True)-fast_beta(z,False),'ci_low':lo,'ci_high':hi,'bootstrap_B':B})
    for q in diags:q.setdefault('selection','first/only-MC-pass')
    selected=d[d.mc_all_pass==1]
    assert len(selected)==269
    selected.groupby('partner')[['intelligence','credibility']].agg(['mean','std','count']).to_csv(OUT/'voice_publication_replication.csv')
    pd.DataFrame(rows).to_csv(OUT/'voice_effects.csv',index=False)
    pd.DataFrame(diags).to_csv(OUT/'voice_selection_sensitivity.csv',index=False)
    ret=d.groupby(['study','partner']).mc_pass.agg(['mean','sum','count']).reset_index()
    ret.to_csv(OUT/'voice_retention.csv',index=False)
    # Ordinal sensitivity: single direct intelligent item, not averaged scale coerced into categories.
    ordrows=[]
    for label,z in [('E1',d[d.study==1]),('E2',d[d.study==2]),('pooled',d)]:
        for select in [False,True]:
            q=z[z.mc_pass==1] if select else z
            x=q[['partner']].copy()
            if q.study.nunique()>1:x['study2']=(q.study==2).astype(int)
            if q.assertive.nunique()>1:x['assertive']=q.assertive
            fit=OrderedModel(q.intelligence_3.astype(int),x, distr='logit').fit(method='bfgs',disp=False)
            ci=fit.conf_int().loc['partner']
            ordrows.append({'sample':label,'selection':'first/only-MC-pass' if select else 'all-released','n':len(q),'log_odds':fit.params.partner,'ci_low':ci.iloc[0],'ci_high':ci.iloc[1],'p':fit.pvalues.partner,'converged':bool(fit.mle_retvals['converged'])})
    pd.DataFrame(ordrows).to_csv(OUT/'voice_ordinal_sensitivity.csv',index=False)
    # Prespecified descriptive moderation; all covariates refer to pre-existing attributes,
    # but reports were collected after exposure. No claim of mechanism.
    mod=[]
    for moderator in ['age_years','female','owner','information_search']:
        z=d.dropna(subset=[moderator]).copy();z['moderator']=z[moderator]-z[moderator].mean()
        m=smf.ols('intelligence ~ partner*moderator + C(study) + assertive',z).fit(cov_type='HC3')
        p='partner:moderator';ci=m.conf_int().loc[p]
        mod.append({'moderator':moderator,'n':len(z),'interaction':m.params[p],'ci_low':ci.iloc[0],'ci_high':ci.iloc[1],'p':m.pvalues[p]})
    from statsmodels.stats.multitest import multipletests
    md=pd.DataFrame(mod);md['p_holm']=multipletests(md.p,method='holm')[1];md.to_csv(OUT/'voice_moderation.csv',index=False)
    return pd.DataFrame(rows)

def alpha(x):
    x=np.asarray(x);k=x.shape[1]
    return k/(k-1)*(1-x.var(axis=0,ddof=1).sum()/x.sum(axis=1).var(ddof=1))

def htmt(x):
    r=np.corrcoef(np.asarray(x),rowvar=False)
    a=np.abs(r[:5,:5][np.triu_indices(5,1)]).mean()
    b=np.abs(r[5:,5:][np.triu_indices(5,1)]).mean()
    return np.abs(r[:5,5:]).mean()/np.sqrt(a*b)

def measurement(d):
    rows=[];cfa=[]
    specs={'one_factor':'G =~ '+' + '.join(I+CR),'two_factor':'Intelligence =~ '+' + '.join(I)+'\nCredibility =~ '+' + '.join(CR)+'\nIntelligence ~~ Credibility'}
    for label,z in [('E1',d[d.study==1]),('E2',d[d.study==2]),('pooled',d)]:
        x=z[I+CR].to_numpy(); h=[htmt(x[rng.integers(0,len(x),len(x))]) for _ in range(B)]
        lo,hi=np.quantile(h,[.025,.975])
        rows.append({'sample':label,'n':len(z),'alpha_intelligence':alpha(z[I]),'alpha_credibility':alpha(z[CR]),'composite_pearson_r':z.intelligence.corr(z.credibility),'composite_spearman_r':stats.spearmanr(z.intelligence,z.credibility).statistic,'htmt':htmt(x),'htmt_ci_low':lo,'htmt_ci_high':hi})
        for name,spec in specs.items():
            m=semopy.Model(spec);fit=m.fit(z[I+CR],obj='MLW');s=semopy.calc_stats(m).iloc[0]
            est=m.inspect(std_est=True);est.to_csv(OUT/f'voice_cfa_{label}_{name}_parameters.csv',index=False)
            v={'sample':label,'model':name,'n':len(z),'converged':bool(fit.success),**{k:float(s[k]) for k in ['DoF','chi2','chi2 p-value','CFI','TLI','RMSEA']}}
            k=sum(p.active for p in m.parameters.values())
            v['n_parameters']=k
            v['AIC_relative_saturated']=float(s['chi2'])+2*k
            v['BIC_relative_saturated']=float(s['chi2'])+np.log(len(z))*k
            if name=='two_factor':
                zz=est[(est.op=='~~')&(est.lval=='Intelligence')&(est.rval=='Credibility')]
                v['latent_correlation']=float(zz['Est. Std'].iloc[0])
            cfa.append(v)
    pd.DataFrame(rows).to_csv(OUT/'voice_measurement.csv',index=False)
    pd.DataFrame(cfa).to_csv(OUT/'voice_cfa.csv',index=False)
    return rows

def metrics(y,p):
    return {'mae':mean_absolute_error(y,p),'rmse':np.sqrt(mean_squared_error(y,p)),'r2':r2_score(y,p),'spearman':stats.spearmanr(y,p).statistic if np.std(p)>1e-10 else np.nan}

def prediction(d):
    user=['age_years','female','diverse_gender','owner','information_search']
    models={'mean':[],'design':['partner','assertive'],'user':user,'design_user':['partner','assertive']+user,'credibility_only':['credibility'],'survey_augmented':['partner','assertive']+user+['credibility']}
    splits=[('E1_to_E2',d[d.study==1],d[d.study==2]),('E2_to_E1_assertive',d[d.study==2],d[(d.study==1)&(d.assertive==1)]),('E2_to_E1_all_shifted',d[d.study==2],d[d.study==1])]
    records=[];preds=[]
    for split,tr,te in splits:
        y=te.intelligence.to_numpy();local={}
        for name,cols in models.items():
            alpha_best=np.nan
            if not cols:p=np.full(len(te),tr.intelligence.mean())
            else:
                pipe=make_pipeline(SimpleImputer(strategy='median',add_indicator=True),StandardScaler(),Ridge())
                cv=KFold(n_splits=5,shuffle=True,random_state=SEED)
                fit=GridSearchCV(pipe,{'ridge__alpha':[.1,1.,10.,100.,1000.]},scoring='neg_mean_absolute_error',cv=cv,n_jobs=1)
                fit.fit(tr[cols],tr.intelligence);p=fit.predict(te[cols]);alpha_best=fit.best_params_['ridge__alpha']
            local[name]=p
            records.append({'split':split,'model':name,'n_train':len(tr),'n_test':len(te),'ridge_alpha':alpha_best,**metrics(y,p)})
            preds.extend({'split':split,'participant':idx,'y':yy,'model':name,'prediction':pp} for idx,yy,pp in zip(te.participant,y,p))
        # Conditional test-sample intervals: trained predictors held fixed; no claim to capture retraining variance.
        inds=rng.integers(0,len(y),(B,len(y)))
        for name,p in local.items():
            r=next(v for v in records if v['split']==split and v['model']==name)
            abs_e=np.abs(y-p);baseline=np.abs(y-local['mean'])
            boot_mae=abs_e[inds].mean(axis=1);diff=(abs_e-baseline)[inds].mean(axis=1)
            r.update(mae_ci_low=np.quantile(boot_mae,.025),mae_ci_high=np.quantile(boot_mae,.975),mae_minus_mean=float(np.mean(abs_e-baseline)),difference_ci_low=np.quantile(diff,.025),difference_ci_high=np.quantile(diff,.975))
    res=pd.DataFrame(records);res.to_csv(OUT/'voice_prediction.csv',index=False)
    pd.DataFrame(preds).to_csv(OUT/'voice_predictions.csv',index=False)
    return res

def plots(e,p,m):
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'figure.dpi':150})
    fig,ax=plt.subplots(figsize=(8,6));z=e[e.outcome=='intelligence'].reset_index(drop=True)
    for j,r in z.iterrows():
        ax.errorbar(r.estimate,j,xerr=[[r.estimate-r.ci_low],[r.ci_high-r.estimate]],fmt='o',color='#2563eb' if r.selection=='all-released' else '#c2410c',capsize=3)
    ax.set_yticks(range(len(z)),[f'{r["sample"]}: {r["selection"]}' for _,r in z.iterrows()]);ax.axvline(0,color='.5',ls='--');ax.set_xlabel('Partner minus servant: perceived intelligence (1–7), HC3 95% CI');fig.tight_layout();fig.savefig(FIG/'voice_selection_effects.png');fig.savefig(FIG/'voice_selection_effects.pdf');plt.close(fig)
    fig,axs=plt.subplots(1,2,figsize=(10,4.6),sharex=True)
    for ax,s in zip(axs,['E1_to_E2','E2_to_E1_assertive']):
        z=p[p.split==s].reset_index(drop=True)
        ax.errorbar(z.mae,range(len(z)),xerr=[z.mae-z.mae_ci_low,z.mae_ci_high-z.mae],fmt='o',capsize=3,color='#2563eb');ax.set_yticks(range(len(z)),z.model);ax.set_title(s.replace('_',' '));ax.set_xlabel('MAE (lower is better), conditional 95% CI')
    fig.tight_layout();fig.savefig(FIG/'voice_transfer_prediction.png');fig.savefig(FIG/'voice_transfer_prediction.pdf');plt.close(fig)

if __name__=='__main__':
    d=load();e=effects(d);m=measurement(d);p=prediction(d);plots(e,p,m)
    summary={'n':len(d),'studies':d.groupby('study').size().to_dict(),'seed':SEED,'bootstrap_B':B,'sample':'released eligible vignette raters; not direct assistant users and not all randomized recruits','measurement':m,'method_notes':['CFA MLW treats seven-category ratings as approximately continuous; no ordinal CFA or invariance test completed.','Ordered-logit sensitivity concerns direct intelligent item and assumes proportional odds.','Study-held-out prediction fits preprocessing and ridge alpha only within training study.','Prediction intervals condition on trained models; overlapping reverse test sets are not independent replications.','Survey credibility is contemporaneous same-rater benchmark, not objective telemetry or a causal driver.','Manipulation-check selected estimates are descriptive and can suffer post-treatment selection bias.','Publication pooled n269 exactly reproduced by E1 only check plus E2 both checks; primary first/only selection n328 is explicitly distinct.','No error-rate/latency/task-success telemetry in Beyond Voice. No longitudinal updating identified.']}
    (OUT/'voice_summary.json').write_text(json.dumps(summary,indent=2,allow_nan=False));print(e.to_string(index=False));print(pd.DataFrame(m).to_string(index=False));print(p[['split','model','mae','r2','mae_minus_mean','difference_ci_low','difference_ci_high']].to_string(index=False))

    # Fit a deliverable research model after evaluation. This all-data fit has no untouched
    # evaluation set; external metrics above concern study-specific training procedures.
    import joblib
    cols=['partner','assertive','age_years','female','diverse_gender','owner','information_search']
    final=GridSearchCV(make_pipeline(SimpleImputer(strategy='median',add_indicator=True),StandardScaler(),Ridge()),{'ridge__alpha':[.1,1.,10.,100.,1000.]},scoring='neg_mean_absolute_error',cv=KFold(5,shuffle=True,random_state=SEED),n_jobs=1)
    final.fit(d[cols],d.intelligence)
    md=ROOT/'models';md.mkdir(exist_ok=True)
    joblib.dump(final.best_estimator_,md/'voice_design_user.joblib')
    card={'name':'Voice perceived-intelligence research Ridge baseline','version':'2026-11-04','source':'https://osf.io/exmc8/','training_n':len(d),'alpha':final.best_params_['ridge__alpha'],'target':'Mean of five 1–7 adapted perceived-intelligence items after watching six voice-assistant vignettes','features':cols,'coding':{'partner':'1 partner framing, 0 servant framing','assertive':'1 assertive style, 0 affiliative style','age_years':'Age at source study, computed as 2024 minus birth year; prediction input should be age in years, not birth year','female':'Source female category indicator; 0 otherwise','diverse_gender':'Source diverse-gender category indicator; 0 otherwise; only five participants, no subgroup validation','owner':'1 owns a smart speaker, 0 does not; not general voice-assistant exposure','information_search':'Mean frequency 1–7 over five named services among owners; null for nonowners'},'training_ranges':{c:[float(d[c].min()),float(d[c].max())] for c in cols},'limitations':['Research baseline only, not deployment-validated','Modest or absent transfer improvement over a constant baseline; see results/voice_prediction.csv','Inputs do not measure factual accuracy, task success, latency or repair behavior','Only UK English-language vignette judgments, not direct voice interaction','All-data final fit is not independently evaluated','No calibrated individual predictive interval is available','Do not interpret demographic coefficients as causal effects or use for consequential decisions'],'metrics_file':'results/voice_prediction.csv','training_procedure':'Five-fold inner CV on full released n553; alpha chosen on MAE; imputation/scaling inside pipeline; fit performed after assessment','output':'Unclipped linear estimate on nominal 1–7 rating scale, not probability','seed':SEED}
    (md/'voice_model_card.json').write_text(json.dumps(card,indent=2))
