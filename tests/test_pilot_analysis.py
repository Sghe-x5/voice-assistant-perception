"""SYNTHETIC fixtures only. These tests collect no human/model observations."""
import copy
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest

from pilot import analyze_pilot as pilot

ROOT = Path(__file__).resolve().parents[1]


def synthetic_export(origin='human_first_person', first='A'):
    """Match the actual form's export, not empirical participant data."""
    planned = pilot.schedule(['S1', 'S2', 'S3', 'S4', 'S5', 'S6'], first)
    models = {slot: dict(product='SYNTHETIC TEST SERVICE ' + slot, version='TEST ONLY',
                        mode='live_voice', details='Synthetic fixture; no interaction occurred.',
                        expectation_smartness=4 if origin == 'human_first_person' else None,
                        expectation_before_interaction=True if origin == 'human_first_person' else None,
                        expectation_missing_reason=None if origin == 'human_first_person' else 'agent_run',
                        baseline_recorded_at='2026-11-04T09:00:01Z') for slot in ('A', 'B')}
    records = []
    for p in planned:
        records.append(dict(**p, evidence_origin=origin, dialogue_date='2026-11-04',
                            completion='completed', experience_confirmed=True,
                            recorded_at=f"2026-11-04T09:{p['sequence']:02d}:00Z",
                            ratings={k: (3 if p['model_slot'] == 'A' else 5) for k in pilot.RATINGS} if origin == 'human_first_person' else None,
                            transcript='SYNTHETIC TEST TEXT. Not a model response.',
                            timing=dict(first_response_seconds=0, dialogue_seconds=20, source='measured'),
                            extra_user_turns=0, clarification_questions=None, asr_error='unknown', deviations=None))
    return dict(schema_version='1.0', participant_code='P-000000000001', consent=True,
                created_at='2026-11-04T09:00:00Z', exported_at='2026-11-04T10:00:00Z',
                settings=dict(evidence_origin=origin, models=models, first_model=first, schedule=planned,
                              recorded_at='2026-11-04T09:00:02Z', timezone='Europe/Moscow'),
                records=records, history=[], drafts={}, notes={'fixture': 'SYNTHETIC ONLY'})


