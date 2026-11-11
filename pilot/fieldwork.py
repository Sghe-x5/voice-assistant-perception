"""Offline natural-dialogue preparation and descriptive coder agreement.

Separate from fixed-task pilot schema. No model calls, population inference,
automated anonymization or inference of human subjective ratings.
"""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import re

if __package__:
    from .analyze_pilot import load_json, number, text, timestamp
    from . import question_coding as qc
else:
    from analyze_pilot import load_json, number, text, timestamp
    import question_coding as qc

SETS = {
    'task_family': {'fact','state_action','constrained_planning','explanation','creative','social','mixed','unknown'},
    'information_state': {'sufficient','missing_parameter','ambiguous_reference','conflicting_constraints','unknown'},
    'assistant_action': {'answer','act','targeted_question','broad_repeat','explicit_assumption','acknowledge_error','revise','refuse','other','unknown'},
}
SCALARS = {
    'repair_outcome': {'resolved','partial','unresolved','abandoned','not_applicable','unknown'},
    'objective_result': {'success','partial','failure','unscorable','unknown'},
}
FIELDS = {**SETS, **SCALARS}
ORIGINS = {'human_assistant_recorded','human_human_recorded','retrospective_report'}
MODES = {'live_voice','voice_text','text','human_human'}
ROLES = {'developer_pilot','volunteer'}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(evidence):
    return hashlib.sha256(json.dumps(evidence, sort_keys=True, ensure_ascii=False,
                                     allow_nan=False).encode('utf-8')).hexdigest()


def prepare(paths):
    """Validate researcher-entered diaries and prepare unlabelled private evidence."""
    evidence=[]; people=set(); seen=set(); sources=[]
    for path in paths:
        d=load_json(path)
        require(isinstance(d,dict) and d.get('schema_version') in ('field-diary-1.0','field-diary-1.1'),'Expected field-diary-1.0 or 1.1')
        pid=d.get('participant_code')
        require(isinstance(pid,str) and re.fullmatch(r'P-[0-9a-f]{12}',pid),'Invalid pseudonymous participant code')
        require(pid not in people,'Duplicate participant diary; explicitly consolidate snapshots first')
        people.add(pid)
        raw=Path(path).read_bytes()
        sources.append(dict(participant_code=pid,sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw)))
        require(isinstance(d.get('sampling_role'),str) and d['sampling_role'] in ROLES,'Explicit sampling_role required')
        require(d.get('analysis_permission') is True and d.get('redaction_reviewed') is True,
                'Document analysis permission and human redaction review before preparing packets')
        rows=d.get('episodes')
        require(isinstance(rows,list) and bool(rows),'A diary needs real episodes; a blank template is not data')
        for row in rows:
            require(isinstance(row,dict),'Episode must be an object')
            for field in ('episode_id','session_id'):
                require(isinstance(row.get(field),str) and re.fullmatch(r'[A-Za-z0-9_-]+',row[field]),'Invalid '+field)
            key=(pid,row['episode_id'])
            require(key not in seen,'Duplicate episode');seen.add(key)
            require(isinstance(row.get('evidence_origin'),str) and row['evidence_origin'] in ORIGINS,'Only consented human episodes; no agent/synthetic runs')
            require(isinstance(row.get('modality'),str) and row['modality'] in MODES,'Unknown modality')
            require(row['evidence_origin']!='human_human_recorded' or row['modality']=='human_human','Human-human modality mismatch')
            require(row['modality']!='human_human' or row['evidence_origin']!='human_assistant_recorded','Assistant modality mismatch')
            require(timestamp(row.get('recorded_at')) is not None,'Timezone-aware diary entry timestamp required')
            for field in ('goal','context','account','product','version'):
                require(text(row.get(field)),field+' must be explicit text; unknown may be stated')
            require('smartness' in row and (row['smartness'] is None or number(row['smartness'],1,7,True)),
                    'smartness must be a human integer 1..7 or explicit null')
            extra=qc.detail(row,d['sampling_role'],legacy=d['schema_version']=='field-diary-1.0')
            evidence.append(dict(participant_code=pid,sampling_role=d['sampling_role'],**{k:row[k] for k in
                ('episode_id','session_id','evidence_origin','modality','goal','context','account')},**extra))
    require(bool(evidence),'No evidence supplied')
    evidence.sort(key=lambda r:(r['participant_code'],r['episode_id']))
    return dict(schema_version='field-coding-1.1',codebook_version='0.2',
                coder_id=None,coder_origin=None,evidence_sha256=digest(evidence),evidence=evidence,source_manifest=sources,
                annotations=[dict(participant_code=e['participant_code'],episode_id=e['episode_id'],
                                  **{k:None for k in FIELDS},evidence_reference=None,
                                  episode_familiarity=None,questions=qc.blank_questions(e)) for e in evidence],
                caveat='Metadata blinding only: manually inspect text for names, brands and ratings. Permission/coder identity are attestations, not independently verified.')


