# Secondary-analysis protocol

Date: 2026-11-04. This is an analysis specification written during a secondary-analysis project, **not an externally timestamped preregistration**. Source articles and descriptive data were already inspected. All new hypotheses and model comparisons are exploratory and require independent confirmation.

## Research question and scope

Can perceived intelligence be distinguished from neighboring evaluations, and how much of it can be predicted from design, user characteristics, and recorded behavior without using other contemporaneous subjective judgments?

The original request concerns live voice-assistant interactions. Accessible data support narrower empirical tests: two voice-assistant video-vignette experiments (released eligible n=353 and n=200), one text/canvas co-creation experiment (n=148), and one text-LLM latency experiment (n=240). These are four studies from three publications, not a pooled homogeneous population. No new participants or simulated ratings are created. Cross-study participant overlap cannot be ruled out by public identifiers.

## Model: contextual evidence and attribution

Distinguish manipulated design signals D, recorded behavioral evidence B, pre-exposure user characteristics U, context C, latent perceived intelligence I, other subjective evaluations T, and behavior/utility outcomes O. Model I with correlated, rather than necessarily independent, item factors and with context-dependent associations of D, B, and U. Predictive equations exclude other contemporaneous ratings from the deployable feature block; a model using T is an explicitly diagnostic common-method benchmark. Factor models are measurement approximations, not causal graphs. No claim of theoretical firstness attaches to this decomposition.

## Exploratory hypotheses

E1: Intelligence is empirically distinguishable from credibility/competence trust, but the dimensions may be highly correlated. Compare one-factor and correlated-factor models, alpha, HTMT, factor correlations, and ordinal/rank sensitivities. Better fit is not evidence of statistical independence.

E2: Design and user covariates predict intelligence above a training-mean baseline on a held-out voice experiment. Use study-held-out prediction, training-only preprocessing/tuning, and separate common-method benchmarks. Negative R-squared is a reportable result.

E3: Selecting respondents using a post-treatment role-recognition check changes the estimated role contrast. Show full released eligible sample and explicitly defined selected subsets; do not call the former strict intention-to-treat because unavailable earlier exclusions exist. Neither subgroup comparison identifies a controlled causal effect of role recognition.

E4: Recorded co-creation behavior predicts intelligence beyond design and demographics. Compare nested ridge models under participant-disjoint outer folds and leave-condition-out testing. Distinguish pre-selection telemetry from end-of-session adoption, which is potentially a consequence rather than a cause of intelligence judgments.

E5: Latency effects vary by outcome and task in the text experiment. Analyze participants, not event rows; correct the stated families of outcome tests. No intelligence item exists in this dataset: it is a boundary-case study of perceived output quality.

## Safeguards

- Preserve original files and record sources, licenses, SHA256, exact rows and exclusions.
- Inspect scale endpoints and reverse coding; never infer direction from variable name alone.
- Use two-sided tests, effect sizes and confidence intervals; distinguish original authors' one-sided results.
- Fit all learned preprocessing inside each training fold; never use test labels to choose features, regularization or reported model.
- Use HC3 heteroskedasticity-consistent standard errors for linear associations. Report ordinal/rank sensitivities where implemented; continuous-item CFA is not fully ordinal validation.
- Resample individuals for bootstrap intervals. Prediction intervals from fixed out-of-fold predictions are conditional and do not fully propagate training uncertainty.
- Report all specified feature blocks, all tested outcomes, failed fits and negative results.
- Do not infer causes from same-session behavioral associations or treat significance/non-significance as proof of difference/equivalence.
- Do not harmonize different questionnaires merely by rescaling to 0–1.

## Documented exploratory extensions after initial results

Independent review requested a shallow nonlinear comparator for the co-creation
features. Nested histogram gradient boosting was added with the same outer
partitions; all candidate models are reported, including failures to improve.
The constant AI-note count (20 per session) was replaced with the observed user-
note count, after source inspection and before final reruns. No target-driven
feature selection was performed.

A post-hoc paired contrast of information sources was then added. It compares
concurrent evaluation predictors with the explicitly named comparison block on
the same held-out individuals, using 4,000 bootstrap resamples. Its confidence
intervals are conditional on fitted predictions. It is exploratory, not a
preregistered hypothesis or causal estimator of common-method bias. In repeated
latency CV the contrast uses averaged predictions, whereas primary metrics
average per-repeat performance; both estimands are labeled.

A final sensitivity subsequently resampled training and test participants and
retuned both voice models for 1,000 draws per transfer. Original participant IDs
define inner GroupKFold groups so duplicate bootstrap copies cannot leak across
folds. The altered grouped tuning protocol has its own original-sample reference.
This extension addresses empirical training variability for voice transfer only;
its results do not replace missing prospective observations or identify causal
effects. The initial 300-draw run was a development checkpoint; the final tables
use 1,000 draws. See `retraining_sensitivity.md` for seeds and verification.

## Planned outputs

Executable analysis for all three source datasets; participant-level cleaned derivatives without free text; exact predictions and fold assignment; numerical tables; figures; source and verification records; interim findings with limitations; an implementable prospective live-voice validation protocol clearly marked unexecuted. A deployment-ready universal smartness metric and a newly collected voice study are outside what these public data can substantiate.
