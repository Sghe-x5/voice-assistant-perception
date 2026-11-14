# Perceived Intelligence in Voice Assistants

How do people judge a voice assistant's intelligence, and how well do experimental
conditions and interaction features predict those judgments? This repository
contains secondary analyses of published human ratings and an experimental design
for studying how people form expectations about an assistant's abilities.

## Measurement and prediction

We reanalyzed two published video-vignette experiments with 353 and 200 participant
records. Participants rated voice assistants after watching scripted interactions.
Perceived intelligence and credibility had a pooled score correlation of 0.744.
A correlated two-factor model fit better than a single-factor model (RMSEA 0.105
vs. 0.156), with residual misfit. [Source study](https://doi.org/10.1080/15358593.2026.2621084) ·
[Measurement results](results/voice_measurement.csv) · [Factor models](results/voice_cfa.csv)

Ridge models trained on the first experiment and tested on the second achieved
R² = 0.022 with experimental conditions and user characteristics, and R² = 0.518
with credibility ratings from the same questionnaire as a diagnostic benchmark.
With 1,000 bootstrap draws per transfer direction, including retraining, the
benchmark retained its advantage. The bootstrap intervals for the reduction in
mean absolute error from conditions and user features over a constant prediction
included zero. [Analysis code](src/analyze_voice.py) · [Prediction results](results/voice_prediction.csv) ·
[Retraining analysis](research/retraining_sensitivity.md)

## Expectations about new tasks

The scenario experiment swaps which of two operations the assistant and a
supporting module perform, keeping the final outcome and amount of assistance
fixed. For subsequent tasks, module availability varies independently, and task
topic is crossed with operation. Mathematical counterexamples show that changes
in general impressions can produce apparent operation-specific effects in
aggregate forecasts. The repository contains the scenarios, response form and
analysis code for this design. The experiment is documented at the design and
software verification stage. [Study materials](pilot/process_transfer/README.md) ·
[Counterexamples](pilot/process_transfer/diagnostics.py)

An accompanying analysis reproduces two baselines from Vafa et al. (ICML 2024)
and examines the benchmark split. All test task categories were represented in
training, and both questions in 384 of 492 test pairs appeared individually in
training. The split evaluates new pairs within known categories.
[Source study](https://proceedings.mlr.press/v235/vafa24a.html) ·
[Reproduction and split analysis](analysis/generalization/README.md)

## Reproduce the analyses

Use Python 3.12. From the repository root:

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python scripts/run_all.py --download
```

The runner downloads and verifies the study files, rebuilds the analysis outputs
in `results/`, and runs the tests. [Data provenance](data/PROVENANCE.md) ·
[Results summary](results/README.md) · [Additional analyses](analysis/README.md)
