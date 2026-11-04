# Earlier prospective live-voice latency protocol

**Design status update (2026-11-04 audit):** Retained as an optional latency extension. The active proposed research sequence and primary context-by-clarification question are in [the research roadmap](../docs/research_plan_ru.md). Do not combine the two primary estimands or sample-size plans without a new protocol. Neither design has been executed.


Status: **design only; no participants recruited, no new observations collected, no ethics approval or public preregistration obtained for this protocol.** It is a specification for extending the completed public-data secondary analysis, not evidence that a live-user model has been validated. Version 2026-11-04.

## Scientific target

Primary question: how much additional out-of-user and out-of-task predictive information do independently manipulated interaction characteristics supply for *perceived intelligence*, beyond objective completion success and baseline user expectations? Secondary questions concern credibility and satisfaction as distinct outcomes, context-specific effects, and perception changes after a repaired error. The design must distinguish what causes an attribution from what merely predicts it after the interaction.

Primary estimand: the average effect of assigned latency on the post-trial direct perceived-intelligence rating, averaged over randomized correctness and repair-policy assignments. Two co-primary contrasts compare 3 versus 1 seconds and 8 versus 1 seconds; Holm adjustment across these two. Prespecified secondary effects include initial correctness, repair policy within error trials, and correctness×repair policy. Additional interactions and user heterogeneity are exploratory with family-level correction or hierarchical shrinkage.

## Stage A: instrument and task preparation

Use a separate pilot that is excluded from confirmatory analysis. Conduct cognitive interviews on translated questions and response anchors, including what 'intelligent', 'competent', 'responsible' and 'knowledgeable' mean for a voice assistant. Do not silently substitute 'conscious' for 'competent'. Preserve an item-version ledger with exact language, anchors, order and source. Translation requires forward translation, independent review, back translation and user comprehension checks; machine translation alone does not establish equivalence.

Candidate measurement battery:

- Perceived intelligence: the adapted five-item intelligence set used in the public voice study, with unchanged 1–7 anchors within this experiment. Collect the direct intelligent item after every trial; collect all five after each four-trial block to reduce burden.
- Perceived credibility: the five-item credibility set from the same source, after each block; record it separately, never include it among operational telemetry predictors.
- Satisfaction: a brief direct satisfaction item after each trial plus a predefined validated usability/voice-UX scale after each block. Do not create an undocumented composite from heterogeneous scales.
- Baseline expected competence before any exposure; prior assistant experience, relevant task expertise, language proficiency, accessibility needs and hearing conditions before randomization.
- End-of-study qualitative interview, analyzed separately from predictive labels.

Randomize intelligence/credibility battery order at the participant level and include order as a design factor. The pilot should check whether repeated ratings perturb interaction; compare brief and block-only variants before freezing the main protocol. Pilot-based scale modifications cannot be optimized on confirmatory outcomes.

## Stage B: independently randomized voice interactions

Use three instrumental scenario families with externally verifiable success: fact lookup, device-state control in a safe simulator, and constrained multi-step planning. Prepare multiple distinct task exemplars per family. A creative/social scenario should be a separate extension because objective correctness cannot be treated as the same construct without a validated rubric.

Cross three assigned factors: initial response correctness (correct/incorrect), added delay (1/3/8 seconds from end of user speech to first audible substantive response), and repair policy (proactive acknowledgement plus correction/minimal retry). This produces 12 assignment cells. Each participant completes 12 distinct trials, seeing each cell once, with scenario exemplars counterbalanced across cells across participants. Use a preregistered randomization generator and save its seed, assignment matrix and actual presented order. Blocks and scenario orders are counterbalanced; prohibit sequences with more than two incorrect trials consecutively. The generator must preserve equal marginal assignment probabilities under these restrictions.

Repair policy is assigned on every trial but has its principal causal contrast **within randomly assigned error trials**. A correctly answered trial need not exhibit a repair. Do not interpret lack of a repair in correct trials as a failed manipulation. After an initial response, a controlled opportunity to challenge or clarify is provided with identical wording across relevant conditions. Final completion may become equal across policies; record initial correctness and final success separately. Final success is potentially a mediator of assigned repair and must not be adjusted away in primary total-effect analyses.

Hold assistant identity, voice, loudness, substantive content, recognition pipeline and visual affordances constant. Use prespecified responses or a bounded response library for manipulated content so that latency is not confounded with verbosity or correctness. Real speech input and actual timestamps are required. Speech recognition errors should be logged and independently annotated; do not force an error by covertly substituting transcripts without describing the procedure. Exclude dangerous or consequential tasks. Debrief participants about deliberate inaccuracies and ensure no false advice persists beyond the session.

## Event schema and annotations

