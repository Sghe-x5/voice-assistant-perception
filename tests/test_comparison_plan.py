"""Planning tests only; no real participants, calls or model responses."""
import copy
from collections import Counter
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from pilot.plan_comparison import make_plan, write_plan
from pilot.analyze_pilot import schedule


def model_specs():
    return [dict(model_id=x, product=x, version='TEST', mode='text',
                 details='Synthetic configuration') for x in ('GPT', 'Claude', 'DeepSeek', 'Qwen')]


class ComparisonPlanTests(unittest.TestCase):
    def test_balanced_pairs_and_existing_form_contract(self):
        models = model_specs()
        original = copy.deepcopy(models)
        plan = make_plan(models, ['S1', 'S2', 'S3', 'S4', 'S5', 'S6'], seed=19)
        self.assertEqual(models, original)
        self.assertEqual(plan['status'], 'planned_not_observed')
        self.assertEqual(len(plan['allocations']), 12)
        pairs, starts, appearances = Counter(), Counter(), Counter()
        for a in plan['allocations']:
            ids = [a['models'][s]['model_id'] for s in ('A', 'B')]
            pairs[tuple(sorted(ids))] += 1
            starts[(tuple(sorted(ids)), a['first_model'])] += 1
            appearances.update(ids)
            self.assertEqual(a['schedule'], schedule(['S1', 'S2', 'S3', 'S4', 'S5', 'S6'], a['first_model']))
            self.assertNotIn('records', a)
            self.assertNotIn('participant_code', a)
        self.assertEqual(set(pairs.values()), {2})
        self.assertEqual(set(starts.values()), {1})
        self.assertEqual(set(appearances.values()), {6})
        self.assertEqual(plan, make_plan(models, ['S1', 'S2', 'S3', 'S4', 'S5', 'S6'], seed=19))
        other = make_plan(models, ['S1', 'S2', 'S3', 'S4', 'S5', 'S6'], seed=20)
        self.assertNotEqual(plan['allocations'], other['allocations'])

    def test_invalid_or_mixed_mode_configs_rejected(self):
        for change in (lambda m: m.pop(), lambda m: m[1].update(model_id='GPT'),
                       lambda m: m[1].update(mode='live_voice'),
                       lambda m: m[1].update(version=''), lambda m: m[0].update(mode='other')):
            m = model_specs()[:2]
            change(m)
            with self.assertRaises(ValueError):
                make_plan(m, ['S1', 'S2'], seed=1)
        for tasks in ([], ['S1', 'S1'], ['S1'], ['../S1', 'S2']):
            with self.assertRaises(ValueError):
                make_plan(model_specs(), tasks, seed=1)
        for seed in (True, 'one', -1):
            with self.assertRaises(ValueError):
                make_plan(model_specs(), ['S1', 'S2'], seed=seed)

    def test_manifest_files_and_no_overwrite(self):
        plan = make_plan(model_specs(), ['S1', 'S2'], seed=1)
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / 'plan'
            write_plan(plan, out)
            saved = json.loads((out / 'plan.json').read_text())
            self.assertEqual(saved, plan)
            self.assertEqual(len(list(out.glob('allocation-*.json'))), 12)
            before = (out / 'plan.json').read_bytes()
            with self.assertRaises(FileExistsError):
                write_plan(plan, out)
            self.assertEqual((out / 'plan.json').read_bytes(), before)

    def test_unicode_config_round_trips_in_ascii_locale(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / 'plan'
            script = r"""
from pilot.plan_comparison import make_plan, write_plan
import sys
models = [dict(model_id=x, product=x, version='v1', mode='text', details='\u0422\u0435\u0441\u0442') for x in ('A','B')]
write_plan(make_plan(models, ['S1','S2'], 1), sys.argv[1])
"""
            env = dict(os.environ, LC_ALL='C', PYTHONUTF8='0', PYTHONCOERCECLOCALE='0')
            result = subprocess.run([sys.executable, '-c', script, str(out)],
                                    cwd=Path(__file__).resolve().parents[1], env=env,
                                    capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr.decode('utf-8', errors='replace'))
            for path in out.glob('*.json'):
                self.assertIn('Тест', path.read_text(encoding='utf-8'))
