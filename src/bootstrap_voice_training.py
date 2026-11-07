#!/usr/bin/env python3
"""Training-and-test bootstrap sensitivity for two voice-study transfers.
Resampled training copies retain original participant-ID groups during inner CV.
No original test-study participant ever enters training. No synthetic outcomes.
"""
from pathlib import Path
import argparse,json,time,importlib.util,hashlib
import numpy as np
import pandas as pd
from sklearn.model_selection import GroupKFold,GridSearchCV
from sklearn.pipeline import make_pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error,r2_score

ROOT=Path(__file__).resolve().parents[1]
SEED=202611041
COLS={'design_user':['partner','assertive','age_years','female','diverse_gender','owner','information_search'],'credibility_only':['credibility']}
ALPHAS=[.1,1.,10.,100.,1000.]


def load():
    spec=importlib.util.spec_from_file_location('voice_analysis',ROOT/'src/analyze_voice.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module.load()


def fit_predict(train,test):
    """Explicit grouped folds reused across feature sets and tuning candidates."""
    groups=train.participant.to_numpy()
    cv=list(GroupKFold(n_splits=5).split(train,groups=groups))
    for tr,va in cv:
        assert set(groups[tr]).isdisjoint(groups[va]), 'Bootstrap duplicate leaks across inner folds'
    predictions={'mean':np.full(len(test),train.intelligence.mean())}
    alphas={}
    for name,cols in COLS.items():
        est=GridSearchCV(make_pipeline(SimpleImputer(strategy='median',add_indicator=True),StandardScaler(),Ridge()),{'ridge__alpha':ALPHAS},scoring='neg_mean_absolute_error',cv=cv,n_jobs=1,error_score='raise')
        est.fit(train[cols],train.intelligence)
        predictions[name]=est.predict(test[cols])
        alphas[name]=est.best_params_['ridge__alpha']
    y=test.intelligence.to_numpy()
    maes={name:mean_absolute_error(y,p) for name,p in predictions.items()}
    rs={name:r2_score(y,p) for name,p in predictions.items()}
    stats={**{f'mae_{k}':float(v) for k,v in maes.items()},**{f'r2_{k}':float(v) for k,v in rs.items()},**{f'alpha_{k}':float(v) for k,v in alphas.items()},
           'mae_reduction_survey_vs_operational':float(maes['design_user']-maes['credibility_only']),
           'r2_gain_survey_vs_operational':float(rs['credibility_only']-rs['design_user']),
           'mae_reduction_operational_vs_mean':float(maes['mean']-maes['design_user'])}
    assert all(np.isfinite(v) for v in stats.values())
    return stats


def run(draws=1000):
    if draws<200:raise ValueError('At least 200 draws are required for this sensitivity run')
    start=time.monotonic();d=load();all_rows=[];references=[]
    splits=[('E1_to_E2',d[d.study==1],d[d.study==2]),('E2_to_E1_assertive',d[d.study==2],d[(d.study==1)&(d.assertive==1)])]
    # Independent RNG stream per transfer; same train/test draws across compared models.
    seeds=np.random.SeedSequence(SEED).spawn(len(splits))
    for (name,train,test),seed in zip(splits,seeds):
        assert set(train.participant).isdisjoint(test.participant)
        references.append({'split':name,**fit_predict(train,test)})
        rng=np.random.default_rng(seed)
        for b in range(draws):
            trix=rng.integers(0,len(train),len(train));teix=rng.integers(0,len(test),len(test))
            tr=train.iloc[trix].reset_index(drop=True);te=test.iloc[teix].reset_index(drop=True)
            assert set(tr.participant).isdisjoint(te.participant)
            row={'split':name,'draw':b,'n_train':len(tr),'n_test':len(te),'n_unique_train':tr.participant.nunique(),'n_unique_test':te.participant.nunique(),**fit_predict(tr,te)}
            all_rows.append(row)
            if (b+1)%50==0:print(f'{name}: {b+1}/{draws} draws; elapsed {time.monotonic()-start:.1f}s',flush=True)
    out=ROOT/'results';out.mkdir(exist_ok=True)
    samples=pd.DataFrame(all_rows);samples.to_csv(out/'voice_retraining_bootstrap_draws.csv',index=False)
    reference=pd.DataFrame(references);reference.to_csv(out/'voice_retraining_reference.csv',index=False)
    summaries=[]
    metrics=[c for c in reference.columns if c!='split' and not c.startswith('alpha_')]
    for name,g in samples.groupby('split',sort=False):
        r=reference[reference.split==name].iloc[0]
        for metric in metrics:
            x=g[metric].to_numpy();lo,hi=np.quantile(x,[.025,.975])
            summaries.append({'split':name,'metric':metric,'reference_grouped_cv':r[metric],'bootstrap_mean':x.mean(),'bootstrap_median':np.median(x),'ci_low':lo,'ci_high':hi,'draws':draws})
    summary=pd.DataFrame(summaries);summary.to_csv(out/'voice_retraining_bootstrap.csv',index=False)
    meta={'seed':SEED,'input_sha256':{f'experiment{i}.sav.csv':hashlib.sha256((ROOT/f'data/raw/beyond_voice/experiment{i}.sav.csv').read_bytes()).hexdigest() for i in (1,2)},'bootstrap_draws_per_transfer':draws,'bootstrap_final_model_refits':int(len(samples)*len(COLS)), 'reference_final_model_refits':int(len(splits)*len(COLS)), 'inner_candidate_fits_including_reference':int((len(samples)+len(splits))*len(COLS)*len(ALPHAS)*5),'source':'data/raw/beyond_voice/experiment{1,2}.sav.csv','training_samples':'All released eligible participants: E1=353 or E2=200; no manipulation-check filtering','test_samples':'E1→E2: n200; E2→E1 assertive: n180','resampling':'Independent ordinary participant bootstrap of train and test within each transfer, preserving original sample sizes; same resamples paired across models','inner_validation':'Five-fold GroupKFold by original participant ID; bootstrap copies cannot appear in both inner-training and validation folds; explicit disjointness assertions execute on every draw','preprocessing':'Median imputation with missing indicator, standardization, Ridge; all learned inside inner training folds, then refit on entire bootstrapped training set','tuning':{'alphas':ALPHAS,'selection_metric':'mean absolute error','folds':5},'sign_conventions':{'mae_reduction_survey_vs_operational':'MAE(design_user) - MAE(credibility_only); positive favors survey benchmark','r2_gain_survey_vs_operational':'R2(credibility_only) - R2(design_user); positive favors survey benchmark','mae_reduction_operational_vs_mean':'MAE(train mean) - MAE(design_user); positive favors operational model'},'interval':'2.5th and 97.5th empirical percentiles of paired training-and-test bootstrap draws','protocol_difference':'Original voice analysis tunes with shuffled KFold. This sensitivity uses grouped KFold, required to prevent leakage of bootstrap duplicate participants. Reference results refit original samples with this grouped protocol. It is not an identical rerun of the original training algorithm.','limitations':['Exploratory sensitivity, not preregistered','Conditional on these empirical studies and their stimulus sets; no new populations, products or languages','Does not capture uncertainty over study choice, source exclusions, stimulus sampling or feature selection','Two transfer tests share source data and are not independent replications','Percentile bootstrap of tuned models is an approximation; nominal coverage is not independently established',f'At {draws} draws, each 2.5% interval tail uses approximately {draws*.025:g} observations and retains Monte Carlo variation','Survey credibility is contemporaneous same-rater information, not deployable objective telemetry'],'elapsed_seconds':time.monotonic()-start,'checks':{'inner_duplicate_leakage_assertions_passed':True,'train_test_original_ID_disjointness_passed':True,'all_metrics_finite':True}}
    (out/'voice_retraining_bootstrap.json').write_text(json.dumps(meta,indent=2))
    print(summary[summary.metric.str.contains('reduction|gain')].to_string(index=False),flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--draws',type=int,default=1000);args=parser.parse_args();run(args.draws)
