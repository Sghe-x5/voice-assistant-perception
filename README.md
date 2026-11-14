# Perceived Intelligence in Voice Assistants

This project studies how people judge the intelligence of voice assistants and
form expectations about their performance on new tasks. It combines a reanalysis
of published ratings of scripted voice-assistant interactions with an experimental
design for studying how people evaluate an assistant that shares work with a tool.

Across the two video-vignette experiments, experimental conditions and user
characteristics gave weak predictions of perceived intelligence. Credibility ratings
from the same questionnaire predicted it substantially better.

## Research questions

- Do survey items on perceived intelligence and credibility capture distinct aspects of users' judgments?
- How well do experimental conditions and user characteristics predict intelligence ratings in a different experiment?
- When two versions of a scenario end with the same result, how does the division of work between an assistant and a tool shape expectations for new tasks?

## Repository contents

- [Measurement and prediction](results/README.md) — analyses of published user ratings.
- [Transfer study materials](pilot/process_transfer/README.md) — experimental protocol, scenarios, response form and analysis code.
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
