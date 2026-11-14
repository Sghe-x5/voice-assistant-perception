# Supplementary analyses

| Analysis | Purpose | Command from the repository root |
|---|---|---|
| [Arithmetic checks](validation/README.md) | Independently recalculate statistics and prediction metrics | `.venv/bin/python analysis/validation/check_arithmetic.py` |
| [Ordinal measurement checks](validation/README.md) | Compare factor structure using polychoric correlations and unweighted least squares | `.venv/bin/python analysis/validation/ordinal_structure.py` |
| [Text features](lexical/SUMMARY.md) | Test whether text from AI-generated ideas improves prediction beyond session features | `.venv/bin/python analysis/lexical/analyze_lexical.py` |

Run `scripts/run_all.py --download` to prepare the data and reproduce the main
results. The runner includes the text-feature analysis. The arithmetic and
ordinal checks can be run separately.

The [analysis of Vafa et al.'s benchmark](generalization/README.md) reproduces two
baselines for predicting changes in human expectations about AI and examines the
training and test splits. It uses a separate dataset and outcome.
