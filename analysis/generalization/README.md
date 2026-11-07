# Данные Vafa et al.: состав выборки и две модели

Offline examination of the public release accompanying Vafa, Rambachan
and Mullainathan, ICML 2024. This is a check of data suitability, **not a
new voice-perception study or a replication of every model in their paper**.

Primary [paper](https://proceedings.mlr.press/v235/vafa24a.html), inspected
[full text §§3–4](https://arxiv.org/html/2406.01382v1), and pinned
[repository](https://github.com/keyonvafa/human-generalization-llms/tree/526ba59931749c052fb88ff4a17d27a348bb149d).

## Reproduction

Upstream `train.py` reads train.csv → `model.tokenize_function` → BERT training →
`ckpts/bert.pth`; `evaluate_belief_change_models.py` reads test.csv and the saved
model, computes predictions/NLL/AUC, then its two simple baselines read train.csv.
The baseline features are prior correctness and whether source1 equals source2.
The upstream evaluator also writes other model predictions later in that script.

Our `audit_release.py` independently reads only the two hash-pinned CSVs, computes
aggregate structure/overlap and optionally reproduces those two non-text baselines.
It never imports upstream code, loads checkpoints, downloads models or calls APIs.

```bash
git clone https://github.com/keyonvafa/human-generalization-llms.git /path/to/source
git -C /path/to/source checkout 526ba59931749c052fb88ff4a17d27a348bb149d
.venv/bin/python analysis/generalization/audit_release.py --source /path/to/source --baselines --output /path/to/comparison.json
```

The output must not exist. Baseline reproduction uses this project's numerical
environment; structure check uses only the standard library. No raw survey rows
or question texts are redistributed. Repository MIT licensing does not erase
rights in the benchmark questions from other sources.

## Directly computed findings

| Property | Training release | Test release |
|---|---:|---:|
| Rows | 18,480 | 492 |
| Missing cells in the six documented fields | 0 | 0 |
| Rows labelled belief change | 7,970 | 211 |
| Distinct source tasks, across both positions | 79 | 69 |
| Duplicate complete rows beyond the first | 1,637 | 0 |
| Duplicate (q1,q2,previous_correct) rows beyond the first | 2,735 | 0 |
| Conditioned pairs containing both labels | 1,098 | 0 |

Repeated judgments and differing labels are retained. Without respondent IDs,
the release cannot identify which repetitions involve which people; these counts
are **not evidence of accidental duplication or annotation errors**.

Exact conditioned and unconditioned ordered pairs shared across train/test: **0**.
Nevertheless, 432/492 test rows have q1 seen somewhere in training and 429/492 have
q2 seen; **384/492 have both questions seen**, while only **15/492 have both unseen**.
Every test task is present among training tasks. Comparisons use exact text only;
no semantic near-duplicate search was performed.

This is compatible with testing new combinations of familiar questions. It is
not, by itself, proof of improper leakage, nor a test of held-out task families.
Our prospective deployment targets must be named separately: new person, new
question/episode, new combination and new operation/domain.

## Small numerical replication

| Author-code baseline | Recomputed NLL | Recomputed AUC | Published rounded NLL / AUC |
|---|---:|---:|---:|
| Previous correctness | 0.665624 | 0.599282 | 0.666 / 0.599 |
| Previous correctness + same task | 0.636533 | 0.687625 | 0.637 / 0.688 |

Both reproduce at the paper's displayed precision. NLL was also checked with
direct logarithms and AUC with positive-negative pair comparisons: errors below
1.2e-16. No test-set tuning or outcome-based sample selection was added. BERT and
other LLM results were not reproduced. These point metrics have no new population
confidence interval or causal interpretation.

## What the files do not measure

The paper describes adaptive training-pair selection and an intentionally
enriched final test stage; test labels aggregate at least eight judgments by
majority. Therefore 492 rows are not 492 individual participants, and label
prevalence is not ordinary-use prevalence. The six released columns contain no
participant ID, original prior/posterior values, direction/magnitude of belief
change, direct intelligence rating, voice signals or process intervention.

This release is useful for a forecasting baseline and for learning how to define
generalization targets. It cannot establish our proposed process-versus-halo
mechanism, recover individual updating dynamics or replace new human observations.
Do not pool its labels with the project's intelligence questionnaires.

## Checks and limitations

Source hashes are in source_manifest.json; aggregate calculations are in
release_audit.json. The script hash and sklearn version accompany outputs.
Synthetic tests cover role-crossed question overlap, repeated/discordant labels,
correctness-conditioned keys, invalid data, hash refusal and Unicode record
boundaries. The calculations were cross-checked against a separate pandas
calculation. Source files remained unchanged.
