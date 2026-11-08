"""Independent arithmetic/source checks for the scientific outputs."""
from pathlib import Path
import unittest,hashlib,json
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]

class IntegrityChecks(unittest.TestCase):
    def test_pinned_raw_files(self):
        m=json.loads((ROOT/'data/download_manifest.json').read_text())
        for item in m['files']:
            with self.subTest(path=item['path']):
                self.assertEqual(hashlib.sha256((ROOT/item['path']).read_bytes()).hexdigest(),item['sha256'])

    def test_voice_metrics_from_saved_individual_predictions(self):
        p=pd.read_csv(ROOT/'results/voice_predictions.csv');s=pd.read_csv(ROOT/'results/voice_prediction.csv')
        for _,r in s.iterrows():
            q=p[(p['split']==r['split'])&(p.model==r.model)]
            self.assertEqual(len(q),r.n_test)
            self.assertAlmostEqual(np.abs(q.y-q.prediction).mean(),r.mae,places=11)
            self.assertAlmostEqual(1-np.sum((q.y-q.prediction)**2)/np.sum((q.y-q.y.mean())**2),r.r2,places=11)

    def test_cocreation_join_and_observation_key(self):
        book=ROOT/'data/raw/komura2026/s003.xlsx'
        q=pd.read_excel(book,sheet_name='questionnaires');s=pd.read_excel(book,sheet_name='sessions_metrics');n=pd.read_excel(book,sheet_name='notes_detailed')
        self.assertEqual(set(q.sessionId),set(s.sessionId));self.assertEqual(set(q.sessionId),set(n.sessionId))
        self.assertFalse(n.duplicated(['sessionId','creator','turnId']).any())
        selected=n.groupby(['sessionId','creator']).is_selected.sum().unstack()
        for role in ['ai','user']:
            self.assertTrue(np.array_equal(s.sessionId.map(selected[role]),s['selected_'+role+'_notes_count']))
        self.assertEqual(int((q.aitype=='unknown').sum()),6)

    def test_cocreation_cv_coverage_and_metrics(self):
        metrics=pd.read_csv(ROOT/'results/cocreation_prediction_metrics.csv')
        for split in ['participant','condition']:
            p=pd.read_csv(ROOT/f'results/cocreation_predictions_{split}.csv')
            self.assertTrue(p.sessionId.is_unique);self.assertEqual(len(p),142)
            self.assertNotIn('unknown',set(p.aitype))
            if split=='condition':self.assertTrue(p.groupby('fold').aitype.nunique().eq(1).all())
            for _,r in metrics[metrics['split']==split].iterrows():
                pred=p[r.model];y=p.observed
                self.assertAlmostEqual(np.sqrt(np.mean((y-pred)**2)),r.rmse,places=11)
                self.assertAlmostEqual(1-np.sum((y-pred)**2)/np.sum((y-y.mean())**2),r.r2,places=11)

    def test_latency_unit_and_repeated_cv(self):
        raw=pd.read_csv(ROOT/'data/raw/tan2026/DATASET.csv')
        self.assertEqual(raw.ParticipantID.nunique(),240)
        self.assertTrue(raw.groupby('ParticipantID').Rating_usefulness.count().eq(1).all())
        p=pd.read_csv(ROOT/'results/latency_predictions.csv')
        self.assertFalse(p.duplicated(['participant','target','model','repeat']).any())
        self.assertTrue(p.groupby(['target','model','repeat']).size().eq(237).all())
        s=pd.read_csv(ROOT/'results/latency_prediction_metrics.csv')
        for _,r in s.iterrows():
            q=p[(p.target==r.target)&(p.model==r.model)]
            rs=[1-np.sum((g.observed-g.predicted)**2)/np.sum((g.observed-g.observed.mean())**2) for _,g in q.groupby('repeat')]
            self.assertAlmostEqual(np.mean(rs),r.oof_r2_mean,places=11)

    def test_adjusted_p_values_and_model_ranks(self):
        for name,col in [('latency_omnibus.csv','p_holm_21'),('latency_contrasts.csv','p_holm_28')]:
            q=pd.read_csv(ROOT/'results'/name);self.assertTrue((q[col]>=q.p-1e-12).all());self.assertTrue(q[col].between(0,1).all())
        q=pd.read_csv(ROOT/'results/cocreation_regressions.csv');self.assertNotIn('ai_notes',set(q.term))

    def test_added_log_comparator_is_design_user(self):
        m=pd.read_csv(ROOT/'results/cocreation_prediction_metrics.csv').set_index(['split','model'])
        d=pd.read_csv(ROOT/'results/cocreation_increment_vs_design.csv')
        self.assertEqual(len(d),4)
        for _,r in d.iterrows():
            self.assertEqual(r.comparator,'design_user')
            a=m.loc[(r['split'],r.model)];b=m.loc[(r['split'],'design_user')]
            self.assertAlmostEqual(r.r2_gain,a.r2-b.r2,places=11)
            self.assertAlmostEqual(r.mae_reduction,b.mae-a.mae,places=11)

    def test_retraining_bootstrap_algebra_and_quantiles(self):
        meta=json.loads((ROOT/'results/voice_retraining_bootstrap.json').read_text())
        b=meta['bootstrap_draws_per_transfer'];self.assertGreaterEqual(b,1000)
        self.assertTrue(all(meta['checks'].values()))
        d=pd.read_csv(ROOT/'results/voice_retraining_bootstrap_draws.csv')
        self.assertEqual(len(d),2*b);self.assertFalse(d.duplicated(['split','draw']).any())
        self.assertTrue(np.allclose(d.mae_reduction_survey_vs_operational,d.mae_design_user-d.mae_credibility_only))
        self.assertTrue(np.allclose(d.r2_gain_survey_vs_operational,d.r2_credibility_only-d.r2_design_user))
        for _,r in pd.read_csv(ROOT/'results/voice_retraining_bootstrap.csv').iterrows():
            x=d.loc[d['split']==r['split'],r.metric]
            self.assertAlmostEqual(x.quantile(.025),r.ci_low,places=11)
            self.assertAlmostEqual(x.quantile(.975),r.ci_high,places=11)

if __name__=='__main__':unittest.main()
