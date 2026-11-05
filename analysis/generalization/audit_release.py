"""Offline audit of the pinned Vafa et al. public release; no raw-row export.

Separate endpoint from perceived intelligence. No author code/checkpoint is run.
Question overlap is reported descriptively, not automatically called leakage.
"""
import argparse
from collections import Counter, defaultdict
import csv
import hashlib
import io
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
COLUMNS=('q1','q2','source1','source2','previous_correct','belief_change')


def read_verified(path, expected_sha256):
    raw=Path(path).read_bytes()
    if hashlib.sha256(raw).hexdigest()!=expected_sha256:
        raise ValueError('Pinned source hash mismatch: '+Path(path).name)
    # CSV is data only; no execution/import of the upstream repository.
    return list(csv.DictReader(io.StringIO(raw.decode('utf-8'),newline='')))


def validate(rows):
    if not rows:raise ValueError('Empty release table')
    for row in rows:
        if set(row)!=set(COLUMNS) or any(not isinstance(row[c],str) or not row[c].strip() for c in COLUMNS):
            raise ValueError('Expected six complete source fields')
        if row['previous_correct'] not in ('0','1') or row['belief_change'] not in ('0','1'):
            raise ValueError('Expected binary source labels')


def pair(row):
    return row['q1'],row['q2'],row['previous_correct']


def summarize(rows):
    groups=defaultdict(set)
    for row in rows:groups[pair(row)].add(row['belief_change'])
    return dict(rows=len(rows),columns=list(COLUMNS),missing=0,
                labels=dict(Counter(r['belief_change'] for r in rows)),
                previous_correct=dict(Counter(r['previous_correct'] for r in rows)),
                unique_q1=len({r['q1'] for r in rows}),unique_q2=len({r['q2'] for r in rows}),
                task_count=len({r[c] for r in rows for c in ('source1','source2')}),
                duplicate_complete_rows=len(rows)-len({tuple(r[c] for c in COLUMNS) for r in rows}),
                duplicate_conditioned_pairs=len(rows)-len(groups),
                conditioned_pairs_with_both_labels=sum(len(v)>1 for v in groups.values()))


def audit_rows(train,test):
    validate(train);validate(test)
    train_questions={r[c] for r in train for c in ('q1','q2')}
    train_tasks={r[c] for r in train for c in ('source1','source2')}
    test_tasks={r[c] for r in test for c in ('source1','source2')}
    return dict(files={'train':summarize(train),'test':summarize(test)},
                overlap=dict(exact_conditioned_pairs=len({pair(r) for r in train}&{pair(r) for r in test}),
                             exact_unconditioned_pairs=len({(r['q1'],r['q2']) for r in train}&{(r['q1'],r['q2']) for r in test}),
                             test_q1_seen_in_either_training_role_rows=sum(r['q1'] in train_questions for r in test),
                             test_q2_seen_in_either_training_role_rows=sum(r['q2'] in train_questions for r in test),
                             test_rows_both_questions_seen=sum(r['q1'] in train_questions and r['q2'] in train_questions for r in test),
                             test_rows_both_questions_unseen=sum(r['q1'] not in train_questions and r['q2'] not in train_questions for r in test),
                             test_only_tasks=sorted(test_tasks-train_tasks)),
                limitations=['Exact text comparison only; no semantic/near-duplicate audit.',
                             'No respondent IDs, direct intelligence, original priors/posteriors or voice measurements in these six columns.',
                             'Repeated rows/discordant labels may be legitimate repeated judgments; nothing is deduplicated.',
                             'Selected aggregated test pairs do not estimate population prevalence or individual calibration.'])


def replicate_baselines(train,test):
    import math
    import numpy as np
    import sklearn
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import log_loss, roc_auc_score
    y=np.array([int(r['belief_change']) for r in test])
    train_y=np.array([int(r['belief_change']) for r in train])
    features=lambda rows:np.array([[int(r['previous_correct']),int(r['source1']==r['source2'])] for r in rows])
    x,xt=features(train),features(test)
    if set(y)!={0,1} or set(train_y)!={0,1} or set(x[:,0])!={0,1}:
        raise ValueError('Both correctness and outcome classes required for this reproduction')
    rates={c:train_y[x[:,0]==c].mean() for c in (0,1)}
    predictions={'previous_correct':np.array([rates[c] for c in xt[:,0]]),
                 'previous_correct_and_same_task':LogisticRegression(C=1.0,solver='lbfgs',max_iter=100,tol=1e-4).fit(x,train_y).predict_proba(xt)[:,1]}
    result={}
    for name,pred in predictions.items():
        if not np.all((pred>0)&(pred<1)):raise ValueError('Boundary probabilities need explicit handling')
        nll=float(log_loss(y,pred));auc=float(roc_auc_score(y,pred))
        direct_nll=-sum(math.log(p if yy else 1-p) for yy,p in zip(y,pred))/len(y)
        positive,negative=pred[y==1],pred[y==0]
        direct_auc=float(((positive[:,None]>negative).sum()+.5*(positive[:,None]==negative).sum())/(len(positive)*len(negative)))
        if abs(nll-direct_nll)>1e-12 or abs(auc-direct_auc)>1e-12:
            raise AssertionError('Independent metric calculation mismatch')
        result[name]=dict(nll=nll,auc=auc,independent_nll_error=abs(nll-direct_nll),independent_auc_error=abs(auc-direct_auc))
    return dict(sklearn_version=sklearn.__version__,models=result,
                scope='Only two non-text baselines; no BERT/LLM reproduction, tuning on test, intervals or causal claims.')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',required=True,type=Path,help='Local upstream repository root')
    parser.add_argument('--output',required=True,type=Path,help='New aggregate JSON file')
    parser.add_argument('--baselines',action='store_true')
    args=parser.parse_args()
    manifest=json.loads((HERE/'source_manifest.json').read_text(encoding='utf-8'))
    try:
        data={name:read_verified(args.source/item['path'],item['sha256']) for name,item in manifest['files'].items()}
        report=audit_rows(data['train'],data['test']);report['provenance']=manifest
        if args.baselines:report['baseline_replication']=replicate_baselines(data['train'],data['test'])
        report['script_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
        with args.output.open('x',encoding='utf-8') as stream:json.dump(report,stream,ensure_ascii=False,indent=2,allow_nan=False)
    except (ValueError,OSError) as exc:parser.error(str(exc))
    print('Saved aggregate-only audit; originals unchanged.')


if __name__=='__main__':main()
