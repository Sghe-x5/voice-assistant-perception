#!/usr/bin/env python3
"""Descriptive, local-only analysis of rating_form.html schema 1.0 exports."""
import argparse
from collections import Counter
import csv
from datetime import date, datetime
import hashlib
import json
import math
from pathlib import Path
import re
import sys
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

HERE = Path(__file__).resolve().parent
RATINGS = ('smartness', 'understanding', 'usefulness', 'trust', 'effort')
NUMBERS = ('extra_user_turns', 'clarification_questions',
           'first_response_seconds', 'dialogue_seconds')
ORIGINS = ('human_first_person', 'agent_run')
MODES = ('live_voice', 'voice_text', 'text', 'other')


def load_json(path):
    def unique(pairs):
        obj = {}
        for key, value in pairs:
            if key in obj:
                raise ValueError(f'duplicate JSON key: {key}')
            obj[key] = value
        return obj
    def invalid(value):
        raise ValueError(f'non-finite JSON constant: {value}')
    return json.loads(Path(path).read_text(encoding='utf-8'),
                      object_pairs_hook=unique, parse_constant=invalid)


def text(value):
    return isinstance(value, str) and bool(value.strip())


def timestamp(value):
    try:
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
        return parsed if parsed.tzinfo is not None else None
    except (AttributeError, TypeError, ValueError):
        return None


def number(value, low=0, high=math.inf, integer=False):
    try:
        return (type(value) in (int, float) and math.isfinite(value)
                and low <= value <= high and (not integer or value == int(value)))
    except OverflowError:
        return False


def schedule(tasks, first):
    result = []
    for i, task in enumerate(tasks):
        lead = first if i % 2 == 0 else ('B' if first == 'A' else 'A')
        for slot in (lead, 'B' if lead == 'A' else 'A'):
            result.append(dict(trial_id=f'{task}_{slot}', task_id=task,
                               model_slot=slot, sequence=len(result) + 1))
    return result


