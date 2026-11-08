"""Failure-path checks use synthetic process fixtures, never participant data."""
import importlib.util,json,os,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('runner',ROOT/'scripts/run_all.py')
runner=importlib.util.module_from_spec(spec);spec.loader.exec_module(runner)

class RunnerChecks(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);(self.root/'data').mkdir();(self.root/'results').mkdir()
        (self.root/'data/download_manifest.json').write_text('{"files":[]}')
        (self.root/'results/reproduction.json').write_text('{"status":"completed","commands":["stale"]}')
    def record(self):
        return json.loads((self.root/'results/reproduction.json').read_text())
    def test_failed_child_replaces_stale_success_and_stops(self):
        with self.assertRaises(RuntimeError):
            runner.run_commands(self.root,[['-c','raise SystemExit(7)'],['-c','raise AssertionError("must not run")']],os.environ.copy())
        r=self.record();self.assertEqual(r['status'],'failed');self.assertEqual(len(r['commands']),1)
        self.assertEqual(r['commands'][0]['exit_code'],7)
    def test_launch_failure_is_recorded(self):
        with patch.object(runner.subprocess,'call',side_effect=OSError('fixture')):
            with self.assertRaises(OSError):runner.run_commands(self.root,[['missing.py']],os.environ.copy())
        r=self.record();self.assertEqual(r['status'],'failed');self.assertEqual(r['commands'][0]['error_type'],'OSError')
    def test_missing_source_manifest_replaces_stale_success(self):
        (self.root/'data/download_manifest.json').unlink()
        with self.assertRaises(FileNotFoundError):runner.run_commands(self.root,[['-c','pass']],os.environ.copy())
        r=self.record();self.assertEqual(r['status'],'failed');self.assertEqual(r['stage'],'source_manifest')
        self.assertEqual(r['commands'],[])
    def test_success_is_current_and_logs_exist(self):
        r=runner.run_commands(self.root,[['-c','print("fixture")']],os.environ.copy())
        self.assertEqual(r['status'],'completed');self.assertEqual(r['commands'][0]['exit_code'],0)
        self.assertIn('fixture',(self.root/r['commands'][0]['log']).read_text())
        self.assertFalse((self.root/'results/reproduction.json.tmp').exists())

if __name__=='__main__':unittest.main()
