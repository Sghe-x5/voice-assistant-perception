# Secondary analysis results

| Published dataset | Participant records | Outcomes |
|---|---:|---|
| Two voice-assistant video-vignette experiments | 353 and 200 | Perceived intelligence and credibility |
| Text-based co-creation with GPT-4.1 | 148 | Perceived intelligence and other evaluations |
| Text interaction with assigned response delays | 240, with 237 used for prediction | Usefulness, thoughtfulness and other response-quality ratings |

Each source was analyzed separately. The voice-assistant data capture ratings
after watching scripted interactions. See [data provenance](../data/PROVENANCE.md)
for inclusion rules, source links and measures.

## Voice-assistant vignettes

**Measurement.** Perceived intelligence and credibility had a pooled score
correlation of 0.744. A correlated two-factor model fit better than a single
factor (RMSEA 0.105 vs. 0.156), with residual misfit.
[Score associations](voice_measurement.csv) · [Factor models](voice_cfa.csv)

**Prediction across experiments.** Ridge models trained on the first experiment
and tested on the second achieved R² = 0.022 from conditions and user
characteristics, and R² = 0.518 from same-survey credibility ratings. The
credibility model serves as a diagnostic comparison between ratings from the
same participant. Across 1,000 bootstrap draws per direction with retraining,
its advantage persisted. The intervals for the gain from conditions and user
characteristics over a constant prediction included zero.
[Prediction results](voice_prediction.csv) · [Retraining results](voice_retraining_bootstrap.csv)

**Role recognition.** In the pooled analysis, the estimated role contrast
(partner minus servant) was -0.055 points across the 553 released records.
It was +0.410 points among the 328 participants who passed the first or sole
role recognition check. The check took place after assignment, so conditioning
on its outcome can change the composition of the comparison groups.
[Role contrasts](voice_effects.csv)

## Text interaction

**Co-creation.** Adding session events to conditions and user characteristics
changed R² by +0.0047 on held-out participants and -0.0131 on held-out
conditions. Adding TF-IDF text features also yielded small changes.
[Feature comparisons](cocreation_increment_vs_design.csv) ·
[Prediction results](cocreation_prediction_metrics.csv) ·
[Text-feature analysis](../analysis/lexical/SUMMARY.md)

**Assigned response delays.** Event counts predicted thoughtfulness and
usefulness weakly. Models using other ratings from the same questionnaire
achieved R² of approximately 0.50 and 0.55, respectively. This study measured
response quality without a direct perceived-intelligence rating.
[Prediction results](latency_prediction_metrics.csv) ·
[Condition contrasts](latency_contrasts.csv)

## Reproduction

Run `scripts/run_all.py --download` from the repository root. Participant-level
files and predictions are generated locally and kept outside Git. The
[information-source comparisons](information_gap.csv) use resampling with fixed
predictions. Interval coverage for the text cross-validation analyses has not
been established. The [voice retraining analysis](../research/retraining_sensitivity.md)
resamples training and test participants and refits models.

[Analysis protocol](../research/analysis_protocol.md) ·
[Verification](../research/verification.md)
