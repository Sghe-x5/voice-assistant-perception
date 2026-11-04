"""Turn-anchored question coding within fieldwork, not automatic intent inference.

An observed utterance does not establish what reached the model. Assistant
availability is supported only by a recorded pre-question input snapshot.
"""
import re

QUESTION_FIELDS = ('is_question','request_kind','user_information_before','assistant_information_before')
FAMILIARITY = {'own_episode','seen_before','new_to_coder','unknown'}
PARTITIONS = {'development','held_out','unassigned'}
KINDS = {'new_information_request','repeat_known_information','confirmation','other','unknown'}
USER_STATES = {'supplied','not_supplied','conflicting','unknown'}
ASSISTANT_STATES = {'available','absent','conflicting','unknown'}


def need(ok, message):
    if not ok:raise ValueError(message)


def nonempty(value):
    return isinstance(value,str) and bool(value.strip())


def safe_id(value):
    return isinstance(value,str) and re.fullmatch(r'[A-Za-z0-9_-]+',value) is not None


def detail(row, role, legacy=False):
    """Validate order and source links; never derive them from free-form account."""
    if legacy:
        need(not any(k in row for k in ('turns','question_units','turn_coverage','coding_partition')),
             'Version 1.0 cannot silently discard new detail; explicitly use field-diary-1.1')
        return dict(detail_status='legacy_unavailable',turns=[],question_units=[],
                    turn_coverage='unknown',coding_partition='unassigned')
    need(row.get('turn_coverage') in ('complete','partial','unknown'),'Explicit turn coverage required')
    partition=row.get('coding_partition')
    need(isinstance(partition,str) and partition in PARTITIONS,'Explicit coding partition required')
    need(not (role=='developer_pilot' and partition=='held_out'),'Author episodes cannot be independent held-out validation')
    turns=row.get('turns');units=row.get('question_units')
    need(isinstance(turns,list) and isinstance(units,list),'turns and question_units must be arrays')
    byid={}
    for turn in turns:
        need(isinstance(turn,dict) and set(turn)=={'turn_id','speaker','text','evidence_reference','assistant_context_before'},'Exact turn fields required')
        tid=turn['turn_id']
        need(safe_id(tid) and tid not in byid,'Invalid/duplicate turn ID')
        need(turn['speaker'] in ('user','assistant','tool'),'Unknown turn speaker')
        need(nonempty(turn['text']) and nonempty(turn['evidence_reference']),'Turn text and source reference required')
        snap=turn['assistant_context_before']
        if snap is not None:
            need(turn['speaker']=='assistant','Pre-question input snapshots belong to assistant turns')
            need(isinstance(snap,dict) and set(snap)=={'text','source','complete','evidence_reference'},'Exact snapshot fields required')
            need(isinstance(snap['text'],str) and snap['source'] in ('request_log','controlled_script')
                 and type(snap['complete']) is bool and nonempty(snap['evidence_reference']),
                 'Snapshot needs observed source, explicit completeness and provenance; unknown input is null')
        byid[tid]=turn
    seen=set()
    for unit in units:
        need(isinstance(unit,dict) and set(unit)=={'turn_id','parameter_id','parameter_definition'},'Exact question unit fields required')
        need(safe_id(unit['turn_id']) and safe_id(unit['parameter_id']) and nonempty(unit['parameter_definition']),'Invalid question/parameter identity')
        key=(unit['turn_id'],unit['parameter_id'])
        need(key not in seen and unit['turn_id'] in byid and byid[unit['turn_id']]['speaker']=='assistant',
             'Question units must uniquely reference an assistant turn')
        seen.add(key)
    return dict(detail_status='turn_detail',turns=turns,question_units=units,
                turn_coverage=row['turn_coverage'],coding_partition=partition)


def blank_questions(evidence):
    return [dict(turn_id=u['turn_id'],parameter_id=u['parameter_id'],is_question=None,
                 request_kind=None,user_information_before=None,assistant_information_before=None,
                 user_evidence=[],assistant_evidence=[],candidate_value=None,coding_note=None)
            for u in evidence['question_units']]


