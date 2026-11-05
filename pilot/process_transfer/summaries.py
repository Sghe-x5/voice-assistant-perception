"""Descriptive role-swap arithmetic, never a unique mechanism test."""
from math import isfinite, log
from statistics import mean

if __package__:
    from .materials import CELLS, ABS_CELLS, ARMS
else:
    from materials import CELLS, ABS_CELLS, ARMS


def operation_score(values):
    if any(values[c] is None for c in CELLS):return None
    return (values['same_same']+values['different_same']-values['same_different']-values['different_different'])/2


def relative_bounds(values):
    low=high=0.
    for cell in CELLS:
        weight=.5 if cell.split('_')[1]=='same' else -.5
        value=values[cell]
        if value is None:
            low+=min(0,100*weight);high+=max(0,100*weight)
        else:low+=weight*value;high+=weight*value
    return [low,high]


def absolute_values(allocation,values):
    return {p['absolute_id']:values[p['id']] for p in allocation['stimuli']['probes']}


def ordering(d,s,tolerance=1e-10):
    if d>tolerance and s < -tolerance:return 'predicted_opposite'
    if d < -tolerance and s>tolerance:return 'reverse_opposite'
    return 'same_direction_or_zero'


def point_diagnostics(dependency_owner,selection_owner,tolerance=1e-10):
    for values in (dependency_owner,selection_owner):
        if set(values)!=set(ABS_CELLS):raise ValueError('Exact absolute probe cells required')
        for v in values.values():
            if v is not None and (type(v) not in (int,float) or not 0<=v<=100 or not isfinite(v)):
                raise ValueError('Finite percentages required; no booleans')
    if any(v is None for x in (dependency_owner,selection_owner) for v in x.values()):
        return dict(status='not_evaluable',deltas=None,crossover=None,ordering='not_evaluable',marginal_logit_shift_range=None)
    deltas={c:dependency_owner[c]-selection_owner[c] for c in ABS_CELLS}
    d=mean(deltas[c] for c in ABS_CELLS if c.endswith('_dependency'))
    s=mean(deltas[c] for c in ABS_CELLS if c.endswith('_selection'))
    by_topic={t:ordering(deltas[t+'_dependency'],deltas[t+'_selection'],tolerance) for t in ('same','different')}
    logits=None
    if all(0<v<100 for x in (dependency_owner,selection_owner) for v in x.values()):
        logit=lambda x:log(x/(100-x))
        shifts=[logit(dependency_owner[c])-logit(selection_owner[c]) for c in ABS_CELLS]
        logits=max(shifts)-min(shifts)
    return dict(status='descriptive_point_means_not_inference',deltas=deltas,
                dependency_difference=d,selection_difference=s,crossover=(d-s)/2,
                ordering=ordering(d,s,tolerance),ordering_by_topic=by_topic,
                predicted_opposite_in_both_topics=all(v=='predicted_opposite' for v in by_topic.values()),
                marginal_logit_shift_range=logits,tolerance_for_arithmetic_only=tolerance,
                interpretation='Opposed point means challenge a common-direction monotone-global restriction only; signed heterogeneity and credit/salience remain possible.')


def paired_block(rows):
    """Rows grouped by assigned assistant-owned operation; both arms required."""
    if any(not rows[arm] for arm in ARMS):raise ValueError('Both assigned roles required')
    means={};bounds={};counts={}
    for arm in ARMS:
        all_rows=rows[arm]
        complete=[(d,a) for d,a in all_rows if operation_score(d['forecasts']) is not None]
        counts[arm]=dict(n_exports=len(all_rows),n_complete_forecasts=len(complete))
        abs_rows=[absolute_values(a,d['forecasts']) for d,a in complete]
        means[arm]={c:mean(x[c] for x in abs_rows) if abs_rows else None for c in ABS_CELLS}
        intervals=[relative_bounds(d['forecasts']) for d,a in all_rows]
        bounds[arm]=[mean(x[j] for x in intervals) for j in (0,1)]
    point=point_diagnostics(means[ARMS[0]],means[ARMS[1]])
    combined=[mean(bounds[arm][j] for arm in ARMS) for j in (0,1)]
    return dict(arms=counts,absolute_means_complete_cases=means,diagnostic=point,
                missing_answer_bounds=combined,
                bounds_scope='Worst-case ranges for missing answers among submitted exports; not confidence intervals or recruitment-nonresponse bounds.')


def aggregate_blocks(blocks,expected):
    complete=[b for b in blocks if b['diagnostic']['crossover'] is not None]
    point=mean(b['diagnostic']['crossover'] for b in complete) if complete else None
    bounds=[mean(b['missing_answer_bounds'][i] for b in blocks) for i in (0,1)] if blocks else None
    means={arm:{c:mean(b['absolute_means_complete_cases'][arm][c] for b in complete) if complete else None for c in ABS_CELLS} for arm in ARMS}
    return dict(common_block_crossover=point,full_design_crossover=point if len(complete)==expected else None,
                common_block_missing_answer_bounds=bounds,
                full_design_missing_answer_bounds=bounds if len(blocks)==expected else None,
                n_complete_blocks=len(complete),n_observed_paired_blocks=len(blocks),n_planned_blocks=expected,
                complete_block_coverage=f'{len(complete)}/{expected}',
                point_diagnostic=point_diagnostics(means[ARMS[0]],means[ARMS[1]]),
                weighting='Equal roles, equal two probe topics, then equal common blocks; complete-case and missing-bound targets may differ.')
