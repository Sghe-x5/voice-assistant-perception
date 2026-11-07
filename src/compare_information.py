"""Paired contrasts between information sets on identical held-out people.

Exploratory addition after initial analyses. Not a new causal estimator. The
bootstrap conditions on already fitted predictions; no cross-dataset pooling.
"""
from pathlib import Path
import os,json
ROOT=Path(__file__).resolve().parents[1]
os.environ.setdefault('MPLCONFIGDIR',str(ROOT/'.mplconfig'))
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

def paired(y,operational,survey):
    y=np.asarray(y);a=np.asarray(operational);b=np.asarray(survey)
    assert y.shape==a.shape==b.shape and np.isfinite(np.c_[y,a,b]).all()
    den=np.mean((y-y.mean())**2)
    return (np.mean((y-a)**2)-np.mean((y-b)**2))/den, np.mean(np.abs(y-a)-np.abs(y-b))

def main():
    r=ROOT/'results';cases=[]
    v=pd.read_csv(r/'voice_predictions.csv')
    for split in ['E1_to_E2','E2_to_E1_assertive']:
        d=v[v['split']==split].pivot(index='participant',columns='model',values='prediction')
        y=v[v['split']==split].groupby('participant').y.first().reindex(d.index)
        cases.append((f'Voice {split}',y,d.design_user,d.credibility_only,'1–7 intelligence','design and reported user attributes'))
    increments=[]
    for split in ['participant','condition']:
        d=pd.read_csv(r/f'cocreation_predictions_{split}.csv')
        cases.append((f'Co-creation {split}',d.observed,d.telemetry,d.same_survey_benchmark,'1–5 adapted intelligence','design, reported user attributes and logs'))
        for name in ['telemetry','telemetry_adoption']:
            gain,reduction=paired(d.observed,d.design_user,d[name])
            increments.append({'split':split,'model':name,'comparator':'design_user','r2_gain':gain,'mae_reduction':reduction})
    pd.DataFrame(increments).to_csv(r/'cocreation_increment_vs_design.csv',index=False)
    l=pd.read_csv(r/'latency_predictions.csv')
    for target in ['Rating_thoughtfulness','Rating_usefulness']:
        d=l[l.target==target].groupby(['participant','model']).predicted.mean().unstack()
        y=l[l.target==target].groupby('participant')['observed'].first().reindex(d.index)
        cases.append((target.removeprefix('Rating_').capitalize()+' (text)',y,d.design_telemetry,d.survey_diagnostic,'1–7 '+target.removeprefix('Rating_'),'design and logs; averaged repeated OOF predictions'))
    rows=[];rng=np.random.default_rng(20261104)
    for name,y,a,b,scale,block in cases:
        y,a,b=map(np.asarray,(y,a,b));gap,mae=paired(y,a,b)
        boot=[]
        for _ in range(4000):
            ix=rng.integers(0,len(y),len(y));boot.append(paired(y[ix],a[ix],b[ix]))
        lo,hi=np.quantile(boot,[.025,.975],axis=0)
        rows.append({'comparison':name,'n':len(y),'scale':scale,'comparison_feature_block':block,'r2_gain_survey':gap,
                     'r2_gain_low':lo[0],'r2_gain_high':hi[0],'mae_reduction_survey':mae,'mae_reduction_low':lo[1],'mae_reduction_high':hi[1]})
    out=pd.DataFrame(rows);out.to_csv(r/'information_gap.csv',index=False)
    fig,ax=plt.subplots(figsize=(9,4.8),layout='constrained')
    ax.errorbar(out.r2_gain_survey,np.arange(len(out)),xerr=[out.r2_gain_survey-out.r2_gain_low,out.r2_gain_high-out.r2_gain_survey],fmt='o',capsize=4,color='#21618c')
    ax.axvline(0,color='#777',lw=1);ax.set_yticks(np.arange(len(out)),['Voice: E1 → E2','Voice: E2 → E1 assertive','Co-creation: participant CV','Co-creation: condition holdout','Text: thoughtfulness','Text: usefulness'])
    ax.invert_yaxis();ax.set_xlabel('R² gain from concurrent ratings (2.5–97.5% resampling percentiles)')
    ax.set_title('Information-source contrasts; different endpoints, no pooled effect')
    fig.savefig(r/'figures/information_gap.png',dpi=180);plt.close(fig)
    (r/'information_gap_metadata.json').write_text(json.dumps({'bootstrap':4000,'seed':20261104,'analysis_status':'post-hoc exploratory contrast',
       'interpretation':'Concurrent evaluative judgments vs the named comparison feature set; not an identified common-method-bias effect.',
       'limitations':['Different outcomes and scales; do not pool','Overlapping test sets across validations are not independent replications','Intervals condition on trained predictions','Text OOF row resampling does not account for CV dependence; confidence coverage is unestablished','Latency contrast uses averaged repeated OOF predictions, not average per-repeat R2']},indent=2))
    print(out.to_string(index=False))

if __name__=='__main__':main()
