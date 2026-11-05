"""Offline authored-stimulus pilot. Standard library only; no model calls."""
import argparse
from collections import Counter, defaultdict
import hashlib
import itertools
import json
from pathlib import Path
import random
import re
import shutil
from statistics import mean

if __package__:
    from .summaries import operation_score, paired_block, aggregate_blocks
    from .materials import VERSION, ARMS, CELLS, ABS_CELLS, RATINGS, CHECKS, ORDERS, TOOLS, PROCESS_ORDERS, RESOURCE_SCOPE, material
else:
    from summaries import operation_score, paired_block, aggregate_blocks
    from materials import VERSION, ARMS, CELLS, ABS_CELLS, RATINGS, CHECKS, ORDERS, TOOLS, PROCESS_ORDERS, RESOURCE_SCOPE, material

HERE = Path(__file__).resolve().parent


def require(ok, message):
    if not ok:
        raise ValueError(message)


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                     allow_nan=False, separators=(',', ':')).encode()).hexdigest()


def load(path):
    def pairs(items):
        d = {}
        for key, value in items:
            require(key not in d, 'Duplicate JSON key: ' + key)
            d[key] = value
        return d
    def bad(value):
        raise ValueError('Nonfinite JSON value: ' + value)
    return json.loads(Path(path).read_text(encoding='utf-8'), object_pairs_hook=pairs, parse_constant=bad)


