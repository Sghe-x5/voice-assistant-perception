"""Synthetic design/math fixtures only; never human study evidence."""
import copy
import itertools
import unittest
from pilot.process_transfer import materials as m, study as s
from pilot.process_transfer import summaries as stats
from pilot.process_transfer.diagnostics import examples


def export(plan,a,pid,values):
    return dict(version=m.VERSION,plan_sha256=plan['plan_sha256'],allocation_id=a['allocation_id'],
        participant_code=f'P-{pid:012x}',sampling_role=plan['sampling_role'],evidence_origin=plan['evidence_origin'],
        mode='text_vignette_observer',analysis_permission=True,status='complete',
        ratings={k:None for k in m.RATINGS},forecasts=dict(zip(m.CELLS,values)),
        checks={k:None for k in m.CHECKS},presented=s.sequence(a),completed=s.sequence(a))


class PairedTransferTests(unittest.TestCase):
    def test_blocks_cross_roles_and_resources_with_identical_absolute_probes(self):
        p=s.make_plan(23);self.assertEqual(len(p['allocations']),256)
        for start in range(0,256,4):
            block=p['allocations'][start:start+4]
            self.assertEqual(len({a['block_id'] for a in block}),1)
            self.assertEqual({(a['stimuli']['arm'],a['future_tools']) for a in block},set(itertools.product(m.ARMS,m.TOOLS)))
            probes=[]
            for a in block:
                steps=a['stimuli']['steps']
                self.assertEqual(sorted(x['actor'] for x in steps),['assistant','component'])
                probes.append({x['absolute_id']:x['request'] for x in a['stimuli']['probes']})
            self.assertTrue(all(x==probes[0] for x in probes))
            self.assertEqual(len({a['stimuli']['request'] for a in block}),1)
            self.assertEqual(len({a['stimuli']['final'] for a in block}),1)

    def test_relative_labels_follow_executor_not_fixed_dependency(self):
        for arm in m.ARMS:
            x=m.material('schedule',0,arm)
            for probe in x['probes']:
                self.assertEqual(probe['operation']==x['assistant_operation'],probe['id'].split('_')[1]=='same')
        self.assertNotEqual(m.dependency('schedule',0)['truth']['direction'],m.dependency('schedule',1)['truth']['direction'])
        self.assertNotEqual(m.selection('inventory',0)['truth']['constraint'],m.selection('inventory',1)['truth']['constraint'])

    def test_bounds_match_exhaustive_extreme_completions(self):
        for values in ([None]*4,[None,20,30,40],[0,100,0,100],[50,None,None,50]):
            d=dict(zip(m.CELLS,values));lo,hi=stats.relative_bounds(d)
            missing=[k for k,v in d.items() if v is None];scores=[]
            for completions in itertools.product((0,100),repeat=len(missing)):
                full=dict(d);full.update(zip(missing,completions));scores.append(s.operation_score(full))
            self.assertEqual((lo,hi),(min(scores),max(scores)))

    def test_counterexamples_and_endpoint_logit_guard(self):
        x=examples()
        self.assertAlmostEqual(x['nonlinear_global_shift']['difference'],15.928152978545384)
        self.assertGreater(x['paired_swap']['homogeneous_global']['crossover'],0)
        self.assertEqual(x['paired_swap']['homogeneous_global']['ordering'],'same_direction_or_zero')
        signed=x['paired_swap']['opposite_signed_global_mixture']
        self.assertAlmostEqual(signed['crossover'],6.015040226689528)
        self.assertEqual(signed['ordering'],'predicted_opposite')
        edge=stats.point_diagnostics(dict(zip(m.ABS_CELLS,[100,0,100,0])),dict(zip(m.ABS_CELLS,[0,100,0,100])))
        self.assertIsNone(edge['marginal_logit_shift_range'])
        self.assertEqual(edge['crossover'],100)

    def test_complete_case_and_missing_bounds_have_explicit_coverage(self):
        p=s.make_plan(23);block=p['allocations'][:4]
        docs=[export(p,a,i+1,[80,20,80,20]) for i,a in enumerate(block)]
        r=s.analyze(p,docs)
        self.assertEqual(len(r['strata']),2)
        for g in r['strata']:
            self.assertEqual(g['common_block_crossover'],60)
            self.assertIsNone(g['full_design_crossover'])
            self.assertEqual(g['common_block_missing_answer_bounds'],[60,60])
        docs[0]['forecasts']['same_same']=None
        g=next(g for g in s.analyze(p,docs)['strata'] if g['future_tools']==block[0]['future_tools'])
        self.assertIsNone(g['common_block_crossover'])
        self.assertGreater(g['common_block_missing_answer_bounds'][1]-g['common_block_missing_answer_bounds'][0],0)

    def test_tools_checks_and_source_checks_follow_plan(self):
        p=s.make_plan(23)
        for i,a in enumerate(p['allocations'][:4]):
            d=export(p,a,i+1,[50]*4)
            d['checks'].update(dependency_source='assistant' if a['stimuli']['assistant_operation']=='dependency' else 'component',
                selection_source='assistant' if a['stimuli']['assistant_operation']=='selection' else 'component',
                tools=a['future_tools'],allocation='assigned',interpretation='Synthetic fixture only')
            g=s.analyze(p,[d])['strata'][0]['arms'][a['stimuli']['arm']]
            self.assertEqual(g['source_checks_both_correct'],1);self.assertEqual(g['tools_check_correct'],1)
            d['checks']['interpretation']='x'*2001
            with self.assertRaises(ValueError):s.analyze(p,[d])

    def test_plan_hash_rejects_bool_integer_alias(self):
        p=s.make_plan(23);altered=copy.deepcopy(p)
        altered['allocations'][0]['stimuli']['variant']=bool(altered['allocations'][0]['stimuli']['variant'])
        with self.assertRaises(ValueError):s.check_plan(altered)

    def test_partial_export_cannot_claim_all_pages_completed(self):
        p=s.make_plan(23)
        d=export(p,p['allocations'][0],1,[50]*4);d['status']='partial'
        with self.assertRaises(ValueError):s.analyze(p,[d])

    def test_full_block_and_resource_moderation_are_explicit(self):
        p=s.make_plan(23)
        docs=[export(p,a,i+1,[80,20,80,20] if a['future_tools']=='unavailable' else [50]*4) for i,a in enumerate(p['allocations'])]
        r=s.analyze(p,docs)
        self.assertEqual(len(r['strata']),8)
        for g in r['strata']:
            expected=60 if g['future_tools']=='unavailable' else 0
            self.assertEqual(g['full_design_crossover'],expected)
            self.assertEqual(g['full_design_missing_answer_bounds'],[expected,expected])
        self.assertTrue(all(a['full_design_unavailable_minus_available']==60 for a in r['availability_comparisons']))

    def test_role_relabeling_and_mixture_logit_warning(self):
        left=dict(zip(m.ABS_CELLS,[80,30,60,40]));right=dict(zip(m.ABS_CELLS,[20,80,40,60]))
        self.assertAlmostEqual(stats.point_diagnostics(left,right)['crossover'],-stats.point_diagnostics(right,left)['crossover'])
        self.assertGreater(examples()['paired_swap']['same_direction_global_mixture']['marginal_logit_shift_range'],0)
        for invalid in (True,-1,101,float('nan'),float('inf')):
            bad=dict(left);bad[m.ABS_CELLS[0]]=invalid
            with self.assertRaises(ValueError):stats.point_diagnostics(bad,right)

    def test_credit_cannot_be_reported_before_post_forecast_page(self):
        p=s.make_plan(23);a=next(x for x in p['allocations'] if x['measure_order']=='ratings_first')
        d=export(p,a,1,[None]*4)
        d.update(status='partial',presented=s.sequence(a)[:3],completed=s.sequence(a)[:2])
        d['ratings']['credit']=4
        with self.assertRaises(ValueError):s.analyze(p,[d])
