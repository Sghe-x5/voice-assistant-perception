"""Prepare balanced A/B pilot allocations for many models. Never run models.

This is a diagnostic pilot schedule, NOT a power calculation or confirmatory
randomization. Each participant uses the existing two-model form. Every model
pair occurs twice, with opposite starting orders. Task order remains fixed.
"""
import argparse
import copy
import hashlib
import itertools
import json
from pathlib import Path
import random
import re

if __package__:
    from .analyze_pilot import load_json, schedule, text
else:
    from analyze_pilot import load_json, schedule, text


def make_plan(models, tasks, seed):
    """Return prospective allocations; retain stable model IDs across pairs."""
    if type(seed) is not int or seed < 0:
        raise ValueError('seed must be a nonnegative integer')
    if not isinstance(models, list) or not 2 <= len(models) <= 8:
        raise ValueError('Supply 2..8 model configurations')
    if (not isinstance(tasks, list) or len(tasks) < 2 or len(tasks) % 2
            or any(not isinstance(t, str) or not re.fullmatch(r'[A-Za-z0-9_-]+', t) for t in tasks)
            or len(set(tasks)) != len(tasks)):
        raise ValueError('Tasks must have unique safe IDs and positive even count')
    ids = []
    for m in models:
        if not isinstance(m, dict) or set(m) != {'model_id', 'product', 'version', 'mode', 'details'}:
            raise ValueError('Each model needs exactly model_id, product, version, mode, details')
        if any(not text(m[k]) for k in ('model_id', 'product', 'version')):
            raise ValueError('Model identity fields must be nonempty strings')
        if m['mode'] not in ('text', 'voice_text', 'live_voice'):
            raise ValueError('Use an explicitly documented comparable interaction mode')
        if m['details'] is not None and not text(m['details']):
            raise ValueError('details must be text or null')
        ids.append(m['model_id'])
    if len(set(ids)) != len(ids):
        raise ValueError('model_id must be unique')
    if len({m['mode'] for m in models}) != 1:
        raise ValueError('Do not mix modalities; create separate plans')
    allocations = []
    for left, right in itertools.combinations(models, 2):
        for first in ('A', 'B'):
            allocations.append(dict(models={'A': copy.deepcopy(left), 'B': copy.deepcopy(right)},
                                    first_model=first, schedule=schedule(tasks, first)))
    random.Random(seed).shuffle(allocations)
    for index, a in enumerate(allocations, 1):
        a['allocation_id'] = f'allocation-{index:03d}'
    canonical = json.dumps({'models': models, 'tasks': tasks}, sort_keys=True, ensure_ascii=False)
    return dict(schema_version='comparison-plan-1.0', status='planned_not_observed', seed=seed,
                input_sha256=hashlib.sha256(canonical.encode()).hexdigest(),
                planned_slots=len(allocations), planned_dialogues=len(allocations)*len(tasks)*2,
                allocations=allocations,
                limitations=['No model calls, responses, human participants or ratings exist in this file.',
                             'A/B are local slots; retain model_id and exact configuration for each allocation.',
                             'Task order is fixed; carryover, learning and brand cues remain uncontrolled.',
                             'This count balances a complete pilot block; it is not a justified sample size.',
                             'Copy one allocation into the existing form manually; no automatic import.',
                             'Do not combine multiple exports from the same person as independent people.'])


def write_plan(plan, output):
    """Write into a new directory only; never overwrite human data."""
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    (output / 'plan.json').write_text(json.dumps(plan, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    for a in plan['allocations']:
        (output / (a['allocation_id'] + '.json')).write_text(
            json.dumps(dict(status='planned_not_observed', **a), ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--models', type=Path, required=True, help='JSON array of model configurations')
    parser.add_argument('--seed', type=int, required=True)
    parser.add_argument('--output', type=Path, required=True, help='New output directory')
    args = parser.parse_args()
    tasks = [t['id'] for t in load_json(Path(__file__).with_name('tasks.json'))]
    try:
        plan = make_plan(load_json(args.models), tasks, args.seed)
        write_plan(plan, args.output)
    except (ValueError, OSError) as exc:
        parser.error(str(exc))
    print(f"Planned only: {plan['planned_slots']} allocation slots, {plan['planned_dialogues']} dialogues; no observations.")


if __name__ == '__main__':
    main()
