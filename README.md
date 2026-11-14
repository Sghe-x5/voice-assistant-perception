# Perceived Intelligence in Voice Assistants

Research code for measuring perceived intelligence in voice assistants and studying
how people form expectations about an assistant on new tasks.

- [Measurement and prediction](results/README.md) — analyses of published user ratings.
- [Transfer study materials](pilot/process_transfer/README.md) — scripted scenarios that vary how an assistant and a module share a task, with a response form and analysis code.
- [Benchmark replication](analysis/generalization/README.md) — reproduction of two baselines from Vafa et al. (ICML 2024) and an analysis of the train–test split.

## Reproduce the analyses

With Python 3.12, run from the repository root:

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python scripts/run_all.py --download
```

The runner verifies the input files, writes results to `results/`, and runs the tests.
See [data provenance](data/PROVENANCE.md) for sources and data access.