def analyze(paths, annotations=None):
    """Return audit and tables; never write inputs or infer unobserved values."""
    tasks = [t['id'] for t in load_json(HERE / 'tasks.json')]
    issues, sessions, records, baselines, manifest, documents = [], [], [], [], [], []

    def issue(source, pid, trial, code, detail, severity='error'):
        issues.append(dict(source=source, participant_code=pid, trial_id=trial,
                           severity=severity, code=code, detail=detail))

    for path in paths:
        path = Path(path)
        source = str(path.resolve())
        try:
            raw = path.read_bytes()
            manifest.append(dict(path=source, sha256=hashlib.sha256(raw).hexdigest()))
            d = load_json(path)
            if not isinstance(d, dict):
                raise ValueError('export root must be an object')
            documents.append((source, d))
        except (OSError, ValueError) as exc:
            issue(source, None, None, 'unreadable_export', str(exc))
    ids = Counter(d.get('participant_code') for _, d in documents
                  if isinstance(d.get('participant_code'), str))
    for source, d in documents:
        pid = d.get('participant_code')
        pid = pid if isinstance(pid, str) else None
        start = len(issues)
        def check(ok, code, detail, trial=None, severity='error'):
            if not ok:
                issue(source, pid, trial, code, detail, severity)
        check(d.get('schema_version') == '1.0', 'schema_version', 'Expected schema 1.0.')
        check(bool(pid and re.fullmatch(r'P-[0-9a-f]{12}', pid)), 'participant_id',
              'Expected the random participant code produced by the form.')
        check(ids[pid] <= 1, 'duplicate_export',
              'All exports of this code excluded; explicitly select one snapshot.')
        check(d.get('consent') is True, 'consent', 'Local consent must be true.')
        s = d.get('settings')
        s = s if isinstance(s, dict) else {}
        origin = s.get('evidence_origin')
        check(origin in ORIGINS, 'evidence_origin', 'Unknown or missing session origin.')
        check(s.get('first_model') in ('A', 'B'), 'first_model', 'Expected A or B.')
        planned = schedule(tasks, s.get('first_model'))
        check(s.get('schedule') == planned and all(type(p['sequence']) is int for p in s['schedule']), 'schedule', 'Schedule does not match task/slot/order contract.')
        for label, value in [('created_at', d.get('created_at')),
                             ('exported_at', d.get('exported_at')),
                             ('settings.recorded_at', s.get('recorded_at'))]:
            check(timestamp(value) is not None, 'timestamp', label + ' requires a timezone-aware timestamp.')
        created, setup, exported = map(timestamp, (d.get('created_at'), s.get('recorded_at'), d.get('exported_at')))
        if all((created, setup, exported)):
            check(created <= setup <= exported, 'timestamp_order', 'Expected created <= settings <= export.')
        try:
            zone = ZoneInfo(s.get('timezone'))
        except (TypeError, ValueError, ZoneInfoNotFoundError):
            zone = None
            check(False, 'timezone', 'Missing/unknown timezone; date chronology is not fully checkable.', severity='warning')
        models = s.get('models')
        models = models if isinstance(models, dict) else {}
        check(set(models) == {'A', 'B'}, 'models', 'Exactly slots A and B required.')
        for slot in ('A', 'B'):
            m = models.get(slot)
            m = m if isinstance(m, dict) else {}
            for field in ('product', 'version'):
                check(text(m.get(field)), 'model_metadata', f'{slot}.{field} required; unknown version may be explicit.')
            check(m.get('mode') in MODES, 'model_mode', f'{slot}: unknown interaction mode.')
            check(m.get('details') is None or text(m.get('details')), 'model_details', f'{slot}: details must be text/null.')
            check(m.get('mode') != 'other' or text(m.get('details')), 'other_mode_details', f'{slot}: describe other mode.')
            check(timestamp(m.get('baseline_recorded_at')) is not None, 'baseline_timestamp', f'{slot}: timestamp required.')
            baseline_time = timestamp(m.get('baseline_recorded_at'))
            if all((created, setup, baseline_time)):
                check(created <= baseline_time <= setup, 'baseline_chronology', f'{slot}: baseline metadata outside setup interval.')
        rows = d.get('records')
        check(isinstance(rows, list), 'records_type', 'records must be an array.')
        history, drafts = d.get('history'), d.get('drafts')
        check(isinstance(history, list) and all(isinstance(x, dict) for x in history),
              'history_type', 'history must be an array of objects.')
        check(isinstance(drafts, dict), 'drafts_type', 'drafts must be an object.')
        rejected = any(i['severity'] == 'error' for i in issues[start:])
        sessions.append(dict(source=source, participant_code=pid, evidence_origin=origin,
                             accepted=not rejected, n_export_records=len(rows) if isinstance(rows, list) else None,
                             n_history_ignored=len(history) if isinstance(history, list) else None,
                             n_drafts_ignored=len(drafts) if isinstance(drafts, dict) else None))
        if rejected:
            continue
        check(not drafts, 'drafts_ignored', 'Unsaved drafts are not observations.', severity='warning')
        check(not history, 'history_ignored', 'Revisions are audit only, never additional observations.', severity='warning')
        if models['A']['mode'] != models['B']['mode']:
            check(False, 'mixed_modes', 'A/B modalities differ; pair differences suppressed.', severity='warning')
        if all(models['A'].get(k) == models['B'].get(k) for k in ('product', 'version')):
            check(False, 'same_product_version', 'A/B labels do not document distinct models.', severity='warning')
        for slot, m in models.items():
            expectation = m.get('expectation_smartness')
            if origin == 'agent_run':
                check(expectation is None, 'agent_expectation_excluded', f'{slot}: agent expectation removed.')
                expectation = None
            elif expectation is not None:
                if not number(expectation, 1, 7, True) or m.get('expectation_before_interaction') is not True:
                    check(False, 'invalid_expectation', f'{slot}: invalid/post-hoc expectation removed.')
                    expectation = None
            else:
                check(text(m.get('expectation_missing_reason')), 'expectation_missing_reason',
                      f'{slot}: missing expectation without explanation.', severity='warning')
            baselines.append(dict(participant_code=pid, evidence_origin=origin, model_slot=slot,
                                  product=m['product'], version=m['version'], mode=m['mode'], details=m.get('details'),
                                  expectation_smartness=expectation, expectation_missing_reason=m.get('expectation_missing_reason')))
        row_ids = Counter(r.get('trial_id') for r in rows if isinstance(r, dict) and isinstance(r.get('trial_id'), str))
        accepted = []
        for r in rows:
            row_start = len(issues)
            if not isinstance(r, dict):
                check(False, 'record_type', 'Record must be an object.')
                continue
            trial = r.get('trial_id')
            trial = trial if isinstance(trial, str) else None
            expected = next((p for p in planned if p['trial_id'] == trial), None)
            check(expected is not None, 'trial_id', 'Unknown trial ID.', trial)
            check(row_ids[trial] == 1, 'duplicate_trial', 'All copies of duplicate trial excluded.', trial)
            if expected:
                check(all(r.get(k) == v and type(r.get(k)) is type(v) for k, v in expected.items()),
                      'trial_metadata', 'Task, model slot or sequence mismatch.', trial)
            check(r.get('evidence_origin') == origin, 'origin_mismatch', 'Record/session origins must agree.', trial)
            check(r.get('experience_confirmed') is True, 'unconfirmed_record', 'Experience must be confirmed.', trial)
            check(r.get('completion') in ('completed', 'interrupted'), 'completion', 'Unknown completion status.', trial)
            saved = timestamp(r.get('recorded_at'))
            check(saved is not None and setup <= saved <= exported, 'record_timestamp', 'Record must be between setup and export.', trial)
            try:
                day = date.fromisoformat(r.get('dialogue_date'))
                check(not zone or day <= exported.astimezone(zone).date(), 'dialogue_date_future', 'Dialogue date after export.', trial)
                if zone:
                    check(day >= setup.astimezone(zone).date(), 'dialogue_before_setup', 'Dialogue predates setup.', trial)
            except (TypeError, ValueError):
                check(False, 'dialogue_date', 'Expected ISO calendar date.', trial)
            for field in ('transcript', 'deviations'):
                check(r.get(field) is None or text(r.get(field)), 'text_field', field + ' must be text/null.', trial)
            check(r.get('asr_error') in ('yes', 'no', 'unknown'), 'asr_error', 'Expected yes/no/unknown.', trial)
            if any(i['severity'] == 'error' for i in issues[row_start:]):
                continue
            values = {}
            ratings = r.get('ratings')
            if origin == 'agent_run':
                check(ratings is None, 'agent_ratings_excluded', 'Agent subjective fields discarded.', trial)
                ratings = {}
            elif not isinstance(ratings, dict):
                check(False, 'ratings_type', 'Human ratings require an object; all items remain missing.', trial)
                ratings = {}
            for key in RATINGS:
                value = ratings.get(key)
                if origin == 'human_first_person' and key not in ratings:
                    check(False, 'rating_key_missing', key + ': expected explicit value/null.', trial)
                if value is not None and not number(value, 1, 7, True):
                    check(False, 'invalid_rating', key + ': expected integer 1..7/null; excluded.', trial)
                    value = None
                values[key] = value
            timing = r.get('timing')
            if not isinstance(timing, dict):
                check(False, 'timing_type', 'Expected timing object; values excluded.', trial)
                timing = {}
            timing_source = timing.get('source')
            check(timing_source in (None, 'measured', 'estimated'), 'timing_source', 'Unknown timing source.', trial)
            for key in NUMBERS:
                value = (timing if key.endswith('_seconds') else r).get(key)
                if value is not None and not number(value, integer=not key.endswith('_seconds')):
                    check(False, 'invalid_number', key + ': nonnegative finite value required; excluded.', trial)
                    value = None
                if key.endswith('_seconds') and value is not None and timing_source not in ('measured', 'estimated'):
                    check(False, 'unattributed_timing', key + ': source required; excluded.', trial)
                    value = None
                values[key] = value
            latency, duration = values['first_response_seconds'], values['dialogue_seconds']
            if latency is not None and duration is not None and latency > duration:
                check(False, 'impossible_timing', 'First response delay exceeds entire dialogue; both excluded.', trial)
                values['first_response_seconds'] = values['dialogue_seconds'] = None
            check(not values['extra_user_turns'], 'extra_turns_reported',
                  'Unplanned user turns reported; inspect protocol deviation.', trial, 'warning')
            check(not r.get('deviations'), 'reported_deviation', 'Participant reports a protocol deviation; inspect export.', trial, 'warning')
            check(r['completion'] == 'completed', 'interrupted', 'Retained as an interrupted attempt.', trial, 'warning')
            m = models[r['model_slot']]
            check(m['mode'] != 'text' or r['asr_error'] == 'unknown', 'asr_in_text', 'ASR report in text mode needs review.', trial, 'warning')
            rec = dict(source=source, participant_code=pid, evidence_origin=origin, **expected,
                       product=m['product'], version=m['version'], mode=m['mode'], completion=r['completion'],
                       dialogue_date=r['dialogue_date'], recorded_at=r['recorded_at'], timing_source=timing_source,
                       asr_error=r['asr_error'], has_transcript=text(r.get('transcript')),
                       has_deviations=text(r.get('deviations')), **values)
            records.append(rec)
            accepted.append(rec)
        missing = [p['trial_id'] for p in planned if p['trial_id'] not in {r['trial_id'] for r in accepted}]
        check(not missing, 'incomplete_session', 'Absent/rejected trials: ' + ', '.join(missing), severity='warning')
        # Save times are proxies only: editing and delayed entry can change them.
        ordered = sorted(accepted, key=lambda r: timestamp(r['recorded_at']))
        check([r['sequence'] for r in ordered] == sorted(r['sequence'] for r in ordered),
              'save_order_mismatch', 'Save chronology differs from plan; actual interaction order unverified.', severity='warning')
    pairs = []
    for session in sessions:
        if not session['accepted']:
            continue
        pid = session['participant_code']
        by_trial = {r['trial_id']: r for r in records if r['participant_code'] == pid}
        for task in tasks:
            a, b = by_trial.get(task + '_A'), by_trial.get(task + '_B')
            for outcome in RATINGS + NUMBERS:
                av, bv = (a.get(outcome) if a else None), (b.get(outcome) if b else None)
                reason = ('missing_trial' if not a or not b else
                          'agent_subjective_excluded' if outcome in RATINGS and session['evidence_origin'] == 'agent_run' else
                          'missing_value' if av is None or bv is None else
                          'mixed_modes' if a['mode'] != b['mode'] else
                          'mixed_timing_sources' if outcome.endswith('_seconds') and a['timing_source'] != b['timing_source'] else None)
                pairs.append(dict(participant_code=pid, evidence_origin=session['evidence_origin'], task_id=task,
                                  outcome=outcome, A=av, B=bv, B_minus_A=bv-av if reason is None else None,
                                  unavailable_reason=reason, A_completion=a['completion'] if a else None,
                                  B_completion=b['completion'] if b else None,
                                  A_mode=a['mode'] if a else None, B_mode=b['mode'] if b else None,
                                  A_timing_source=a['timing_source'] if a else None, B_timing_source=b['timing_source'] if b else None,
                                  has_deviations=bool((a and a['has_deviations']) or (b and b['has_deviations']))))
    objective_items, objective_tasks = [], []
    if annotations is not None:
        objective_items, objective_tasks = score_annotations(annotations, records, issue, manifest)
    objective_pairs = []
    objective_lookup = {(r['participant_code'], r['trial_id'], r['criterion_id']): r for r in objective_items}
    record_lookup = {(r['participant_code'], r['trial_id']): r for r in records}
    for item in objective_items:
        pid, trial, cid = item['participant_code'], item['trial_id'], item['criterion_id']
        task = trial.rsplit('_', 1)[0]
        if any(p['participant_code'] == pid and p['criterion_id'] == cid for p in objective_pairs):
            continue
        a = objective_lookup.get((pid, task + '_A', cid), {}).get('score')
        b = objective_lookup.get((pid, task + '_B', cid), {}).get('score')
        ra, rb = record_lookup.get((pid, task + '_A')), record_lookup.get((pid, task + '_B'))
        reason = ('missing_value' if a is None or b is None else
                  'mixed_modes' if ra['mode'] != rb['mode'] else None)
        objective_pairs.append(dict(participant_code=pid, evidence_origin=item['evidence_origin'],
                                    task_id=task, criterion_id=cid, A=a, B=b,
                                    B_minus_A=b-a if reason is None else None, unavailable_reason=reason,
                                    A_completion=ra['completion'] if ra else None, B_completion=rb['completion'] if rb else None,
                                    A_mode=ra['mode'] if ra else None, B_mode=rb['mode'] if rb else None,
                                    has_deviations=bool((ra and ra['has_deviations']) or (rb and rb['has_deviations']))))
    human_codes = sorted({r['participant_code'] for r in records if r['evidence_origin'] == 'human_first_person'})
    return dict(summary=dict(analysis='descriptive_only', human_participant_codes=human_codes,
                             n_human_participant_codes=len(human_codes), n_human_dialogues=sum(r['evidence_origin'] == 'human_first_person' for r in records),
                             n_agent_dialogues=sum(r['evidence_origin'] == 'agent_run' for r in records),
                             population_inference=False, n_errors=sum(i['severity'] == 'error' for i in issues),
                             caveats=['Codes are not independently verified people. Repeated tasks are not independent participants.',
                                      'No population tests, confidence intervals, pooled model ranking or composite intelligence index.',
                                      'Effort retains its original direction: higher means more effort.',
                                      'Interaction order, new chats, prompt fidelity, key blinding and immediate ratings cannot be established from export alone.',
                                      'Interrupted attempts retained and labeled. Metadata and timing are self-reported.',
                                      'Manual objective annotations are attributed reports, not independently verified truth.']),
                inputs=manifest, sessions=sessions, baselines=baselines, records=records,
                pairs=pairs, objective_pairs=objective_pairs, objective_items=objective_items, objective_tasks=objective_tasks, violations=issues)


