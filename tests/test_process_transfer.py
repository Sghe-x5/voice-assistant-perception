"""Synthetic fixtures only: never human observations."""
import copy
from collections import Counter
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from pilot.process_transfer import study as s
from pilot.process_transfer import materials as m
from pilot.process_transfer.diagnostics import examples


def fixture(plan, a, pid='P-000000000001'):
    return dict(version=m.VERSION,plan_sha256=plan['plan_sha256'],allocation_id=a['allocation_id'],
                participant_code=pid,sampling_role='developer_pilot',evidence_origin='synthetic_test',
                mode='text_vignette_observer',analysis_permission=True,status='complete',
                ratings={k:None for k in m.RATINGS},forecasts={k:None for k in m.CELLS},
                checks={k:None for k in m.CHECKS},presented=s.sequence(a),completed=s.sequence(a))


class TransferTests(unittest.TestCase):
    def setUp(self):
        self.plan=s.make_plan(17)

    def test_factorial_balance_and_deterministic_order(self):
        p=self.plan
        self.assertEqual(p,s.make_plan(17)); self.assertNotEqual(p,s.make_plan(18))
        self.assertEqual(len(p['allocations']),256)
        counts=Counter((a['stimuli']['exposure_id'],a['stimuli']['arm'],a['measure_order']) for a in p['allocations'])
        self.assertEqual(set(counts.values()),{16})
        for arm in m.ARMS:
            a=[a for a in p['allocations'] if a['stimuli']['arm']==arm]
            for pos in range(4):
                self.assertEqual(set(Counter(x['probe_order'][pos] for x in a).values()),{32})
        transitions=Counter((order[i],order[i+1]) for order in m.ORDERS for i in range(3))
        self.assertEqual(len(transitions),12);self.assertEqual(set(transitions.values()),{1})
        for a in p['allocations']:
            self.assertEqual(set(a['probe_order']),set(m.CELLS))

    def test_material_arithmetic_and_identical_outcome(self):
        for topic in ('schedule','inventory'):
            for v in (0,1):
                left=m.material(topic,v,m.ARMS[0]);right=m.material(topic,v,m.ARMS[1])
                for key in ('request','final','truth'):self.assertEqual(left[key],right[key])
                self.assertEqual({p['absolute_id']:p['request'] for p in left['probes']},
                                 {p['absolute_id']:p['request'] for p in right['probes']})
                self.assertNotEqual(left['process'],right['process'])
                for target in (topic,'inventory' if topic=='schedule' else 'schedule'):
                    for exposure in (False,True):
                        t=m.dependency(target,v,exposure)['truth'];base,new,last=t['inputs']
                        expected=([base+new,base+new+last] if target=='schedule' else [base+new,base+new-last]) if v==0 else ([base-last-new,base-last] if target=='schedule' else [base+last-new,base+last])
                        self.assertEqual(t['outputs'],expected)
                        t=m.selection(target,v,exposure)['truth']
                        eligible=[i for i,x in enumerate(t['values']) if (x>=t['threshold'] if t['constraint']=='at_least' else x<=t['threshold'])]
                        self.assertEqual(t['selected_index'],min(eligible,key=lambda i:t['prices'][i]))

    def test_build_is_offline_no_answers_no_overwrite_and_cleanup(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'slots'
            s.build(root,17,origin='synthetic_test',study_info='Test only </script>',batch_id='ui-test')
            self.assertEqual(len(list(root.glob('*.html'))),256)
            html=(root/'S001.html').read_text()
            self.assertIn('Test only \\u003c/script>',html)
            config=json.loads(html.split('const CONFIG = ',1)[1].split(';\nconst el',1)[0])
            self.assertNotIn('truth',json.dumps(config));self.assertNotIn('plan.json',html)
            self.assertEqual(config['evidence_origin'],'synthetic_test')
            with self.assertRaises(FileExistsError):s.build(root,17,study_info='test',batch_id='test')
            out=Path(tmp)/'failed'
            with patch.object(Path,'write_text',side_effect=OSError('synthetic failure')):
                with self.assertRaises(OSError):s.build(out,17,study_info='test',batch_id='test')
            self.assertFalse(out.exists())

    def test_missingness_and_contrast_by_hand(self):
        a=next(a for a in self.plan['allocations'] if a['stimuli']['arm']=='assistant_dependency')
        b=next(b for b in self.plan['allocations'] if b['stimuli']['arm']=='assistant_selection'
               and b['block_id']==a['block_id'] and b['future_tools']==a['future_tools'])
        one=fixture(self.plan,a);two=fixture(self.plan,b,'P-000000000002')
        one['forecasts']=dict(zip(m.CELLS,[80,30,60,50]));two['forecasts']=dict(zip(m.CELLS,[40,40,40,40]))
        one['ratings']['smartness']=7
        report=s.analyze(self.plan,[one,two]);group=report['strata'][0]
        self.assertEqual(group['common_block_crossover'],15)
        self.assertEqual(group['complete_block_coverage'],'1/16')
        self.assertEqual(group['arms']['assistant_selection']['ratings']['smartness'],dict(n=0,mean=None,n_at_min=0,n_at_max=0))
        one['forecasts']['same_same']=None
        self.assertIsNone(s.analyze(self.plan,[one,two])['strata'][0]['common_block_crossover'])
        self.assertEqual(s.operation_score(dict(zip(m.CELLS,[0,100,0,100]))),-100)

    def test_rejects_wrong_plan_duplicate_and_invalid_evidence(self):
        good=fixture(self.plan,self.plan['allocations'][0])
        changes=[lambda d:d.update(analysis_permission=False),lambda d:d.update(mode='live_voice'),
                 lambda d:d.update(plan_sha256='bad'),lambda d:d.update(evidence_origin='agent_run'),
                 lambda d:d['forecasts'].update(same_same=True),lambda d:d['forecasts'].update(same_same=101),
                 lambda d:d['forecasts'].update(same_same=1.5),lambda d:d['ratings'].update(smartness=0),
                 lambda d:d.update(participant_code='name'),lambda d:d['completed'].pop(),
                 lambda d:d.update(sampling_role='volunteer')]
        for change in changes:
            d=copy.deepcopy(good);change(d)
            with self.assertRaises(ValueError):s.analyze(self.plan,[d])
        with self.assertRaises(ValueError):s.analyze(self.plan,[good,good])
        modified=copy.deepcopy(self.plan);modified['allocations'][0]['stimuli']['final']='changed'
        with self.assertRaises(ValueError):s.analyze(modified,[good])

    def test_partial_prefix_no_unseen_answers_and_no_check_exclusion(self):
        a=self.plan['allocations'][0];d=fixture(self.plan,a)
        d.update(status='partial',presented=['exposure',s.sequence(a)[1]],completed=['exposure'])
        report=s.analyze(self.plan,[d]);self.assertEqual(report['n_exports'],1)
        d['checks']['dependency_source']='unknown'
        with self.assertRaises(ValueError):s.analyze(self.plan,[d])
        d=fixture(self.plan,a);d['checks']['dependency_source']='unknown'
        self.assertEqual(s.analyze(self.plan,[d])['n_exports'],1)

    def test_strict_json_rejects_duplicate_and_nonfinite(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'x.json'
            for text in ('{"x":1,"x":2}','{"x":NaN}','{"x":Infinity}'):
                p.write_text(text)
                with self.assertRaises(ValueError):s.load(p)

    def test_batch_consent_and_evidence_origin_are_bound_to_plan(self):
        d=fixture(self.plan,self.plan['allocations'][0])
        human=s.make_plan(17,role='volunteer',origin='human_observer',study_info='Human consent',batch_id='people-01')
        self.assertNotEqual(self.plan['plan_sha256'],human['plan_sha256'])
        with self.assertRaises(ValueError):s.analyze(human,[d])
        d.update(sampling_role='volunteer',evidence_origin='human_observer')
        with self.assertRaises(ValueError):s.analyze(self.plan,[d])
        for option in ({'batch_id':'new'},{'study_info':'Changed terms'},{'origin':'human_observer'}):
            self.assertNotEqual(self.plan['plan_sha256'],s.make_plan(17,**option)['plan_sha256'])

    def test_mathematical_examples_are_not_mechanistic_evidence(self):
        d=examples()
        self.assertEqual(d['linear_examples']['operation']['difference'],20)
        self.assertEqual(d['linear_examples']['topic']['difference'],0)
        self.assertEqual(d['linear_examples']['global']['difference'],0)
        self.assertGreater(d['nonlinear_global_shift']['difference'],10)
        self.assertEqual(d['missingness_example']['full_mean'],0)
        self.assertNotIn('p_value',d)

if __name__=='__main__':unittest.main()
