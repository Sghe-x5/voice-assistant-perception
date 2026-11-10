"""Synthetic fixtures only. No actual participant or model observations."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from pilot import fieldwork as f


def diary():
    return dict(schema_version='field-diary-1.0', participant_code='P-000000000001',
                analysis_permission=True, redaction_reviewed=True, sampling_role='developer_pilot',
                episodes=[dict(episode_id='E-001', session_id='S-001',
                    evidence_origin='human_assistant_recorded', modality='live_voice',
                    recorded_at='2026-11-04T12:00:00Z', product='TEST BRAND', version='TEST',
                    goal='SYNTHETIC goal', context='SYNTHETIC context',
                    account='SYNTHETIC text, not an observation.', smartness=None)])


class FieldworkTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)

    def prepare(self, d=None):
        p=self.root/'diary.json';p.write_text(json.dumps(d or diary()),encoding='utf-8')
        return f.prepare([p])

    def coded(self, packet, coder):
        p=copy.deepcopy(packet);p.update(coder_id=coder,coder_origin='human')
        for row in p['annotations']:
            row.update(task_family=['fact'],information_state=['sufficient'],
                       assistant_action=['answer'],repair_outcome='not_applicable',
                       objective_result='success',evidence_reference='synthetic turn 1')
        return p

    def test_packets_hide_brand_and_ratings_but_keep_groups(self):
        packet=self.prepare()
        serialized=json.dumps(packet)
        self.assertNotIn('TEST BRAND',serialized);self.assertNotIn('smartness',serialized)
        self.assertEqual(packet['evidence'][0]['participant_code'],'P-000000000001')
        self.assertIsNone(packet['annotations'][0]['task_family'])
        self.assertIsNone(packet['coder_origin'])
        self.assertIn('evidence_sha256',packet)

    def test_rejects_unapproved_agent_and_malformed_diaries(self):
        changes=[lambda d:d.update(analysis_permission=False),lambda d:d.update(redaction_reviewed=False),
                 lambda d:d['episodes'][0].update(evidence_origin='agent_run'),
                 lambda d:d['episodes'][0].update(smartness=True),
                 lambda d:d['episodes'][0].update(recorded_at='yesterday'),
                 lambda d:d['episodes'].append(copy.deepcopy(d['episodes'][0])),
                 lambda d:d.update(episodes=[])]
        for change in changes:
            d=diary();change(d)
            with self.assertRaises(ValueError): self.prepare(d)

    def test_duplicate_diary_and_json_keys_rejected(self):
        self.prepare();p=self.root/'diary.json'
        with self.assertRaises(ValueError): f.prepare([p,p])
        p.write_text('{"schema_version":1,"schema_version":2}')
        with self.assertRaises(ValueError): f.prepare([p])

    def test_exact_agreement_constant_kappa_is_undefined(self):
        p=self.prepare();a=self.coded(p,'A');b=self.coded(p,'B')
        report=f.compare(a,b)
        group=report['strata'][0]
        self.assertEqual(group['n_participant_codes'],1)
        self.assertEqual(group['fields']['objective_result']['agreement'],1)
        self.assertIsNone(group['fields']['objective_result']['kappa'])
        self.assertFalse(report['population_inference'])

    def test_unknown_is_not_a_negative_label_and_different_evidence_rejected(self):
        p=self.prepare();a=self.coded(p,'A');b=self.coded(p,'B')
        b['annotations'][0]['information_state']=['unknown']
        report=f.compare(a,b)
        r=report['strata'][0]['fields']['information_state']
        self.assertEqual(r['n_paired'],0)
        self.assertIsNone(r['agreement'])
        b['evidence'][0]['account']='changed'
        with self.assertRaises(ValueError):f.compare(a,b)

    def test_bad_coders_labels_and_duplicate_annotations_rejected(self):
        for change in [lambda b:b.update(coder_id='A'),lambda b:b.update(coder_origin='agent'),
                       lambda b:b['annotations'][0].update(task_family=['invented']),
                       lambda b:b['annotations'][0].update(task_family=['unknown','fact']),
                       lambda b:b['annotations'][0].update(evidence_reference=''),
                       lambda b:b['annotations'].append(copy.deepcopy(b['annotations'][0]))]:
            p=self.prepare();a=self.coded(p,'A');b=self.coded(p,'B');change(b)
            with self.assertRaises(ValueError):f.compare(a,b)

    def test_kappa_hand_calculation(self):
        r=f.agreement(['a','a','b','b'],['a','b','a','b'])
        self.assertEqual(r['agreement'],.5);self.assertEqual(r['kappa'],0)
        r=f.agreement(['a','b'],['b','a'])
        self.assertEqual(r['kappa'],-1)

    def test_developer_and_volunteer_materials_are_separate(self):
        first=diary();second=diary()
        second.update(participant_code='P-000000000002',sampling_role='volunteer')
        paths=[]
        for i,d in enumerate((first,second)):
            path=self.root/f'{i}.json';path.write_text(json.dumps(d));paths.append(path)
        p=f.prepare(paths);r=f.compare(self.coded(p,'A'),self.coded(p,'B'))
        self.assertEqual(len(r['strata']),2)
        self.assertEqual({s['sampling_role'] for s in r['strata']},{'developer_pilot','volunteer'})

    def test_new_directory_contract_and_utf8(self):
        p=self.prepare();out=self.root/'packets'
        f.write_packets(p,out)
        self.assertEqual(len(list(out.glob('coder-*.json'))),2)
        original=(out/'coder-a.json').read_bytes()
        with self.assertRaises(FileExistsError):f.write_packets(p,out)
        self.assertEqual((out/'coder-a.json').read_bytes(),original)

    def test_private_source_manifest_tracks_original_snapshot(self):
        one=self.prepare();d=diary();d['episodes'][0]['smartness']=6;two=self.prepare(d)
        self.assertEqual(one['evidence_sha256'],two['evidence_sha256'])
        self.assertNotEqual(one['source_manifest'],two['source_manifest'])
        out=self.root/'packets';f.write_packets(two,out)
        self.assertTrue((out/'preparation-manifest.json').is_file())
        self.assertNotIn('source_manifest',json.loads((out/'coder-a.json').read_text()))

    def test_second_packet_failure_removes_own_partial_files(self):
        p=self.prepare();out=self.root/'packets';real_open=Path.open
        def failing_open(path,*args,**kwargs):
            if path.name=='coder-b.json':raise OSError('Synthetic disk failure')
            return real_open(path,*args,**kwargs)
        with patch.object(Path,'open',failing_open),self.assertRaises(OSError):f.write_packets(p,out)
        self.assertFalse(out.exists())
        f.write_packets(p,out)
        self.assertTrue((out/'coder-b.json').is_file())