def score_annotations(path, records, issue, manifest):
    """Read separate researcher annotations. Never classify transcript content."""
    source = str(Path(path).resolve())
    try:
        d = load_json(path)
        manifest.append(dict(path=source, sha256=hashlib.sha256(Path(path).read_bytes()).hexdigest()))
        if not isinstance(d, dict) or d.get('schema_version') != '1.0' or not isinstance(d.get('annotations'), list):
            raise ValueError('Expected annotation schema 1.0 with annotations array.')
    except (OSError, ValueError) as exc:
        issue(source, None, None, 'annotation_file', str(exc))
        return [], []
    key = load_json(HERE / 'scoring_key.json')
    criteria = {t['id']: [c['id'] for c in t['criteria']] for t in key['tasks']}
    eligible = {(r['participant_code'], r['trial_id']): r for r in records}
    items, accepted, counts = [], {}, Counter()
    for x in d['annotations']:
        if isinstance(x, dict) and all(isinstance(x.get(k), str) for k in ('participant_code', 'trial_id')):
            counts[x['participant_code'], x['trial_id']] += 1
    for x in d['annotations']:
        if not isinstance(x, dict):
            issue(source, None, None, 'annotation_type', 'Annotation must be an object.')
            continue
        pid, trial = x.get('participant_code'), x.get('trial_id')
        pair = (pid, trial) if isinstance(pid, str) and isinstance(trial, str) else None
        r = eligible.get(pair)
        if not r or counts[pair] != 1:
            issue(source, pid, trial, 'annotation_identity', 'Unknown/rejected/duplicate trial annotation; excluded.')
            continue
        scores = x.get('criteria')
        if (x.get('coder_origin') != 'human' or not text(x.get('coder_id'))
                or x.get('rubric_version') != key['schema_version']
                or not text(x.get('evidence_reference')) or not timestamp(x.get('coded_at'))
                or not isinstance(scores, dict) or set(scores) != set(criteria[r['task_id']])):
            issue(source, pid, trial, 'annotation_metadata', 'Human coder, time, rubric version, evidence reference and exact criterion IDs required.')
            continue
        if any(not isinstance(v, dict) or (v.get('score') is not None and not number(v.get('score'), 0, 1, True))
               or 'score' not in v or not text(v.get('reason')) for v in scores.values()):
            issue(source, pid, trial, 'annotation_score', 'Each criterion requires score 0/1/null and textual reason; excluded.')
            continue
        latest_rating = max(timestamp(v['recorded_at']) for v in records if v['participant_code'] == pid)
        if timestamp(x['coded_at']) < latest_rating:
            issue(source, pid, trial, 'coding_before_ratings', 'Coding predates saved ratings; excluded.')
            continue
        if sum(v['participant_code'] == pid for v in records) < 12:
            issue(source, pid, trial, 'coding_in_partial_session',
                  'Partial session coded; verify participant has not seen the key before resumed collection.', 'warning')
        accepted[pair] = scores
        for cid, v in scores.items():
            items.append(dict(participant_code=pid, trial_id=trial, criterion_id=cid, score=v['score'], reason=v['reason'], evidence_origin=r['evidence_origin'],
                              coder_id=x['coder_id'], coder_origin='human', coded_at=x['coded_at'],
                              evidence_reference=x['evidence_reference'], rubric_version=x['rubric_version']))
    totals = []
    for pair, r in eligible.items():
        scores = accepted.get(pair, {})
        observed = [v['score'] for v in scores.values() if v['score'] is not None]
        totals.append(dict(participant_code=pair[0], trial_id=pair[1], task_id=r['task_id'],
                           evidence_origin=r['evidence_origin'], model_slot=r['model_slot'], mode=r['mode'], completion=r['completion'],
                           passed=sum(observed) if observed else None, assessed=len(observed),
                           total_criteria=len(criteria[r['task_id']]),
                           missing=len(criteria[r['task_id']])-len(observed),
                           fraction_passed=sum(observed)/len(observed) if observed else None))
    return items, totals


