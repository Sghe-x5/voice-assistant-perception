#!/usr/bin/env python3
"""Local research inference: python src/predict_voice.py --input input.json
JSON fields: partner, assertive, age_years, female, diverse_gender, owner,
information_search (1–7 for owners, null for nonowners).
"""
from pathlib import Path
import argparse,json,sys
import joblib
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]

def predict(record):
    card=json.loads((ROOT/'models/voice_model_card.json').read_text())
    required=card['features']
    if set(record)!=set(required):raise ValueError(f'Expected exactly these fields: {required}')
    for key in ['partner','assertive','female','diverse_gender','owner']:
        if type(record[key]) not in (int,float) or record[key] not in (0,1):raise ValueError(f'{key} must be numeric 0 or 1')
    if record['female']+record['diverse_gender']>1:raise ValueError('Source gender indicators must be mutually exclusive')
    age=record['age_years']
    if type(age) not in (int,float) or not 20<=age<=76:raise ValueError('age_years must be within the observed source range 20–76')
    freq=record['information_search']
    if record['owner']==0 and freq is not None:raise ValueError('Nonowner information_search must be null (structurally unobserved)')
    if record['owner']==1 and (type(freq) not in (int,float) or not 1<=freq<=7):raise ValueError('Owner information_search must be within 1–7')
    # Only load the locally generated, trusted model artifact; never an arbitrary pickle URL.
    model=joblib.load(ROOT/'models/voice_design_user.joblib')
    val=float(model.predict(pd.DataFrame([record],columns=required))[0])
    return {'predicted_mean_rating':val,'rating_scale':[1,7],'prediction_interval':None,'model':'voice_design_user','status':'research baseline; weak external predictive validity','scope':'UK English-language recorded voice-vignette judgments','warning':'Not a measure of actual intelligence; no calibrated individual uncertainty interval. Final all-data fit was not independently tested.'}

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--input',required=True,help='JSON file, or - for stdin');args=ap.parse_args()
    try:
        raw=sys.stdin.read() if args.input=='-' else Path(args.input).read_text()
        result=predict(json.loads(raw));print(json.dumps(result,indent=2))
    except (ValueError,TypeError,FileNotFoundError) as e:
        print(json.dumps({'error':str(e)}),file=sys.stderr);return 2
    return 0

if __name__=='__main__':raise SystemExit(main())
