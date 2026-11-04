"""Participant-level secondary analysis of Tan et al. (CHI 2026).
No intelligence scale is present. Post-experiment survey predictors are diagnostic,
not deployable telemetry and not causal adjustment variables.
"""
from pathlib import Path
import json, warnings, os
os.environ.setdefault("MPLCONFIGDIR", str(Path(__file__).resolve().parents[1]/"tmp/matplotlib"))
os.environ.setdefault("XDG_CACHE_HOME", str(Path(__file__).resolve().parents[1]/"tmp/cache"))
import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.stats.multitest import multipletests
from scipy.stats import spearmanr
from sklearn.model_selection import StratifiedKFold, KFold, GridSearchCV
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results'; OUT.mkdir(exist_ok=True)
SEED=20261104
RATINGS=['Rating_'+s for s in ['clarity','relevance','understanding','thoughtfulness','usefulness','trustworthiness','expectation-gap']]
EVENTS=['new-generation','edit-generation','re-generation','copy','paste','cut','new-chat']

def load():
    raw=pd.read_csv(ROOT/'data/raw/tan2026/DATASET.csv')
    assert len(raw)==2651 and raw.ParticipantID.nunique()==240
    assert raw.groupby('ParticipantID').DelayCondition.nunique().eq(1).all()
    ambiguity=raw.groupby('ParticipantID').TaskCondition.nunique()
    ambiguous=ambiguity[ambiguity>1].index.tolist()
    assert ambiguous==['P132','P186','P215']
    raw[raw.ParticipantID.isin(ambiguous)].to_csv(OUT/'latency_ambiguous_task_rows.csv',index=False)
    for c in RATINGS:
        assert raw.groupby('ParticipantID')[c].count().eq(1).all(), c
    survey=raw[raw[RATINGS[0]].notna()].copy().set_index('ParticipantID')
    assert len(survey)==240 and not survey[RATINGS].isna().any().any()
    assert ((survey[RATINGS]>=1)&(survey[RATINGS]<=7)).all().all()
    counts=pd.crosstab(raw.ParticipantID,raw.EventType).reindex(columns=EVENTS,fill_value=0)
    counts.columns=['event_'+x.replace('-','_') for x in counts.columns]
    df=survey.drop(columns=['QuestionID','EventType']).join(counts)
    df['ambiguous_task_id']=df.index.isin(ambiguous)
    df['task_creation']=(df.TaskCondition=='Creation').astype(int)
    df['delay9']=(df.DelayCondition=='9_sec').astype(int)
    df['delay20']=(df.DelayCondition=='20_sec').astype(int)
    df['interaction9']=df.task_creation*df.delay9
    df['interaction20']=df.task_creation*df.delay20
    df.to_csv(ROOT/'data/processed/latency_participants.csv')
    return raw,df