def write_report(report, output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    (output / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    for name in ('sessions', 'baselines', 'records', 'pairs', 'objective_pairs', 'objective_items', 'objective_tasks', 'violations'):
        rows = report[name]
        # Empty tables have a documented sentinel header; report.json keeps [] intact.
        fields = list(dict.fromkeys(k for r in rows for k in r)) or ['no_rows']
        with (output / (name + '.csv')).open('w', newline='', encoding='utf-8') as stream:
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('exports', nargs='+', type=Path)
    parser.add_argument('--output', required=True, type=Path, help='New directory; existing directories are refused.')
    parser.add_argument('--annotations', type=Path, help='Separate human researcher coding, optional.')
    args = parser.parse_args(argv)
    if args.output.exists():
        parser.error('output already exists; choose a new directory')
    report = analyze(args.exports, args.annotations)
    report['software'] = dict(analysis_version='1.0', python=sys.version, analyzer_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                              tasks_sha256=hashlib.sha256((HERE / 'tasks.json').read_bytes()).hexdigest())
    report['software']['form_sha256'] = hashlib.sha256((HERE / 'rating_form.html').read_bytes()).hexdigest()
    report['software']['protocol_sha256'] = hashlib.sha256((HERE / 'protocol.txt').read_bytes()).hexdigest()
    if args.annotations:
        report['software']['rubric_sha256'] = hashlib.sha256((HERE / 'scoring_key.json').read_bytes()).hexdigest()
    write_report(report, args.output)
    print(json.dumps(report['summary'], ensure_ascii=False))
    return 2 if report['summary']['n_errors'] else 0


if __name__ == '__main__':
    raise SystemExit(main())