class PilotAnalysisTests(unittest.TestCase):
    def setUp(self):
        # All generated test exports/reports stay under tests, never data/results.
        self.tmp = tempfile.TemporaryDirectory(prefix='.synthetic-pilot-', dir=ROOT / 'tests')
        self.addCleanup(self.tmp.cleanup)
        self.folder = Path(self.tmp.name)

    def write(self, data, name='synthetic.json'):
        path = self.folder / name
        path.write_text(json.dumps(data), encoding='utf-8')
        return path

    def run_export(self, data):
        return pilot.analyze([self.write(data)])

    def codes(self, result):
        return {i['code'] for i in result['violations']}

    def pair(self, result, outcome, task='S1'):
        return next(p for p in result['pairs'] if p['task_id'] == task and p['outcome'] == outcome)

    def test_contract_matches_form(self):
        form = (ROOT / 'pilot/rating_form.html').read_text()
        tasks = json.loads(re.search(r'const TASKS = (\[.*?\]);', form, re.S)[1])
        self.assertEqual(tasks, pilot.load_json(ROOT / 'pilot/tasks.json'))
        for key in pilot.RATINGS:
            self.assertIn("['" + key + "',", form)
        self.assertIn("schema_version:'1.0'", form)
        self.assertIn("record.ratings=null", form)

    def test_full_repeated_design_and_reverse_order(self):
        for first in ('A', 'B'):
            report = self.run_export(synthetic_export(first=first))
            self.assertEqual(report['summary']['n_errors'], 0)
            self.assertEqual(report['summary']['n_human_participant_codes'], 1)
            self.assertEqual(report['summary']['n_human_dialogues'], 12)
            self.assertEqual(len(report['pairs']), 6 * 9)
            self.assertEqual(self.pair(report, 'smartness')['B_minus_A'], 2)
            self.assertEqual(self.pair(report, 'effort')['B_minus_A'], 2)
            self.assertFalse(report['summary']['population_inference'])
            self.assertEqual(report['objective_items'], [])

    def test_missing_values_zero_and_partial_pairs(self):
        d = synthetic_export()
        d['records'] = d['records'][:2]
        d['records'][0]['ratings']['smartness'] = None
        d['records'][0]['extra_user_turns'] = None
        report = self.run_export(d)
        self.assertIsNone(self.pair(report, 'smartness')['A'])
        self.assertIsNone(self.pair(report, 'smartness')['B_minus_A'])
        self.assertEqual(self.pair(report, 'extra_user_turns')['B'], 0)
        self.assertIsNone(self.pair(report, 'smartness', 'S6')['B_minus_A'])
        self.assertIn('incomplete_session', self.codes(report))

    def test_agent_subjective_values_and_baselines_excluded(self):
        d = synthetic_export('agent_run')
        d['records'][0]['ratings'] = dict.fromkeys(pilot.RATINGS, 7)
        d['settings']['models']['A']['expectation_smartness'] = 7
        report = self.run_export(d)
        self.assertEqual(report['summary']['n_human_participant_codes'], 0)
        self.assertEqual(report['summary']['n_agent_dialogues'], 12)
        self.assertTrue(all(r['smartness'] is None for r in report['records']))
        self.assertTrue(all(r['expectation_smartness'] is None for r in report['baselines']))
        self.assertIn('agent_ratings_excluded', self.codes(report))
        self.assertEqual(self.pair(report, 'smartness')['unavailable_reason'], 'agent_subjective_excluded')

    def test_record_origin_cannot_override_session(self):
        d = synthetic_export()
        d['records'][0]['evidence_origin'] = 'agent_run'
        report = self.run_export(d)
        self.assertEqual(len(report['records']), 11)
        self.assertIn('origin_mismatch', self.codes(report))

    def test_duplicates_not_arbitrarily_selected(self):
        d = synthetic_export()
        d['records'].append(copy.deepcopy(d['records'][0]))
        report = self.run_export(d)
        self.assertEqual(len(report['records']), 11)
        self.assertIn('duplicate_trial', self.codes(report))
        report = pilot.analyze([self.write(d, 'one.json'), self.write(d, 'two.json')])
        self.assertEqual(report['records'], [])
        self.assertEqual(report['summary']['n_human_participant_codes'], 0)
        self.assertIn('duplicate_export', self.codes(report))

    def test_invalid_session_metadata_quarantines_whole_export(self):
        mutations = [lambda d: d.update(schema_version='2.0'), lambda d: d.update(consent=False),
                     lambda d: d.update(participant_code='somebody'),
                     lambda d: d['settings'].update(evidence_origin='human'),
                     lambda d: d['settings']['schedule'][0].update(sequence=2),
                     lambda d: d['settings']['schedule'][0].update(sequence=True),
                     lambda d: d['settings']['models']['A'].update(mode='speech'),
                     lambda d: d['settings']['models']['A'].update(product='Claude'),
                     lambda d: d['settings']['models']['A'].update(mode='other', details=None),
                     lambda d: d.update(exported_at='invalid')]
        for mutation in mutations:
            d = synthetic_export()
            mutation(d)
            with self.subTest(mutation=mutation):
                report = self.run_export(d)
                self.assertEqual(report['records'], [])
                self.assertGreater(report['summary']['n_errors'], 0)

    def test_bad_record_ids_dates_confirmation_are_excluded(self):
        for update in [dict(task_id='S6'), dict(sequence=True), dict(experience_confirmed=False),
                       dict(trial_id='S7_A'), dict(model_slot='B'), dict(dialogue_date='2026-02-30'),
                       dict(dialogue_date='2026-11-05'), dict(recorded_at='2026-11-04T08:00:00Z')]:
            d = synthetic_export()
            d['records'][0].update(update)
            with self.subTest(update=update):
                report = self.run_export(d)
                self.assertEqual(len(report['records']), 11)
                self.assertGreater(report['summary']['n_errors'], 0)

    def test_numeric_validation_does_not_coerce(self):
        for value in (True, '5', 0, 8, 2.5, []):
            d = synthetic_export()
            d['records'][0]['ratings']['smartness'] = value
            report = self.run_export(d)
            self.assertIsNone(report['records'][0]['smartness'])
            self.assertIn('invalid_rating', self.codes(report))
        for value in (True, -1, 1.5, '0', 10**400):
            d = synthetic_export()
            d['records'][0]['extra_user_turns'] = value
            report = self.run_export(d)
            self.assertIsNone(report['records'][0]['extra_user_turns'])

    def test_timing_attribution_and_modality(self):
        d = synthetic_export()
        d['records'][0]['timing']['source'] = None
        report = self.run_export(d)
        self.assertIsNone(report['records'][0]['first_response_seconds'])
        self.assertIn('unattributed_timing', self.codes(report))
        d = synthetic_export()
        d['records'][0]['timing']['first_response_seconds'] = 30
        report = self.run_export(d)
        self.assertIn('impossible_timing', self.codes(report))
        d = synthetic_export()
        d['records'][0]['timing']['source'] = 'estimated'
        report = self.run_export(d)
        self.assertEqual(self.pair(report, 'dialogue_seconds')['unavailable_reason'], 'mixed_timing_sources')
        d['settings']['models']['B']['mode'] = 'text'
        report = self.run_export(d)
        self.assertIsNone(self.pair(report, 'smartness')['B_minus_A'])
        self.assertEqual(self.pair(report, 'smartness')['unavailable_reason'], 'mixed_modes')

    def test_history_drafts_interruptions_and_order(self):
        d = synthetic_export()
        d['history'] = [copy.deepcopy(d['records'][0])]
        d['drafts'] = {'S1_A': copy.deepcopy(d['records'][0])}
        d['records'][0]['completion'] = 'interrupted'
        d['records'][0]['deviations'] = 'SYNTHETIC interruption'
        d['records'][0]['recorded_at'] = '2026-11-04T09:59:00Z'
        report = self.run_export(d)
        self.assertEqual(len(report['records']), 12)
        self.assertEqual(self.pair(report, 'smartness')['A_completion'], 'interrupted')
        self.assertTrue(self.pair(report, 'smartness')['has_deviations'])
        self.assertTrue({'save_order_mismatch', 'history_ignored', 'drafts_ignored', 'interrupted'} <= self.codes(report))

    def test_posthoc_expectation_removed(self):
        d = synthetic_export()
        d['settings']['models']['A']['expectation_before_interaction'] = False
        report = self.run_export(d)
        self.assertIsNone(report['baselines'][0]['expectation_smartness'])
        self.assertIn('invalid_expectation', self.codes(report))

    def test_malformed_json_nonfinite_duplicate_keys(self):
        for raw in ('[]', '{bad', '{"a":1,"a":2}', '{"a":NaN}', '{"a":Infinity}'):
            path = self.folder / 'malformed.json'
            path.write_text(raw)
            report = pilot.analyze([path])
            self.assertIn('unreadable_export', self.codes(report))
            self.assertEqual(report['records'], [])

    def annotation(self, trial='S1_A'):
        return dict(participant_code='P-000000000001', trial_id=trial, coder_origin='human',
                    coder_id='SYNTHETIC-CODER', rubric_version='1.0', coded_at='2026-11-04T11:00:00Z',
                    evidence_reference='SYNTHETIC fixture only',
                    criteria={f'S1{k}': dict(score=v, reason='SYNTHETIC test rationale')
                              for k, v in zip('abcd', [1, 0, None, None])})

    def test_manual_annotations_preserve_denominator_and_pairs(self):
        a, b = self.annotation(), self.annotation('S1_B')
        b['criteria']['S1a']['score'] = 0
        report = pilot.analyze([self.write(synthetic_export())], self.write(dict(schema_version='1.0', annotations=[a, b]), 'coding.json'))
        total = report['objective_tasks'][0]
        self.assertEqual((total['passed'], total['assessed'], total['missing'], total['fraction_passed']), (1, 2, 2, .5))
        self.assertEqual(report['objective_pairs'][0]['B_minus_A'], -1)
        self.assertIsNone(report['objective_pairs'][2]['B_minus_A'])
        self.assertEqual(report['objective_tasks'][2]['assessed'], 0)
        self.assertIsNone(report['objective_tasks'][2]['fraction_passed'])

    def test_bad_or_agent_coding_is_not_human_annotation(self):
        for change in [dict(coder_origin='agent'), dict(coder_id=''), dict(evidence_reference=None),
                       dict(coded_at='2026-11-04T08:00:00Z'), dict(criteria={})]:
            annotation = self.annotation()
            annotation.update(change)
            report = pilot.analyze([self.write(synthetic_export())], self.write(dict(schema_version='1.0', annotations=[annotation]), 'coding.json'))
            self.assertEqual(report['objective_items'], [])
            self.assertGreater(report['summary']['n_errors'], 0)
        annotation = self.annotation()
        report = pilot.analyze([self.write(synthetic_export())], self.write(dict(schema_version='1.0', annotations=[annotation, annotation]), 'coding.json'))
        self.assertEqual(report['objective_items'], [])

    def test_cli_writes_audit_exit_codes_and_never_overwrites(self):
        path = self.write(synthetic_export())
        original = hashlib.sha256(path.read_bytes()).hexdigest()
        output = self.folder / 'report'
        command = [sys.executable, str(ROOT / 'pilot/analyze_pilot.py'), str(path), '--output', str(output)]
        run = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(json.loads((output / 'report.json').read_text())['summary']['n_human_participant_codes'], 1)
        self.assertTrue((output / 'pairs.csv').exists())
        self.assertEqual(subprocess.run(command, capture_output=True).returncode, 2)
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), original)
        path.write_text('{broken')
        command[-1] = str(self.folder / 'invalid_report')
        self.assertEqual(subprocess.run(command, capture_output=True).returncode, 2)
        self.assertTrue((self.folder / 'invalid_report/violations.csv').exists())


if __name__ == '__main__':
    unittest.main()
