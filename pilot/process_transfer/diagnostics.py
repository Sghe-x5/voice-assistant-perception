"""Mathematical examples only. No participants, fitted model, power or evidence."""
import json
from math import exp
from statistics import mean


def logistic(x):
    return 100 / (1 + exp(-x))


def examples():
    # (same topic/same op, same topic/different op, different topic/same op, neither)
    from importlib import import_module
    module = import_module('pilot.process_transfer.study') if __package__ else import_module('study')
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
    return dict(status='mathematical_counterexamples_not_observations', unit='percentage points',
                cells=list(module.CELLS),
                linear_examples={name:dict(supplied=supplied,derived=values,
                                          difference=score(values)-score(supplied))
                                 for name,values in [('operation',operation),('topic',topic),('global',uniform)]},
                nonlinear_global_shift=dict(supplied=before,derived=after,
                    difference=score(after)-score(before),
                    interpretation='A global log-odds shift alone produces nonzero raw probability interaction.'),
                missingness_example=dict(complete_case_mean=20,
                    full_mean=mean([20,-20]),
                    interpretation='If a participant with score -20 skips a probe, complete-case mean becomes +20 instead of 0.'),
                conclusion='The descriptive contrast is not a unique mechanism test. Check baseline/headroom and competing link-scale models before confirmation.')

if __name__ == '__main__':
    print(json.dumps(examples(), ensure_ascii=False, indent=2, allow_nan=False))