def save_new(path, value):
    with Path(path).open('x', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write('\n')


def make_plan(seed, role='developer_pilot', origin='synthetic_test', study_info='Synthetic fixture', batch_id='test'):
    require(type(seed) is int and seed >= 0, 'Nonnegative integer seed required')
    require(role in ('developer_pilot', 'volunteer'), 'Invalid sampling role')
    require(origin in ('human_observer', 'synthetic_test'), 'Invalid evidence origin')
    require(origin != 'synthetic_test' or role == 'developer_pilot', 'Test runs cannot be volunteers')
    require(isinstance(study_info, str) and bool(study_info.strip()), 'Provide study contact, storage and withdrawal information')
    require(isinstance(batch_id, str) and re.fullmatch(r'[A-Za-z0-9_-]{1,80}', batch_id), 'Explicit safe batch ID required')
    allocations = []
    rng=random.Random(seed)
    nuisance=list(itertools.product(('schedule','inventory'),(0,1),PROCESS_ORDERS,range(4),('ratings_first','forecasts_first')))
    rng.shuffle(nuisance)
    for block_index,(topic,variant,process_order,order,measure_order) in enumerate(nuisance,1):
        cells=list(itertools.product(ARMS,TOOLS));rng.shuffle(cells)
        for arm,tools in cells:
            stimuli=material(topic,variant,arm,process_order)
            # Order ABSOLUTE probes; relative labels change when the executor swaps.
            ids={p['absolute_id']:p['id'] for p in stimuli['probes']}
            allocations.append(dict(stimuli=stimuli,block_id=f'B{block_index:03d}',future_tools=tools,
                probe_order=[ids[ABS_CELLS[i]] for i in ORDERS[order]],measure_order=measure_order))
    for i,a in enumerate(allocations,1):a['allocation_id']=f'S{i:03d}'
    instrument={name:hashlib.sha256((HERE/name).read_bytes()).hexdigest()
                for name in ('materials.py','study.py','summaries.py','form.html')}
    plan = dict(version=VERSION, status='planned_not_observed', seed=seed,
                sampling_role=role, evidence_origin=origin, study_info=study_info, batch_id=batch_id,
                instrument_sha256=instrument, allocations=allocations)
    plan['plan_sha256'] = digest(plan)
    return plan


def check_plan(plan):
    require(isinstance(plan, dict) and type(plan.get('seed')) is int, 'Invalid plan')
    unsigned={k:v for k,v in plan.items() if k!='plan_sha256'}
    require(digest(unsigned)==plan.get('plan_sha256'),'Plan hash does not match its exact JSON values')
    require(plan == make_plan(plan['seed'], plan.get('sampling_role'), plan.get('evidence_origin'),
                             plan.get('study_info'), plan.get('batch_id')),
            'Plan differs from this frozen material version')


def participant_payload(plan, allocation):
    a = allocation
    s = a['stimuli']
    return dict(version=VERSION, plan_sha256=plan['plan_sha256'], allocation_id=a['allocation_id'],
                sampling_role=plan['sampling_role'], evidence_origin=plan['evidence_origin'], study_info=plan['study_info'],
                measure_order=a['measure_order'], probe_order=a['probe_order'], ratings=RATINGS,
                future_tools=a['future_tools'],resource_scope=RESOURCE_SCOPE,
                exposure={k: s[k] for k in ('request', 'process', 'final')},
                probes=[{'id': p['id'], 'request': p['request']} for p in s['probes']])


def build(output, seed, role='developer_pilot', origin='human_observer', study_info=None, batch_id=None):
    plan = make_plan(seed, role, origin, study_info, batch_id)
    template = (HERE / 'form.html').read_text(encoding='utf-8')
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    try:
        save_new(output / 'plan.json', plan)
        for a in plan['allocations']:
            config = participant_payload(plan, a)
            # Only authored text goes into HTML; protect the script delimiter too.
            payload = json.dumps(config, ensure_ascii=False).replace('<', '\\u003c')
            (output / (a['allocation_id'] + '.html')).write_text(
                template.replace('/*CONFIG*/null', payload), encoding='utf-8')
        (output / 'ASSIGNMENT.txt').write_text(
            f"{len(plan['allocations'])} prospective slots, not participants or a sample-size justification.\n"
            'Each consecutive four-slot block balances executor assignment and future resources.\n'
            'Assign sequentially without inspecting condition. One person, one unused slot.\n'
            'Keep assignment/person mapping separately and private. Do not reassign abandoned slots.\n'
            'Each HTML is self-contained. Do not give participants the plan or other slots.\n', encoding='utf-8')
    except BaseException:
        shutil.rmtree(output)
        raise
    return plan


def optional_integer(value, low, high):
    return value is None or (type(value) is int and low <= value <= high)


def validate_export(d, plan):
    require(isinstance(d, dict), 'Export must be an object')
    require(set(d) == {'version', 'plan_sha256', 'allocation_id', 'participant_code', 'sampling_role',
                       'evidence_origin', 'mode', 'analysis_permission', 'status', 'ratings', 'forecasts',
                       'checks', 'presented', 'completed'}, 'Unexpected export fields')
    require(d['version'] == VERSION and d['plan_sha256'] == plan['plan_sha256'], 'Wrong material/plan version')
    a = next((a for a in plan['allocations'] if a['allocation_id'] == d['allocation_id']), None)
    require(a is not None, 'Unknown allocation')
    require(isinstance(d['participant_code'], str) and re.fullmatch(r'P-[0-9a-f]{12}', d['participant_code']), 'Use issued pseudonymous code')
    require(d['sampling_role'] in ('developer_pilot', 'volunteer'), 'Unknown sampling role')
    require(d['evidence_origin'] in ('human_observer', 'synthetic_test'), 'Unknown evidence origin')
    require(d['sampling_role'] == plan['sampling_role'] and d['evidence_origin'] == plan['evidence_origin'],
            'Origin and sampling role must match the issued plan')
    require(d['evidence_origin'] != 'synthetic_test' or d['sampling_role'] == 'developer_pilot', 'Tests cannot be volunteers')
    require(d['mode'] == 'text_vignette_observer', 'This instrument does not collect live voice experience')
    require(d['analysis_permission'] is True, 'No analysis permission')
    require(d['status'] in ('complete', 'partial'), 'Unsupported export status')
    require(isinstance(d['ratings'], dict) and set(d['ratings']) == set(RATINGS), 'Exact rating fields required')
    require(all(optional_integer(v, 1, 7) for v in d['ratings'].values()), 'Ratings must be integers 1..7 or null')
    require(isinstance(d['forecasts'], dict) and set(d['forecasts']) == set(CELLS), 'Exact forecast cells required')
    require(all(optional_integer(v, 0, 100) for v in d['forecasts'].values()), 'Forecasts must be integers 0..100 or null')
    require(isinstance(d['checks'], dict) and set(d['checks']) == set(CHECKS), 'Exact check fields required')
    for key in ('dependency_source','selection_source'):
        require(d['checks'][key] in (None,'assistant','component','unknown'),'Invalid source check')
    require(d['checks']['allocation'] in (None,'assigned','chosen','unknown'),'Invalid allocation check')
    comment=d['checks']['interpretation']
    require(comment is None or (isinstance(comment,str) and bool(comment.strip()) and len(comment)<=2000),'Invalid interpretation text')
    require(d['checks']['tools'] in (None, 'available', 'unavailable', 'unknown'), 'Invalid tool check')
    require(optional_integer(d['checks']['clarity'], 1, 7), 'Invalid clarity')
    expected = sequence(a)
    for key in ('presented', 'completed'):
        require(isinstance(d[key], list) and d[key] == expected[:len(d[key])], 'Pages must form the assigned prefix')
    require(len(d['completed']) <= len(d['presented']) <= len(d['completed']) + 1, 'Invalid page progress')
    require('exposure' in d['completed'], 'No completed exposure')
    if d['status'] == 'complete':
        require(d['completed'] == expected, 'Complete export must finish every page (answers may be null)')
    else:
        require(len(d['completed'])<len(expected),'Partial export cannot have every page completed')
    for key in RATINGS:
        page='checks' if key=='credit' else 'ratings'
        require(page in d['presented'] or d['ratings'][key] is None, 'Rating from unseen page')
    for cell in CELLS:
        require(cell in d['presented'] or d['forecasts'][cell] is None, 'Forecast from unseen page')
    require('checks' in d['presented'] or all(v is None for v in d['checks'].values()), 'Checks from unseen page')
    return a


def sequence(a):
    probes = a['probe_order']
    return ['exposure'] + (['ratings'] + probes if a['measure_order'] == 'ratings_first' else probes + ['ratings']) + ['checks']


def analyze(plan, documents):
    """Describe observed assigned arms. No imputation, p-values or human simulation."""
    check_plan(plan)
    rows = []
    people, slots = set(), set()
    for d in documents:
        a = validate_export(d, plan)
        require(d['participant_code'] not in people, 'Duplicate person: reconcile privately; do not choose a convenient export')
        require(d['allocation_id'] not in slots, 'Duplicate allocation: do not treat repeats as independent')
        people.add(d['participant_code']); slots.add(d['allocation_id'])
        rows.append((d, a))
    groups = defaultdict(list)
    # Measurement order stays separate: forecasts can change later intelligence ratings.
    for d, a in rows:
        groups[(d['sampling_role'], d['evidence_origin'], a['measure_order'],a['future_tools'],a['stimuli']['demonstration_order'])].append((d,a))
    strata = []
    for (role,origin,order,tools,process_order),group in sorted(groups.items()):
        arms = {}
        for arm in ARMS:
            armrows = [(d, a) for d, a in group if a['stimuli']['arm'] == arm]
            summary = dict(n_exports=len(armrows), n_complete=sum(d['status'] == 'complete' for d, _ in armrows))
            for category, keys in (('ratings', RATINGS), ('forecasts', CELLS)):
                summary[category] = {}
                for key in keys:
                    values = [d[category][key] for d, _ in armrows if d[category][key] is not None]
                    summary[category][key] = dict(n=len(values), mean=mean(values) if values else None,
                        n_at_min=sum(v == (0 if category == 'forecasts' else 1) for v in values),
                        n_at_max=sum(v == (100 if category == 'forecasts' else 7) for v in values))
            scores = [operation_score(d['forecasts']) for d, _ in armrows]
            known = [s for s in scores if s is not None]
            summary['operation_specificity'] = dict(n=len(known), mean=mean(known) if known else None)
            owner=arm.removeprefix('assistant_')
            summary['checks']={key:dict(Counter(str(d['checks'][key]) for d,_ in armrows)) for key in CHECKS if key!='interpretation'}
            summary['source_checks_both_correct']=sum(
                d['checks']['dependency_source']==('assistant' if owner=='dependency' else 'component') and
                d['checks']['selection_source']==('assistant' if owner=='selection' else 'component') for d,_ in armrows)
            summary['tools_check_correct']=sum(d['checks']['tools']==tools for d,_ in armrows)
            summary['allocation_check_correct']=sum(d['checks']['allocation']=='assigned' for d,_ in armrows)
            summary['n_interpretations']=sum(d['checks']['interpretation'] is not None for d,_ in armrows)
            summary['exemplars']=dict(Counter(a['stimuli']['exposure_id'] for _,a in armrows))
            arms[arm] = summary
        expected={a['block_id'] for a in plan['allocations'] if a['measure_order']==order
                  and a['future_tools']==tools and a['stimuli']['demonstration_order']==process_order}
        paired=[]
        for bid in sorted({a['block_id'] for _,a in group}):
            by_arm={arm:[(d,a) for d,a in group if a['block_id']==bid and a['stimuli']['arm']==arm] for arm in ARMS}
            if all(by_arm.values()):paired.append(dict(block_id=bid,**paired_block(by_arm)))
        strata.append(dict(sampling_role=role,evidence_origin=origin,measure_order=order,future_tools=tools,
            demonstration_order=process_order,arms=arms,matched_blocks=paired,**aggregate_blocks(paired,len(expected))))
    availability=[]
    for role,origin,order,process_order in sorted({(x['sampling_role'],x['evidence_origin'],x['measure_order'],x['demonstration_order']) for x in strata}):
        two={x['future_tools']:x for x in strata if (x['sampling_role'],x['evidence_origin'],x['measure_order'],x['demonstration_order'])==(role,origin,order,process_order)}
        if set(two)!=set(TOOLS):continue
        blocks={t:{b['block_id']:b for b in two[t]['matched_blocks'] if b['diagnostic']['crossover'] is not None} for t in TOOLS}
        common=sorted(set(blocks['unavailable'])&set(blocks['available']))
        diff=mean(blocks['unavailable'][b]['diagnostic']['crossover']-blocks['available'][b]['diagnostic']['crossover'] for b in common) if common else None
        expected=two['available']['n_planned_blocks']
        availability.append(dict(sampling_role=role,evidence_origin=origin,measure_order=order,demonstration_order=process_order,
            n_common_blocks=len(common),n_planned_blocks=expected,common_block_unavailable_minus_available=diff,
            full_design_unavailable_minus_available=diff if len(common)==expected else None,
            interpretation='Descriptive resource moderation on identical complete blocks; not mediation or independent capability proof.'))
    return dict(version=VERSION, analysis='descriptive_feasibility_only', n_exports=len(rows),
                plan_sha256=plan['plan_sha256'],strata=strata,availability_comparisons=availability,
                limitations=['No human results exist until actual consented exports are supplied.',
                    'No power, inferential intervals, calibrated probabilities or population effects are established.',
                    'Unknown answers remain missing; complete-case differences may be selected.',
                    'Checks are reported, not used for post-treatment exclusion.',
                    'Partial allocation blocks need not balance arms, order or exemplars.',
                    'Condition/source metadata are attestations, not authentication or proof of human authorship.',
                    'Crossover and even opposite arm ordering can arise under heterogeneous global shifts; no unique mechanism identified.',
                    'Both operations are observed: role swap identifies allocation effects, not isolated authorship or actual capability.',
                    'Missing-answer bounds concern submitted exports only, not unsubmitted participants.',
                    'Resource availability cannot affect ratings taken before its disclosure.'])


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='cmd', required=True)
    b = sub.add_parser('build')
    b.add_argument('--output', type=Path, required=True); b.add_argument('--seed', type=int, required=True)
    b.add_argument('--batch-id', required=True, help='Unique issuance ID; never reuse for a separate recruitment batch')
    b.add_argument('--role', choices=('developer_pilot', 'volunteer'), default='developer_pilot')
    b.add_argument('--origin', choices=('human_observer', 'synthetic_test'), default='human_observer')
    b.add_argument('--study-info', required=True, help='Participant contact, local storage, retention and withdrawal arrangements')
    a = sub.add_parser('analyze'); a.add_argument('--plan', type=Path, required=True)
    a.add_argument('--exports', type=Path, nargs='+', required=True); a.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    try:
        if args.cmd == 'build':
            plan = build(args.output, args.seed, args.role, args.origin, args.study_info, args.batch_id)
            print(f"Created {len(plan['allocations'])} planned slots, no observations.")
        else:
            save_new(args.output, analyze(load(args.plan), [load(f) for f in args.exports]))
            print('Local descriptive report saved. No population inference.')
    except (ValueError, OSError) as exc:
        p.error(str(exc))

if __name__ == '__main__':
    main()
