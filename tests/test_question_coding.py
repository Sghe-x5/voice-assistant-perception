"""Authored fixtures only; no observed dialogues or human ratings."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from pilot import fieldwork as f


def turn(tid, speaker, utterance, context=None):
    return dict(turn_id=tid,speaker=speaker,text=utterance,evidence_reference='synthetic:'+tid,
                assistant_context_before=context)


def snapshot(content):
    return dict(text=content,source='request_log',complete=True,evidence_reference='synthetic input log')


def detailed_diary():
    return dict(schema_version='field-diary-1.1',participant_code='P-000000000001',
                sampling_role='volunteer',analysis_permission=True,redaction_reviewed=True,
                episodes=[dict(episode_id='E1',session_id='S1',evidence_origin='human_assistant_recorded',
                 modality='live_voice',recorded_at='2026-11-05T00:00:00Z',product='FIXTURE',version='FIXTURE',
                 goal='Timer',context='Synthetic only',account='Not an observation',smartness=None,
                 turn_coverage='complete',coding_partition='held_out',
                 turns=[turn('T1','user','Timer for ten minutes'),
                        turn('T2','assistant','How long?',snapshot('Timer')),
                        turn('T3','user','Ten minutes'),
                        turn('T4','assistant','How long?',snapshot('Timer. Ten minutes')),
                        turn('T5','user','Ten minutes'),
                        turn('T6','assistant','Ten minutes, correct?',snapshot('Timer. Ten minutes'))],
                 question_units=[dict(turn_id=t,parameter_id='duration',parameter_definition='Required timer duration')
                                 for t in ('T2','T4','T6')])])


class QuestionCodingTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.path=Path(self.tmp.name)/'diary.json'

    def prepared(self,d=None):
        self.path.write_text(json.dumps(d or detailed_diary()),encoding='utf-8')
        return f.prepare([self.path])

    def coded(self, packet, coder='A'):
        p=copy.deepcopy(packet);p.update(coder_id=coder,coder_origin='human')
        row=p['annotations'][0];row['episode_familiarity']='new_to_coder'
        for q in row['questions']:
            q.update(is_question=True,user_information_before='supplied',
                     user_evidence=[dict(turn_id='T1',quote='ten minutes')],
                     assistant_information_before='available',assistant_evidence=['Ten minutes'],
                     request_kind='repeat_known_information',candidate_value=None,
                     coding_note='Synthetic parameter-linked evidence')
            if q['turn_id']=='T2':
                q.update(assistant_information_before='absent',assistant_evidence=[],request_kind='new_information_request')
            if q['turn_id']=='T6':
                q.update(request_kind='confirmation',candidate_value='Ten minutes')
        return p

    def test_information_changes_and_asr_loss_remain_separate(self):
        p=self.prepared();self.assertEqual(p['schema_version'],'field-coding-1.1')
        a=self.coded(p);b=self.coded(p,'B');r=f.compare(a,b)
        q=r['strata'][0]['questions']
        self.assertEqual(q['n_units'],3)
        self.assertEqual(q['fields']['request_kind']['n_paired'],3)
        self.assertEqual(q['fields']['request_kind']['agreement'],1)
        self.assertEqual(a['annotations'][0]['questions'][0]['assistant_information_before'],'absent')
        self.assertEqual(r['strata'][0]['coding_partition'],'held_out')

    def test_future_or_wrong_channel_evidence_rejected(self):
        for change in [lambda q:q.update(user_evidence=[dict(turn_id='T3',quote='Ten minutes')]),
                       lambda q:q.update(user_evidence=[dict(turn_id='T2',quote='How long?')]),
                       lambda q:q.update(assistant_evidence=['ten minutes'],assistant_information_before='available',request_kind='repeat_known_information'),
                       lambda q:q.update(request_kind='repeat_known_information'),
                       lambda q:q.update(user_evidence=[dict(turn_id='T1',quote='not in transcript')])]:
            p=self.prepared();a=self.coded(p);change(a['annotations'][0]['questions'][0])
            with self.assertRaises(ValueError):f.compare(a,self.coded(p,'B'))

    def test_unobserved_assistant_input_cannot_be_treated_as_known_or_absent(self):
        d=detailed_diary();d['episodes'][0]['turns'][1]['assistant_context_before']=None
        p=self.prepared(d);a=self.coded(p);b=self.coded(p,'B')
        with self.assertRaises(ValueError):f.compare(a,b)
        for packet in (a,b):
            packet['annotations'][0]['questions'][0].update(assistant_information_before='unknown',
                request_kind='unknown',assistant_evidence=[])
        r=f.compare(a,b)['strata'][0]['questions']['fields']['assistant_information_before']
        self.assertEqual(r['n_paired'],2);self.assertEqual(r['n_unknown_a'],1)

    def test_confirmation_needs_spoken_candidate_and_units_cannot_disappear(self):
        p=self.prepared()
        for change in [lambda a:a['annotations'][0]['questions'][2].update(candidate_value=None),
                       lambda a:a['annotations'][0]['questions'][2].update(candidate_value='Eleven'),
                       lambda a:a['annotations'][0]['questions'].pop(),
                       lambda a:a['annotations'][0]['questions'].append(copy.deepcopy(a['annotations'][0]['questions'][0]))]:
            a=self.coded(p);change(a)
            with self.assertRaises(ValueError):f.compare(a,self.coded(p,'B'))

    def test_incomplete_transcript_cannot_prove_user_did_not_supply_parameter(self):
        d=detailed_diary();d['episodes'][0]['turn_coverage']='partial'
        p=self.prepared(d);a=self.coded(p)
        a['annotations'][0]['questions'][0].update(user_information_before='not_supplied',user_evidence=[])
        with self.assertRaises(ValueError):f.compare(a,self.coded(p,'B'))

    def test_question_reference_and_heldout_authors_rejected(self):
        for change in [lambda d:d['episodes'][0]['question_units'][0].update(turn_id='missing'),
                       lambda d:d['episodes'][0]['question_units'][0].update(turn_id='T1'),
                       lambda d:d['episodes'][0]['turns'].append(copy.deepcopy(d['episodes'][0]['turns'][0])),
                       lambda d:d.update(sampling_role='developer_pilot')]:
            d=detailed_diary();change(d)
            with self.assertRaises(ValueError):self.prepared(d)

    def test_familiarity_is_reported_not_assumed_blind(self):
        p=self.prepared();a=self.coded(p);a['annotations'][0]['episode_familiarity']='own_episode'
        r=f.compare(a,self.coded(p,'B'))
        self.assertEqual(r['strata'][0]['familiarity'],'familiar_to_at_least_one')

    def test_legacy_diary_has_explicitly_unavailable_detail(self):
        d=detailed_diary();d['schema_version']='field-diary-1.0'
        for k in ('turns','question_units','turn_coverage','coding_partition'):d['episodes'][0].pop(k)
        p=self.prepared(d)
        self.assertEqual(p['evidence'][0]['detail_status'],'legacy_unavailable')
        self.assertEqual(p['annotations'][0]['questions'],[])

    def test_actual_legacy_packet_pair_remains_readable_without_fake_detail(self):
        d=detailed_diary();d['schema_version']='field-diary-1.0'
        for key in ('turns','question_units','turn_coverage','coding_partition'):d['episodes'][0].pop(key)
        p=self.prepared(d);p.update(schema_version='field-coding-1.0',codebook_version='0.1',coder_id='A',coder_origin='human')
        for e in p['evidence']:
            for key in ('turns','question_units','turn_coverage','coding_partition','detail_status'):e.pop(key)
        for a in p['annotations']:
            a.pop('questions');a.pop('episode_familiarity')
        p['evidence_sha256']=f.digest(p['evidence'])
        b=copy.deepcopy(p);b['coder_id']='B'
        r=f.compare(p,b)['strata'][0]
        self.assertEqual(r['questions']['n_episodes_without_turn_detail'],1)
        self.assertEqual(r['familiarity'],'unknown')

    def test_partial_input_and_duplicate_parameter_units_rejected(self):
        d=detailed_diary();d['episodes'][0]['turns'][1]['assistant_context_before']['complete']=False
        p=self.prepared(d)
        with self.assertRaises(ValueError):f.compare(self.coded(p),self.coded(p,'B'))
        d=detailed_diary();d['episodes'][0]['question_units'].append(copy.deepcopy(d['episodes'][0]['question_units'][0]))
        with self.assertRaises(ValueError):self.prepared(d)

    def test_candidate_not_a_question_stays_in_detection_denominator(self):
        p=self.prepared();a=self.coded(p);b=self.coded(p,'B')
        q=b['annotations'][0]['questions'][0]
        q.update(is_question=False,request_kind=None,user_information_before=None,assistant_information_before=None,
                 user_evidence=[],assistant_evidence=[],candidate_value=None,coding_note='Synthetic non-question disagreement')
        fields=f.compare(a,b)['strata'][0]['questions']['fields']
        self.assertEqual(fields['is_question']['n_paired'],3)
        self.assertEqual(fields['is_question']['agreement'],2/3)
        self.assertEqual(fields['request_kind']['n_paired'],2)

    def test_downgrading_packet_version_cannot_hide_question_inventory(self):
        a=self.prepared();a.update(schema_version='field-coding-1.0',codebook_version='0.1',coder_id='A',coder_origin='human')
        for row in a['annotations']:
            row.pop('questions');row.pop('episode_familiarity')
        b=copy.deepcopy(a);b['coder_id']='B'
        with self.assertRaises(ValueError):f.compare(a,b)
