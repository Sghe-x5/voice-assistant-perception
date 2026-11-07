"""Meaningful source integrity, selection, transfer and inference checks."""
import importlib.util,json,unittest
from pathlib import Path
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
def module(name,path):
    s=importlib.util.spec_from_file_location(name,ROOT/path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
v=module('voice','src/analyze_voice.py');p=module('predict','src/predict_voice.py')
class VoiceChecks(unittest.TestCase):
    def test_source_integrity_and_selection(self):
        d=v.load();self.assertEqual(len(d),553)
        self.assertEqual(int(d.mc_pass.sum()),328);self.assertEqual(int(d.mc_all_pass.sum()),269)
        e1=d[d.study==1]
        self.assertTrue(np.array_equal(e1.mc_pass,(e1.socialrole==e1.Mcheck).astype(int)))
        e2=d[d.study==2]
        self.assertEqual(int((e2.socialrole2==e2.MC2_socialrole).sum()),90)
        sel=d[d.mc_all_pass==1]
        self.assertAlmostEqual(sel[sel.partner==1].intelligence.mean(),4.9714285714285715)
        self.assertAlmostEqual(sel[sel.partner==0].intelligence.mean(),4.446666666666666)
    def test_transfer_participants_are_disjoint(self):
        q=pd.read_csv(ROOT/'results/voice_predictions.csv')
        self.assertFalse(q.duplicated(['split','participant','model']).any())
        for split,prefix,n in [('E1_to_E2','E2_',200),('E2_to_E1_assertive','E1_',180),('E2_to_E1_all_shifted','E1_',353)]:
            z=q[q.split==split];self.assertEqual(z.participant.nunique(),n);self.assertTrue(z.participant.str.startswith(prefix).all())
        # Training/test identity also enforced structurally by source-study selection in script.
    def test_inference_valid_and_invalid(self):
        x=json.loads((ROOT/'examples/voice_input.json').read_text())
        self.assertTrue(np.isfinite(p.predict(x)['predicted_mean_rating']))
        self.assertIsNone(p.predict(x)['prediction_interval'])
        x.update(owner=0,information_search=None)
        self.assertTrue(np.isfinite(p.predict(x)['predicted_mean_rating']))
        for bad in [{'age_years':100},{'female':1,'diverse_gender':1},{'information_search':4}]:
            y={**x,**bad}
            with self.assertRaises(ValueError):p.predict(y)
    def test_cfa_results_admissibility(self):
        q=pd.read_csv(ROOT/'results/voice_cfa.csv');self.assertTrue(q.converged.all())
        two=q[q.model=='two_factor'];self.assertTrue((two.latent_correlation.abs()<1).all())
        for _,g in q.groupby('sample'):
            g=g.set_index('model');self.assertLess(g.loc['two_factor','chi2'],g.loc['one_factor','chi2'])
if __name__=='__main__':unittest.main()
