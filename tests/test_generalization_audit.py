"""Synthetic rows only; test overlap accounting without public survey records."""
import copy
import csv
import hashlib
import io
import importlib.util
from pathlib import Path
import unittest
import tempfile

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('release_audit',ROOT/'analysis/generalization/audit_release.py')
audit=importlib.util.module_from_spec(spec);spec.loader.exec_module(audit)


def row(q1,q2,previous='1',label='1'):
    return dict(q1=q1,q2=q2,source1='task-a',source2='task-b',previous_correct=previous,belief_change=label)


class GeneralizationAuditTests(unittest.TestCase):
    def test_new_pair_can_contain_two_seen_questions(self):
        r=audit.audit_rows([row('a','b')],[row('b','a'),row('new','b')])
        self.assertEqual(r['overlap']['exact_conditioned_pairs'],0)
        self.assertEqual(r['overlap']['test_rows_both_questions_seen'],1)
        self.assertEqual(r['overlap']['test_q2_seen_in_either_training_role_rows'],2)

    def test_repeated_judgments_are_counted_not_removed(self):
        rows=[row('a','b'),row('a','b'),row('a','b',label='0')]
        before=copy.deepcopy(rows)
        r=audit.audit_rows(rows,[row('x','y')])['files']['train']
        self.assertEqual(rows,before)
        self.assertEqual(r['rows'],3)
        self.assertEqual(r['duplicate_complete_rows'],1)
        self.assertEqual(r['duplicate_conditioned_pairs'],2)
        self.assertEqual(r['conditioned_pairs_with_both_labels'],1)

    def test_correctness_condition_is_part_of_pair_key(self):
        r=audit.audit_rows([row('a','b',previous='0')],[row('a','b',previous='1')])
        self.assertEqual(r['overlap']['exact_conditioned_pairs'],0)
        self.assertEqual(r['overlap']['exact_unconditioned_pairs'],1)

    def test_invalid_rows_and_unexpected_schema_rejected(self):
        for update in [dict(belief_change='2'),dict(q1=''),dict(previous_correct='True'),dict(extra='x')]:
            d=row('a','b');d.update(update)
            with self.assertRaises(ValueError):audit.audit_rows([d],[row('c','d')])
        with self.assertRaises(ValueError):audit.audit_rows([],[row('c','d')])

    def test_unicode_separators_are_question_text_not_csv_record_boundaries(self):
        rows=[row('a\u2028b','c\nd'),row('e','f')]
        stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fieldnames=audit.COLUMNS)
        writer.writeheader();writer.writerows(rows);payload=stream.getvalue().encode('utf-8')
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'fixture.csv';path.write_bytes(payload)
            self.assertEqual(audit.read_verified(path,hashlib.sha256(payload).hexdigest()),rows)
            with self.assertRaises(ValueError):audit.read_verified(path,'0'*64)
