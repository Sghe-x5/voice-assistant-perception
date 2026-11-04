# Training-variability sensitivity for the voice prediction gap

This is a supplementary, exploratory analysis of the same released human observations. It introduces no synthetic outcomes or additional participants. It addresses the earlier conditional intervals' omission of retraining variability. Code: `src/bootstrap_voice_training.py`; run with `.venv/bin/python src/bootstrap_voice_training.py --draws 1000`.

## Protocol

For each transfer (E1→E2, and E2→E1 assertive arm), independently resample the training participants and the test participants with replacement, preserving their original sample sizes. Keep all original row values and study assignments. Use 1000 draws per transfer, with a fixed seed (202611041) and an independent child random stream for each direction. In every draw, evaluate the training-set target mean, the design-plus-reported-user-attributes Ridge model, and the same-survey credibility-only Ridge model on the **same** resampled test participants. This pairing removes avoidable resampling noise from model differences.

Each Ridge model repeats imputation, scaling, five-fold tuning over alpha {0.1,1,10,100,1000}, and final fitting within the resampled training set. The tuning score is mean absolute error. **All copies of a bootstrapped participant share an inner-CV group.** Explicit assertions require disjoint original participant IDs between every inner-training and inner-validation fold, and between original external-training and external-test studies. Therefore, duplicated responses cannot inflate validation performance by appearing on both sides of a fold.

This protocol uses GroupKFold rather than the original shuffled KFold. It is not numerically the identical training algorithm used in the main transfer analysis; grouping is required for leakage-free tuning on bootstrap duplicates. We also refit the original unresampled data with GroupKFold and report these reference values, so the comparison does not confuse a tuning-protocol change with resampling variability.

## Estimands and interpretation

Three paired contrasts are primary for this sensitivity analysis:

- MAE(design+user) minus MAE(credibility-only): positive values favor the subjective benchmark.
- R²(credibility-only) minus R²(design+user): positive values favor the subjective benchmark.
- MAE(training mean) minus MAE(design+user): positive values indicate operational-model improvement over a constant.

The 2.5th and 97.5th empirical percentiles incorporate variability in both training-set composition and test-set composition, including the discrete hyperparameter-selection step. They do not establish nominal confidence-interval coverage; the tuned estimator is nonlinear and the finite empirical bootstrap is approximate. At 1000 draws, each 2.5% tail contains approximately 25 draws, so percentile endpoints retain Monte Carlo error. The raw draws are saved to permit inspection or a larger future run.

These intervals still condition on the two studies, their experimental protocols and stimulus sets, the released eligibility filters, chosen predictors and chosen model classes. They do not describe uncertainty over new products, cultures, languages, scenario families or hypothetical deployment populations. The two directions share data and are not independent replications. Credibility remains a contemporaneous same-rater benchmark, not objective telemetry, and its predictive advantage does not prove a causal common-method mechanism.

## Outputs and checks

- `results/voice_retraining_bootstrap_draws.csv`: all 2000 draws, sample sizes, unique participant counts, selected alphas, model metrics and paired contrasts.
- `results/voice_retraining_reference.csv`: GroupKFold reference fits on the original samples.
- `results/voice_retraining_bootstrap.csv`: reference estimates and percentile intervals.
- `results/voice_retraining_bootstrap.json`: complete protocol, sign conventions, limitations and runtime checks.

Every draw checks identity separation, finite metrics and shared paired resampling. Reproducibility concerns the statistical CSV outputs; the JSON runtime field and progress timings necessarily change between runs.

An initial 300-draw development run identified a training-variability sensitivity. The final run uses 1000 draws per transfer to stabilize percentile tails; this increases Monte Carlo precision without changing feature sets, model classes, split definitions, or outcome-selection rules. The 300-draw outputs are superseded by the final run.

## Final 1000-draw results

Positive MAE reductions favor the named more-informed model. Intervals below include training and test resampling and are percentile bootstrap approximations.

| Transfer | Contrast | Grouped-CV reference | 95% bootstrap interval |
|---|---|---:|---:|
| E1_to_E2 | MAE reduction: credibility vs design+user | 0.3237 | [0.2108, 0.4285] |
| E1_to_E2 | R² gain: credibility vs design+user | 0.4960 | [0.3205, 0.6314] |
| E1_to_E2 | MAE reduction: design+user vs mean | 0.0169 | [-0.0002, 0.0667] |
| E2_to_E1_assertive | MAE reduction: credibility vs design+user | 0.3893 | [0.2820, 0.4908] |
| E2_to_E1_assertive | R² gain: credibility vs design+user | 0.5514 | [0.4229, 0.6853] |
| E2_to_E1_assertive | MAE reduction: design+user vs mean | 0.0123 | [-0.0411, 0.0577] |

The same-survey benchmark advantage remains positive in both transfer directions. The modest operational-model advantage over the mean has intervals spanning zero once training variability is included. The forward lower endpoint is extremely close to zero (−0.000205), so its sign should not be overinterpreted given finite-bootstrap Monte Carlo variation. Therefore the earlier forward conditional interval excluding zero is insufficient to claim a robust operational improvement. This finding does not establish that richer objective telemetry could never predict perceived intelligence; those measurements are absent from this voice dataset.

Verification: all 2000 draws have finite metrics, paired differences recompute exactly, and every reported percentile endpoint was recalculated independently from the saved draws. The first 300 draws in each final transfer reproduce the separately executed development run byte-for-byte. Details and hashes: `results/voice_retraining_verification.json`.
