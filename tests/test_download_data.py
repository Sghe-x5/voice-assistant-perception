"""Synthetic SPSS fixtures: verified originals must own the analysis exports."""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import pandas as pd
import pyreadstat

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('downloader', ROOT / 'scripts/download_data.py')
downloader = importlib.util.module_from_spec(spec)
spec.loader.exec_module(downloader)


class DownloadDataTests(unittest.TestCase):
    def test_offline_replay_rebuilds_missing_and_stale_exports(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            files = []
            for study in (1, 2):
                path = root / f'data/raw/beyond_voice/experiment{study}.sav'
                path.parent.mkdir(parents=True, exist_ok=True)
                pyreadstat.write_sav(pd.DataFrame({'fixture_value': [1., 2.]}), path)
                files.append(dict(path=str(path.relative_to(root)), url='https://invalid.test/unused',
                                  sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
            stale = root / 'data/raw/beyond_voice/experiment1.sav.csv'
            stale.write_text('fixture_value\n99\n')
            (root / 'data/download_manifest.json').write_text(json.dumps({'files': files}))
            with patch.object(downloader, 'ROOT', root), patch('sys.argv', ['download_data.py', '--verify-only']), \
                 patch.object(downloader.urllib.request, 'urlopen', side_effect=AssertionError('Network forbidden')):
                downloader.main()
            for item in files:
                source = root / item['path']
                self.assertEqual(pd.read_csv(str(source) + '.csv').fixture_value.tolist(), [1., 2.])
                self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(), item['sha256'])
