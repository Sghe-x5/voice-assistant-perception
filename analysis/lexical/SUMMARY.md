# Lexical-content check: executed result

2026-11-04. DeepSeek drafted the program; the project reviewed every source line,
corrected unknown-condition filtering and silent ID/column handling, then ran it
locally on the original human data. No participant text was sent to DeepSeek.

| Frozen outer scheme | Design/user/log R² | Plus AI-text R² | Increment |
|---|---:|---:|---:|
| Participant | −0.008001 | −0.007861 | +0.000140 |
| Condition | −0.013877 | −0.013336 | +0.000541 |

The 142 retained sessions and outer splits match the earlier analysis. Each fold
fits character TF-IDF and all preprocessing inside training; penalties are tuned
inside four-fold CV. The comparison baseline is refitted with the same expanded
penalty grid and LSQR solver, so it is not numerically identical to the original
table's baseline. Every model is retained in lexical_metrics.json.

This representation adds negligible point-prediction value in these splits.
It is a lexical baseline, not a validated measurement of creativity or semantic
quality. It does not refute the broader missing-content explanation or establish
equivalence. No p-values or CV confidence intervals were invented. Outcomes are
the original human ratings, not model-generated ratings.

Run `python analysis/lexical/analyze_lexical.py` from the root. Input hashes and chosen
penalties are saved. All point metrics were independently recalculated from the
142 unique-ID prediction rows; maximum discrepancy is below 1e−12. See
the saved prediction rows and metrics. No new dependency or paid API is needed.