def run():
    raw,d=load(); design=['delay9','delay20','task_creation','interaction9','interaction20']
    X=sm.add_constant(d[design]); tests=[]; contrasts=[]
    # Marginal delay contrasts equally weight the two randomized task types.
    cs={'9_minus_2':np.array([0,1,0,0,.5,0]),'20_minus_2':np.array([0,0,1,0,0,.5]),'long_minus_2':np.array([0,.5,.5,0,.25,.25]),'creation_minus_advice':np.array([0,0,0,1,1/3,1/3])}
    for y in RATINGS:
        fit=sm.OLS(d[y],X).fit(cov_type='HC3',use_t=True)
        for name,cols in [('delay',[1,2]),('task',[3]),('interaction',[4,5])]:
            if name=='delay':
                C=np.vstack([cs['9_minus_2'],cs['20_minus_2']])
            elif name=='task': C=cs['creation_minus_advice'][None,:]
            else: C=np.eye(6)[cols]
            f=fit.f_test(C)
            tests.append({'outcome':y,'test':name,'F':float(f.fvalue),'p':float(f.pvalue),'df_num':float(f.df_num),'df_denom':float(f.df_denom)})
        for name,c in cs.items():
            t=fit.t_test(c);ci=t.conf_int()[0]
            contrasts.append({'outcome':y,'contrast':name,'estimate':float(np.asarray(t.effect).ravel()[0]),'se':float(np.asarray(t.sd).ravel()[0]),'ci_low':float(ci[0]),'ci_high':float(ci[1]),'p':float(t.pvalue)})
    tests=pd.DataFrame(tests);tests['p_holm_21']=multipletests(tests.p,method='holm')[1];tests.to_csv(OUT/'latency_omnibus.csv',index=False)
    contrasts=pd.DataFrame(contrasts);contrasts['p_holm_28']=multipletests(contrasts.p,method='holm')[1];contrasts.to_csv(OUT/'latency_contrasts.csv',index=False)
    means=d.groupby(['TaskCondition','DelayCondition'])[RATINGS].agg(['mean','std','count']);means.to_csv(OUT/'latency_cell_means.csv')
    # Sensitivity for source IDs carrying conflicting between-subject task labels.
    sensitive=[]
    clean=d.loc[~d.ambiguous_task_id].copy()
    for y in RATINGS:
        fit=sm.OLS(clean[y],sm.add_constant(clean[design])).fit(cov_type='HC3',use_t=True)
        for name,c in cs.items():
            t=fit.t_test(c);ci=t.conf_int()[0]
            sensitive.append({'outcome':y,'contrast':name,'n':len(clean),'estimate':float(np.asarray(t.effect).ravel()[0]),'ci_low':float(ci[0]),'ci_high':float(ci[1]),'p':float(t.pvalue)})
    sensitive=pd.DataFrame(sensitive);sensitive['p_holm_28']=multipletests(sensitive.p,method='holm')[1];sensitive.to_csv(OUT/'latency_contrasts_excluding_ambiguous.csv',index=False)
    # Correlation-based dimensionality diagnostics, explicitly not a validated latent scale.
    ratings=d[RATINGS].to_numpy(); eig=np.linalg.eigvalsh(np.corrcoef(ratings.T))[::-1]
    rng=np.random.default_rng(SEED); null=[]
    for _ in range(1000):
        perm=np.column_stack([rng.permutation(ratings[:,j]) for j in range(ratings.shape[1])]);null.append(np.linalg.eigvalsh(np.corrcoef(perm.T))[::-1])
    alpha=ratings.shape[1]/(ratings.shape[1]-1)*(1-ratings.var(axis=0,ddof=1).sum()/ratings.sum(axis=1).var(ddof=1))
    factor={'pearson_eigenvalues':eig.tolist(),'parallel_analysis_95th_percentile':np.quantile(null,.95,axis=0).tolist(),'components_above_null':int((eig>np.quantile(null,.95,axis=0)).sum()),'alpha_seven_quality_items':float(alpha),'caution':'Exploratory Pearson PCA on ordinal ceiling-heavy ratings. Alpha is not evidence of unidimensionality or an intelligence factor.'}
    (OUT/'latency_dimensionality.json').write_text(json.dumps(factor,indent=2))
    # Nested participant CV. Fixed splits shared across model classes and outcomes.
    full_d=d.copy()
    d=clean
    strata=d.TaskCondition+'_'+d.DelayCondition
    splits=[(r,tr,te) for r in range(10) for tr,te in StratifiedKFold(5,shuffle=True,random_state=SEED+r).split(d,strata)]
    events=['event_'+e.replace('-','_') for e in EVENTS]
    models={'mean':[], 'design':design,'telemetry':events,'design_telemetry':design+events}
    summary=[];predrows=[]
    for target in ['Rating_thoughtfulness','Rating_usefulness']:
        features={**models,'survey_diagnostic':[c for c in RATINGS if c!=target]}
        preds={name:np.full((10,len(d)),np.nan) for name in features}
        y=d[target].to_numpy()
        for r,tr,te in splits:
            for name,cols in features.items():
                if not cols: pred=np.full(len(te),y[tr].mean())
                else:
                    data=d[cols].to_numpy(dtype=float).copy()
                    for j,c in enumerate(cols):
                        if c in events: data[:,j]=np.log1p(data[:,j])
                    estimator=GridSearchCV(make_pipeline(StandardScaler(),Ridge()),{'ridge__alpha':[.01,.1,1,10,100,1000]},cv=KFold(3,shuffle=True,random_state=SEED+r),scoring='neg_mean_squared_error',n_jobs=1)
                    estimator.fit(data[tr],y[tr]);pred=estimator.predict(data[te])
                preds[name][r,te]=pred
        for name,p in preds.items():
            assert np.isfinite(p).all()
            # Summarize metrics per full OOF repeat, not per small fold; avoid fold averaging bias in R2.
            metric=[(mean_absolute_error(y,z),np.sqrt(mean_squared_error(y,z)),r2_score(y,z)) for z in p]
            pooled=p.mean(axis=0);base=preds['mean'].mean(axis=0)
            delta=np.abs(y-pooled)-np.abs(y-base)
            rng=np.random.default_rng(SEED);boots=[delta[rng.integers(0,len(y),len(y))].mean() for _ in range(2000)]
            summary.append({'target':target,'model':name,'n':len(y),'oof_mae_mean':float(np.mean(metric,axis=0)[0]),'oof_rmse_mean':float(np.mean(metric,axis=0)[1]),'oof_r2_mean':float(np.mean(metric,axis=0)[2]),'averaged_oof_mae':float(mean_absolute_error(y,pooled)),'averaged_oof_baseline_mae':float(mean_absolute_error(y,base)),'mean_prediction_spearman':float(spearmanr(y,pooled).statistic) if name!='mean' and np.std(pooled)>0 else None,'paired_mae_delta_vs_mean_averaged_oof':float(delta.mean()),'delta_conditional_boot_ci_low':float(np.quantile(boots,.025)),'delta_conditional_boot_ci_high':float(np.quantile(boots,.975))})
            for r in range(10):
                predrows.extend({'participant':pid,'target':target,'model':name,'repeat':r,'observed':float(y[i]),'predicted':float(p[r,i])} for i,pid in enumerate(d.index))
    cv=pd.DataFrame(summary);cv.to_csv(OUT/'latency_prediction_metrics.csv',index=False);pd.DataFrame(predrows).to_csv(OUT/'latency_predictions.csv',index=False)
    d=full_d
    fig,axes=plt.subplots(1,2,figsize=(9,3.6),sharey=True)
    for ax,y in zip(axes,['Rating_thoughtfulness','Rating_usefulness']):
        for task,color,offset in [('Advice','#7255a5',-.07),('Creation','#087f8c',.07)]:
            z=d[d.TaskCondition==task];m=[];se=[]
            for delay in ['2_sec','9_sec','20_sec']:
                a=z[z.DelayCondition==delay][y];m.append(a.mean());se.append(1.96*a.std(ddof=1)/np.sqrt(len(a)))
            ax.errorbar(np.arange(3)+offset,m,yerr=se,marker='o',label=task,color=color,capsize=4)
        ax.set_xticks(range(3),['2 s','9 s','20 s']);ax.set_title(y.removeprefix('Rating_').capitalize());ax.set_xlabel('Randomized response delay');ax.set_ylim(1,7.2);ax.spines[['top','right']].set_visible(False)
    axes[0].set_ylabel('Mean rating (1–7; 95% CI)');axes[1].legend(frameon=False);fig.tight_layout();fig.savefig(OUT/'figures/latency_ratings.png',dpi=180);plt.close(fig)
    meta={'raw_events':len(raw),'participants':len(d),'prediction_participants':len(clean),'ambiguous_task_ids':['P132','P186','P215'],'condition_resolution':'Survey-bearing row task label for primary n240; sensitivity excludes conflicting IDs, n237; prediction uses n237','cell_sizes':d.groupby(['TaskCondition','DelayCondition']).size().to_dict(),'seed':SEED,'cv':'10 repeats x stratified 5 outer folds; 3 inner folds; ridge alpha selected inside training only','inference':'OLS HC3, t/F reference distributions, participant unit; omnibus 21-test Holm family and contrast 28-test Holm family','limitations':['Secondary exploratory analysis, not preregistered here','Not voice interaction; no direct perceived-intelligence item','No objective correctness, response text, demographics or measured actual latency in released file','Survey diagnostic predicts concurrent ratings and cannot be deployed from telemetry','Bootstrap intervals condition on averaged fitted OOF predictions; not full retraining uncertainty']}
    meta['cell_sizes']={str(k):int(v) for k,v in meta['cell_sizes'].items()};(OUT/'latency_analysis_metadata.json').write_text(json.dumps(meta,indent=2))
    print(tests.to_string(index=False));print(contrasts[contrasts.outcome.isin(['Rating_thoughtfulness','Rating_usefulness'])].to_string(index=False));print(cv.to_string(index=False))

if __name__=='__main__': run()
