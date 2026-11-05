#!/usr/bin/env python3
"""Reanalysis of public Beyond Voice data. No synthetic observations.
Run from repository root: .venv/bin/python src/analyze_voice.py
"""
from pathlib import Path
import os
os.environ.setdefault("MPLCONFIGDIR", str(Path(__file__).resolve().parents[1]/"tmp"/"matplotlib"))
os.environ.setdefault("XDG_CACHE_HOME", str(Path(__file__).resolve().parents[1]/"tmp"/"cache"))
import numpy as np
import pandas as pd
from scipy import stats
import statsmodels.formula.api as smf
from statsmodels.miscmodels.ordinal_model import OrderedModel
import semopy

ROOT=Path(__file__).resolve().parents[1]
OUT = ROOT / 'results'
OUT.mkdir(exist_ok=True)
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

if __name__ == '__main__':
    data = load()
    effects(data)
    measurement(data)