def write_packets(packet, output):
    blinded={k:v for k,v in packet.items() if k!='source_manifest'}
    documents={f'coder-{name}.json':blinded for name in ('a','b')}
    documents['preparation-manifest.json']=dict(evidence_sha256=packet['evidence_sha256'],sources=packet['source_manifest'])
    serialized={name:json.dumps(doc,ensure_ascii=False,indent=2,allow_nan=False)+'\n' for name,doc in documents.items()}
    output=Path(output);output.mkdir(parents=True,exist_ok=False);created=[]
    try:
        for name,payload in serialized.items():
            path=output/name
            with path.open('x',encoding='utf-8') as stream:
                created.append(path);stream.write(payload)
    except BaseException:
        for path in created:
            try:path.unlink()
            except OSError:pass
        try:output.rmdir()
        except OSError:pass
        raise


def _validate_packet(p):
    require(isinstance(p,dict),'Packet must be an object')
    version=(p.get('schema_version'),p.get('codebook_version'))
    require(version in (('field-coding-1.0','0.1'),('field-coding-1.1','0.2')),'Unknown coding version pair')
    modern=version[0]=='field-coding-1.1'
    require(p.get('coder_origin')=='human' and text(p.get('coder_id')),'Explicit distinct human coder IDs required')
    ev=p.get('evidence');rows=p.get('annotations')
    require(isinstance(ev,list) and bool(ev) and all(isinstance(e,dict) for e in ev),'Missing evidence')
    require(digest(ev)==p.get('evidence_sha256'),'Evidence changed after packet creation')
    keys=[]
    evidence_by_key={}
    for e in ev:
        require(all(text(e.get(k)) for k in ('participant_code','episode_id','session_id')),'Invalid evidence identity')
        require(isinstance(e.get('evidence_origin'),str) and e['evidence_origin'] in ORIGINS
                and isinstance(e.get('modality'),str) and e['modality'] in MODES
                and isinstance(e.get('sampling_role'),str) and e['sampling_role'] in ROLES,'Invalid evidence provenance')
        key=(e['participant_code'],e['episode_id']);keys.append(key);evidence_by_key[key]=e
        if modern:
            require(e.get('detail_status') in ('legacy_unavailable','turn_detail'),'Explicit detail status required')
            if e['detail_status']=='turn_detail':qc.detail(e,e['sampling_role'])
            else:require(e.get('turns')==[] and e.get('question_units')==[] and e.get('turn_coverage')=='unknown'
                         and e.get('coding_partition')=='unassigned','Legacy detail cannot contain invented units')
        else:
            require(not any(k in e for k in ('turns','question_units','turn_coverage','coding_partition','detail_status')),
                    'Legacy packet cannot silently discard modern question detail')
    require(len(keys)==len(set(keys)),'Duplicate evidence')
    require(isinstance(rows,list),'Annotations must be an array')
    labels={}
    for r in rows:
        require(isinstance(r,dict) and all(text(r.get(k)) for k in ('participant_code','episode_id')),'Invalid annotation identity')
        key=(r['participant_code'],r['episode_id'])
        require(key in keys and key not in labels,'Unknown/duplicate annotation')
        extra={'episode_familiarity','questions'} if modern else set()
        require(set(r)=={'participant_code','episode_id','evidence_reference',*FIELDS,*extra},'Exact annotation fields required')
        if modern:
            require(r['episode_familiarity'] is None or (isinstance(r['episode_familiarity'],str)
                    and r['episode_familiarity'] in qc.FAMILIARITY),'Invalid episode familiarity')
            qc.validate_questions(evidence_by_key[key],r['questions'])
        for field,options in FIELDS.items():
            value=r[field]
            if value is None:continue
            if field in SETS:
                require(isinstance(value,list) and bool(value) and all(isinstance(x,str) for x in value),'Nonempty label arrays or null required')
                require(len(value)==len(set(value)) and set(value)<=options,'Unknown/duplicate '+field)
                require('unknown' not in value or value==['unknown'],'Unknown cannot accompany determined labels')
            else:require(isinstance(value,str) and value in options,'Unknown '+field)
        if any(r[k] is not None for k in FIELDS):require(text(r.get('evidence_reference')),'Labelled rows need an evidence reference')
        labels[key]=r
    require(set(keys)==set(labels),'Keep all evidence rows; missing labels are explicit null')
    return labels