def validate_questions(evidence, annotations):
    """Check evidence chronology/channel and contradictory labels, not semantics."""
    need(isinstance(annotations,list),'questions must be an array')
    turns=evidence['turns'];byid={t['turn_id']:(i,t) for i,t in enumerate(turns)}
    expected={(u['turn_id'],u['parameter_id']) for u in evidence['question_units']}
    seen={}
    for q in annotations:
        need(isinstance(q,dict) and set(q)=={'turn_id','parameter_id',*QUESTION_FIELDS,
             'user_evidence','assistant_evidence','candidate_value','coding_note'},'Exact question annotation fields required')
        need(safe_id(q['turn_id']) and safe_id(q['parameter_id']),'Invalid question annotation ID')
        key=(q['turn_id'],q['parameter_id'])
        need(key in expected and key not in seen,'Unknown/duplicate question annotation')
        seen[key]=q;pos,turn=byid[q['turn_id']]
        need(q['is_question'] is None or type(q['is_question']) is bool,'is_question must be true/false/null')
        for field,values in [('request_kind',KINDS),('user_information_before',USER_STATES),('assistant_information_before',ASSISTANT_STATES)]:
            need(q[field] is None or (isinstance(q[field],str) and q[field] in values),'Invalid '+field)
        need(isinstance(q['user_evidence'],list) and isinstance(q['assistant_evidence'],list),'Evidence arrays required')
        if q['is_question'] is not True:
            need(all(q[k] is None for k in QUESTION_FIELDS[1:]) and not q['user_evidence']
                 and not q['assistant_evidence'] and q['candidate_value'] is None,'Do not label an unconfirmed/non-question as a request')
            if q['is_question'] is False:need(nonempty(q['coding_note']),'Non-question decision needs a reason')
            continue
        need(nonempty(q['coding_note']),'Question coding needs parameter-linked reasoning')
        user_refs=set()
        for ref in q['user_evidence']:
            need(isinstance(ref,dict) and set(ref)=={'turn_id','quote'} and safe_id(ref['turn_id']) and nonempty(ref['quote']),'Invalid user evidence reference')
            tid=ref['turn_id'];quote=ref['quote']
            need(tid in byid and byid[tid][0]<pos and byid[tid][1]['speaker']=='user',
                 'User evidence must precede the question and refer to a user turn')
            need(quote in byid[tid][1]['text'],'User evidence quote is not in the referenced turn')
            need((tid,quote) not in user_refs,'Duplicate user evidence');user_refs.add((tid,quote))
        us=q['user_information_before']
        if us in ('supplied','conflicting'):need(len(user_refs)>=(2 if us=='conflicting' else 1),'User state needs supporting evidence')
        else:need(not user_refs,'No positive user evidence for unknown/absent/unlabelled state')
        if us=='not_supplied':need(evidence['turn_coverage']=='complete','Partial turn coverage cannot establish user absence')
        snap=turn['assistant_context_before'];state=q['assistant_information_before'];quotes=q['assistant_evidence']
        need(all(nonempty(x) for x in quotes) and len(quotes)==len(set(quotes)),'Invalid/duplicate assistant evidence')
        if state in ('available','conflicting','absent'):
            need(snap is not None,'Unobserved model input cannot establish availability or absence')
            need(all(x in snap['text'] for x in quotes),'Assistant evidence must come from the PRE-question input snapshot')
        if state in ('available','conflicting'):need(len(quotes)>=(2 if state=='conflicting' else 1),'Assistant state needs supporting input quotes')
        else:need(not quotes,'No positive assistant evidence for unknown/absent/unlabelled state')
        if state=='absent':need(snap['complete'],'An incomplete input snapshot cannot establish absence')
        kind=q['request_kind']
        if kind=='new_information_request':need(state=='absent','New-information request requires absence in observed assistant input')
        if kind=='repeat_known_information':need(state=='available','Repeated-known request requires available assistant input, not merely user speech')
        if kind=='confirmation':
            need(nonempty(q['candidate_value']) and q['candidate_value'] in turn['text'],
                 'Confirmation must present a candidate value in the question turn')
        else:need(q['candidate_value'] is None,'Candidate value is recorded only for confirmation')
    need(set(seen)==expected,'Keep every candidate unit; null means unlabelled and false means not a question')
    return seen


def familiarity(a,b):
    if any(x in ('own_episode','seen_before') for x in (a,b)):return 'familiar_to_at_least_one'
    if a==b=='new_to_coder':return 'unfamiliar_to_both_reported'
    return 'unknown'
