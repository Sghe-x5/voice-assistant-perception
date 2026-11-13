"""Mathematical examples only. No participants, fitted model, power or evidence."""
import json
from math import exp
from statistics import mean


def logistic(x):
    return 100 / (1 + exp(-x)) if x >= 0 else 100 * exp(x) / (1 + exp(x))


def examples():
    # (same topic/same op, same topic/different op, different topic/same op, neither)
    from importlib import import_module
    module = import_module('pilot.process_transfer.study') if __package__ else import_module('study')
    stats = import_module('pilot.process_transfer.summaries') if __package__ else import_module('summaries')
    def score(values):
        return module.operation_score(dict(zip(module.CELLS, values)))
    supplied = [50, 50, 50, 50]
    operation = [70, 50, 70, 50]
    topic = [70, 70, 50, 50]
    uniform = [65, 65, 65, 65]
    # SAME latent global shift, DIFFERENT baseline headroom by operation.
    baseline = [0, 2, 0, 2]
    before = [logistic(x) for x in baseline]
    after = [logistic(x + 1) for x in baseline]
    def paired(left,right):
        return stats.point_diagnostics(dict(zip(module.ABS_CELLS,left)),dict(zip(module.ABS_CELLS,right)))
    neutral=[(logistic(0)+logistic(2))/2]*4
    signed=[logistic(1),(logistic(3)+logistic(-1))/2]*2
    mixture_base=[(logistic(b-2)+logistic(b+2))/2 for b in (2,0)]*2
    mixture_shift=[(logistic(b-1)+logistic(b+3))/2 for b in (2,0)]*2
    return dict(status='mathematical_counterexamples_not_observations', unit='percentage points',
                cells=list(module.CELLS),
                linear_examples={name:dict(supplied=supplied,derived=values,
                                          difference=score(values)-score(supplied))
                                 for name,values in [('operation',operation),('topic',topic),('global',uniform)]},
                nonlinear_global_shift=dict(supplied=before,derived=after,
                    difference=score(after)-score(before),
                    interpretation='A global log-odds shift alone produces nonzero raw probability interaction.'),
                paired_swap=dict(
                    neutral_fixed_probe=paired([50,88,50,88],[50,88,50,88]),
                    operation_credit=paired([70,50,70,50],[50,70,50,70]),
                    topic_only=paired([70,70,50,50],[50,50,50,50]),
                    homogeneous_global=paired(after,before),
                    same_direction_global_mixture=paired(mixture_shift,mixture_base),
                    opposite_signed_global_mixture=paired(signed,neutral),
                    mixture_construction='Two equally weighted mathematical types with baselines (0,2)/(2,0); swapping executor adds global +1/-1 on logits within type, no operation-specific shift.'),
                missingness_example=dict(complete_case_mean=20,
                    full_mean=mean([20,-20]),
                    interpretation='If a participant with score -20 skips a probe, complete-case mean becomes +20 instead of 0.'),
                conclusion='Positive crossover alone is insufficient. Opposed arm ordering challenges common-direction monotone global shifts, but signed heterogeneous global shifts can also mimic it. Marginal logits do not identify a unique mechanism.')

if __name__ == '__main__':
    print(json.dumps(examples(), ensure_ascii=False, indent=2, allow_nan=False))