Each event must carry pseudonymous participant, session, trial, scenario-family and exemplar IDs; assigned condition; realized condition; monotonic timestamp; source clock; and event type. Record voice-activity start/end, ASR finalization, model request/response boundaries, first audible output, audio completion, interruption, user clarification, correction and task completion. Store timing definitions explicitly: first audio latency differs from completion latency and from network latency.

Compute prespecified features only from data available before the rating: task success; response delay; utterance duration; turn count; clarification count; self-correction count; unnecessary repetition; ASR word-error rate against a blinded transcript; independently rated factual correctness; verbosity relative to task requirement; interrupted-output fraction. Report missingness and recording failures by assigned condition. Acoustic features should be treated as optional, higher-dimensional predictors requiring separate regularization and microphone controls.

At least two blinded human annotators should label a prespecified subset of factual/task success and repair quality. Report disagreement before adjudication, the agreement metric suited to the label type, and adjudication rules. Model-generated evaluations may be supplementary but cannot replace human/user outcome labels while being described as user data.

## Analysis model and identification

For trial ordinal rating Y on categories 1–7, fit a cumulative-logit mixed model:

`logit P(Y_ust <= k) = threshold_k - [beta_X X_ust + beta_C C_s + beta_XC X_ust*C_s + gamma Z_u + b_u + q_s + r_exemplar + beta_order order_t]`.

Here X contains assigned factors and prespecified interactions; C is scenario family; Z consists of pretreatment attributes; b is participant intercept, q denotes scenario effects and r exemplar effects. Include participant random slopes for latency and correctness if recoverable; document convergence and regularization rather than silently dropping random terms. With only three scenario families, use them as fixed effects; random exemplar effects quantify variation across many task instances. A proportional-odds check and a more flexible ordinal sensitivity model should be planned.

Model the five-item blocks with a hierarchical ordinal measurement model separating intelligence and credibility, compared with a common-factor alternative. Assess configural, loading and threshold invariance across language and task conditions. If invariance fails, report partial or group-specific measurement; do not compare latent means without identification. Allow constructs to correlate; orthogonal rotation must not manufacture independence. Alpha is descriptive reliability, not validation.

For initial errors followed by repair, a secondary change model examines pre/post repair ratings only if both are collected without unacceptable reactivity. Otherwise, no claim about within-trial updating is permitted. Baseline expectation and experimentally observed experience must not be conflated. Mediation from latency through frustration or trust requires additional identification assumptions and should be labeled exploratory rather than causal by default.

## Prediction, generalization and uncertainty

Freeze operational feature availability before modeling. Compare: training mean; task-success-only; linear additive model; context-interaction regularized model; a prespecified nonlinear baseline; and contemporaneous questionnaire predictors as a clearly separate diagnostic. All imputation, feature selection, scaling and tuning remain inside training folds. Evaluate at least three deployment targets separately: a new participant, a new task exemplar, and a new scenario family. For the final target, hold out an entire family; wide uncertainty with only three families must be acknowledged.

An independent final cohort, not used to choose features or thresholds, should provide the main confirmatory performance estimate. Estimate MAE, ordinal log score, calibration and predictive intervals. Bootstrap or resample at participant level and at stimulus level as needed; treating thousands of turns as independent participants is invalid. A model that does not improve over the simple baseline should remain a negative finding, not trigger an unreported search over architectures.

## Power and stopping rules

No defensible fixed sample size is established by this protocol alone. Before recruitment, simulate the exact randomized schedule and hierarchical ordinal model. Use a transparent parameter grid covering participant intraclass correlation 0.15/0.35/0.55, plausible task-exemplar variance, ceiling-heavy versus balanced thresholds, 5%/15% missing sessions, and effect sizes anchored to a substantively chosen smallest relevant difference rather than the largest published estimate. Candidate participant counts 120/240/360 are planning grid points, **not a recommendation or achieved sample**. Simulate at least 1000 trials per final design point, report Monte Carlo standard error, false-positive rates under the null, model-convergence rate, coverage, and power for the prespecified corrected primary contrasts.

Choose the smallest feasible count meeting the prespecified power/precision requirement across the agreed plausible scenarios; if infeasible, revise the scientific target before data collection. Fix the recruitment count, technical-exclusion rules and maximum replacement count in the registration. Never stop when p<.05. Classify loss by timing relative to randomization; retain all available randomized observations in the primary model and report missing-data sensitivity. A manipulation-check failure is a diagnostic outcome, not automatic exclusion from primary causal analysis.

## Research governance and release

Obtain appropriate ethics review and informed consent for audio collection, voice-related biometric sensitivity, and optional public release. Share pseudonymous feature tables, code, stimuli where licensed, randomization and annotation procedures. Do not release raw identifiable speech without specific consent and a data-governance decision. Register hypotheses, analysis, exclusions, power simulation and test split before confirmatory recruitment. Archive an immutable version of code and manifests. This protocol requires real fieldwork and authorization; the current secondary-analysis artifacts do not imply those steps occurred.