def agreement(a,b):
    """Nominal Cohen kappa on supplied pairs; constant marginals -> undefined."""
    require(len(a)==len(b),'Paired lengths differ')
    n=len(a)
    if not n:return dict(n_paired=0,agreement=None,kappa=None)
    ca,cb=Counter(a),Counter(b)
    observed=sum(x==y for x,y in zip(a,b))/n
    expected=sum(ca[k]*cb[k] for k in ca.keys()|cb.keys())/(n*n)
    return dict(n_paired=n,agreement=observed,kappa=(observed-expected)/(1-expected) if expected<1 else None)


def _known(x):
    return x is not None and x!='unknown' and x!=['unknown']


def compare(a,b):
    la,lb=_validate_packet(a),_validate_packet(b)
    require(a['schema_version']==b['schema_version'] and a['codebook_version']==b['codebook_version'],
            'Do not pool codebook versions; explicitly recode both packets')
    require(a['coder_id'].strip()!=b['coder_id'].strip(),'Coders must be distinct')
    require(a['evidence']==b['evidence'],'Compare identical evidence packets only')
    groups=defaultdict(list)
    for e in a['evidence']:
        key=(e['participant_code'],e['episode_id'])
        fam=qc.familiarity(la[key].get('episode_familiarity'),lb[key].get('episode_familiarity'))
        groups[(e['sampling_role'],e['evidence_origin'],e['modality'],e.get('coding_partition','unassigned'),fam)].append(e)
    strata=[]
    for (role,origin,mode,partition,fam),evidence in sorted(groups.items()):
        fields={}
        for field in FIELDS:
            pairs=[(la[e['participant_code'],e['episode_id']][field],lb[e['participant_code'],e['episode_id']][field]) for e in evidence]
            known=[(x,y) for x,y in pairs if _known(x) and _known(y)]
            if field in SETS:
                normalized=[(tuple(sorted(x)),tuple(sorted(y))) for x,y in known]
                result=agreement([x for x,y in normalized],[y for x,y in normalized])
                # Kappa on arbitrary label-set combinations is not reported.
                result.pop('kappa')
                result['per_label']={label:{**agreement([label in x for x,y in known],[label in y for x,y in known]),
                                               'positive_a':sum(label in x for x,y in known),'positive_b':sum(label in y for x,y in known)}
                                     for label in sorted(FIELDS[field]-{'unknown'})}
            else:result=agreement([x for x,y in known],[y for x,y in known])
            result.update(n_missing_a=sum(x is None for x,y in pairs),n_missing_b=sum(y is None for x,y in pairs),
                          n_unknown_a=sum(x=='unknown' or x==['unknown'] for x,y in pairs),
                          n_unknown_b=sum(y=='unknown' or y==['unknown'] for x,y in pairs))
            result['confusion']=[{'a':str(x),'b':str(y),'count':n} for (x,y),n in Counter(
                (tuple(sorted(x)) if isinstance(x,list) else x,tuple(sorted(y)) if isinstance(y,list) else y) for x,y in known).items()]
            fields[field]=result
        qa=[];qb=[]
        for e in evidence:
            key=(e['participant_code'],e['episode_id'])
            left={(q['turn_id'],q['parameter_id']):q for q in la[key].get('questions',[])}
            right={(q['turn_id'],q['parameter_id']):q for q in lb[key].get('questions',[])}
            for unit in sorted(left):qa.append(left[unit]);qb.append(right[unit])
        qfields={}
        for name in qc.QUESTION_FIELDS:
            pairs=[(x[name],y[name]) for x,y in zip(qa,qb)]
            known=[(x,y) for x,y in pairs if _known(x) and _known(y)]
            qfields[name]={**agreement([x for x,y in known],[y for x,y in known]),
                          'n_missing_a':sum(x is None for x,y in pairs),'n_missing_b':sum(y is None for x,y in pairs),
                          'n_unknown_a':sum(x=='unknown' for x,y in pairs),'n_unknown_b':sum(y=='unknown' for x,y in pairs),
                          'confusion':[dict(a=x,b=y,count=n) for (x,y),n in Counter(known).items()]}
        questions=dict(n_units=len(qa),n_episodes_with_turn_detail=sum(e.get('detail_status')=='turn_detail' for e in evidence),
                       n_episodes_without_turn_detail=sum(e.get('detail_status')!='turn_detail' for e in evidence),fields=qfields)
        strata.append(dict(sampling_role=role,evidence_origin=origin,modality=mode,coding_partition=partition,
                           familiarity=fam,n_episodes=len(evidence),
                           n_participant_codes=len({e['participant_code'] for e in evidence}),fields=fields,questions=questions))
    return dict(analysis='descriptive_intercoder_agreement',population_inference=False,
                evidence_sha256=a['evidence_sha256'],strata=strata,
                caveats=['Repeated episodes are dependent; no inferential intervals or population claims.',
                         'Unknown/unlabelled pairs are excluded, with counts reported; they are not negative labels.',
                         'Agreement does not establish truth, construct validity or independently verified human authorship.',
                         'Authors can remember episodes despite hidden metadata. Familiarity and held-out status are reported attestations.',
                         'Question metrics condition on a frozen candidate inventory; they do not validate that all questions/parameters were found.',
                         'Do not publish private packets or small-cell reports without a separate release decision.'])


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='command',required=True)
    p=sub.add_parser('prepare');p.add_argument('diaries',nargs='+',type=Path);p.add_argument('--output',required=True,type=Path)
    p=sub.add_parser('compare');p.add_argument('coder_a',type=Path);p.add_argument('coder_b',type=Path);p.add_argument('--output',required=True,type=Path)
    args=parser.parse_args()
    try:
        if args.command=='prepare':write_packets(prepare(args.diaries),args.output)
        else:
            report=compare(load_json(args.coder_a),load_json(args.coder_b))
            with args.output.open('x',encoding='utf-8') as stream:json.dump(report,stream,ensure_ascii=False,indent=2,allow_nan=False)
    except (ValueError,OSError) as exc:parser.error(str(exc))
    print('Local output saved. No data transmitted and no population inference.')


if __name__=='__main__':main()
