# Independent statistical review

Review date: 2026-11-04. Read-only inputs; all numerical review outputs stay here.
No project analysis module
is imported or executed by these scripts.

Run from the repository root with the existing pinned environment:

```sh
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python analysis/validation/check_arithmetic.py
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python analysis/validation/ordinal_structure.py
```

`check_arithmetic.py` independently reconstructs voice composites, HTMT, CFA
implied covariances/ML discrepancies, role estimates and HC3 intervals. It refits
the main two voice models in both transfer directions and the first resampled
training/test draw in each direction without calling project functions. It also
checks co-creation point metrics and source-level latency contrasts/Holm correction.
Results and tolerances are in `arithmetic_checks.json`.

Two comparator checks accompany the arithmetic checks:

- `median_baseline.csv`: training-median constant for the MAE comparison; 4,000
  fixed-predictor test-participant bootstrap draws, seed 130719. These intervals
  omit training variability, exactly as identified in the report.
- `cocreation_increment_vs_design.csv`: point differences against design/user
  predictions, the comparator specified in E4. No inferential CI is asserted.

The **one substantial additional analysis** is `ordinal_structure.py`: marginal
thresholds estimated from observed category frequencies, pairwise polychoric
correlations under a bivariate-normal latent-response assumption, then standardized
one- and two-factor off-diagonal ULS fits. Pearson ULS fits use the same criterion
to isolate the change of correlation estimator. This is an exploratory ordinal
structure sensitivity, **not WLSMV, an invariance test, or full ordinal CFA with
robust inferential fit indices**. It intentionally reports no chi-square, RMSEA,
p-value or factor-correlation confidence interval.

`ordinal_structure.csv` contains residual summaries; `ordinal_metadata.json`
contains assumptions, input hashes, numerical checks and HTMT; the pair tables,
correlation matrices and loadings allow independent inspection. The original
Pearson-HTMT bootstrap interval cannot be reused for polychoric HTMT.

Numerical checks: all seven categories present; independence probabilities agree
with the outer product of marginal proportions; fitted cell probabilities sum to
one; 64/128-point quadrature and exchange of item order agree within 1e-5; no
boundary pair estimates; positive-definite correlation matrices without repair;
three factor-fit starts converge to the same objective. Sparse cells are retained
and counted, not silently merged. These checks verify implementation, not coverage
of scientific confidence claims or truth of latent-normal assumptions.

No new responses, participant records or artificial rating datasets are generated.
The scripts use the existing numpy/pandas/scipy/scikit-learn environment.
