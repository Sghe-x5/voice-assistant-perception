# Prospective designs after the adversarial review

Version 5 November 2026. **No new participants, ratings, effect estimates, power
results or preregistration exist for these designs.** The broader recommendation
is conditional; see [novelty review](novelty_review_2026-11-05.md). Clarification is
a comparator candidate, not a predetermined thesis topic.

## A. Repair the clarification comparison before using it

Let A be experimentally assigned availability of one recent, unambiguous parameter
in the assistant's input. User knowledge is held separate. An instrumented input
or controlled script is needed; ordinary speech transcripts do not establish A.
Let X be a policy, whose actual action depends on A:

| Assistant input A | State-aware baseline B | Information request Q | Candidate confirmation C |
|---|---|---|---|
| Available value v | Acknowledge and use v; no assumption and no question | Ask for the value again without displaying v | Present v and ask whether it is correct |
| Absent value | State a predefined default d as an assumption, then proceed | Ask for the missing value before proceeding | Present d as a proposal, ask for confirmation, then proceed |

Example with a duration: B-known “Ten minutes, understood”; Q-known “How long?”;
C-known “Ten minutes, correct?”; B-missing “I will assume ten minutes”; Q-missing
“How long?”; C-missing “Would ten minutes work?”. These are authored illustrations.
No real timer is started. Consent/authorization to act is a different speech act.

The same label C does not make verification of a supplied value identical to
proposing a missing preference. Similarly B is a contingent baseline, not a
constant assumption treatment. Broad repetition of the whole request is an
additional burden manipulation and is removed from the core comparison.

### What randomization identifies

For a direct intelligence rating Y, the conditional assignment contrasts are:

- Δknown = E[Y(Q) − Y(B) | A=available]. Cost/benefit of asking again versus using
  supplied information, including the extra exchange and displayed uptake.
- Δmissing = E[Y(Q) − Y(B) | A=absent]. Total effect of eliciting a value versus
  proceeding with an explicit default, including resulting success/mismatch.
- Γknown = E[Y(C) − Y(Q) | A=available]. Confirmation that displays a value versus
  bare re-request. Effort, wording and pragmatics must be examined, not assumed equal.
- Δmissing − Δknown is heterogeneity of a **state-contingent policy effect**.
  It does not isolate a pure psychological effect of information availability:
  the baseline action and downstream consequences also change.

Randomize conditions and exemplars, analyze assigned arms, retain failures and
abandonment with predefined missing-data handling. Final success/usefulness,
experienced effort and liking can be consequences of treatment. Regression
adjustment for them, post-hoc success matching and selecting only successful
sessions do not identify a controlled direct mechanism effect.

### Separate outcome-controlled experiment

If the question is what the process signals *at an identical final outcome*, use
an explicit controlled-stimulus study. Restrict the first experiment to known
information; randomize B/Q/C and deliver the same correct final artifact by design.
C versus Q is the narrower contrast; B also changes exchange count. A later
version can match the user response format/action count between C and Q, provided
cognitive interviews confirm the intended speech acts remain distinct.

All participants receive scripted or prerecorded material under the same rules;
label them observers or guided-interaction users accurately. Do not make a
missing-information system magically know the hidden value and call it natural
behavior. A fixed outcome estimates response to a controlled sequence, not the
total deployed-policy effect. Identical final answers do not make all intermediate
performance, information or experienced effort identical.

This comparison is useful but has close predecessors, including Zheng et al.,
Mai & Carson-Berndsen, See & Manning and commercial confirmation work. It is not
recommended as the sole novelty claim. If more precise evidence shows no
meaningful confirmation/re-request difference under valid controls, the uptake
mechanism loses support; an underpowered null is inconclusive.

## B. Recommended candidate: what capability does process evidence support?

Working question: **at the same final result, does observable evidence of a
specific operation change competence expectations selectively, or merely create
a generally favorable impression?** This must also affect directly measured
intelligence to explain that construct; forecast calibration alone is a different
result. Memory, repair, initiative and effort are alternative sources of evidence.

Closest threats already study memory/intelligence, selective corrections,
cross-task capability transfer, human generalization, reasonable AI failures and
halo from behavioral cues. Therefore this is a proposed mechanistic extension,
not a first theory of belief updating or a newly invented intelligence dimension.

### First pilot: distinguish informational credit from final-result halo

Use a deterministic task with a dependency change, such as a small schedule.
A correction to one duration requires updating one dependent end time while
preserving an unrelated constraint. Create several independent task instances,
not variants of a single story shown repeatedly to one person.

Prepare an identical corrected artifact for two process conditions:

1. The assistant visibly derives the dependent change from the correction.
2. The same numerical patch is visibly supplied by a separate component, and
   the assistant inserts it. Both reach the same final state.

Keep final correctness, user actions, number of presented steps, waiting time,
voice and presentation format fixed where feasible; log any residual differences.
Do not pretend this equals all evidence of performance: the source of the
operation is the intended intervention. Tool orchestration may itself be seen as
intelligent, so a uniformly lower rating for condition 2 is not assumed.

Before seeing outcomes on new tasks, participants forecast success for:

- a surface-different task requiring the demonstrated dependency operation;
- a surface-similar task requiring a different operation;
- an unrelated operation (negative control).

Probe tool availability is explicitly the same across conditions. A proposed
additional test varies whether that patch component is available for the new
probe, separating beliefs about the assistant from the composite system. Do not
add this factor to a tiny first pilot unless comprehension permits it.

Measure direct intelligence separately from usefulness, liking, trust and effort.
Use a brief warmth-only control in a separate pilot or a prespecified additional
arm to see whether positive style produces the same forecast pattern. Do not
create a score by averaging intelligence with these neighbors. Adapted scale
wording and construct distinction require human cognitive interviews and, later,
an adequately sized measurement study.

### Competing explanations and predictions

| Explanation | Discriminating prediction |
|---|---|
| Final-outcome evaluation | Little process-condition difference when the verified final artifact is identical |
| General halo / reassurance | Similar changes across capability probes and liking; warmth control can mimic them |
| Surface similarity | Greater transfer to same-topic probes, regardless of required operation |
| Operation-specific inference | Process × shared-operation pattern across topics; source of patch matters for relevant forecasts |
| Work/responsibility attribution | Effects depend on necessary vs avoidable user work or tool dependence, not just the operation |

The intended diagnostic is the process-condition × probe-operation interaction,
not merely “more intelligent” in one arm. Randomize assignment, counterbalance
probe order, keep all outcomes, and avoid showing the same story in both variants
to one participant. A before/after forecast design can introduce reactivity;
pilot an early-measurement versus post-only allocation before choosing it.

### Analysis contract and rejection criteria

Freeze one primary mechanistic contrast and one clearly designated direct
intelligence endpoint before main collection. Ordinal mixed models can model the
latter; bounded forecasts need an appropriate bounded/ordinal or transparently
specified robust model with participant and exemplar dependence. Define convergence
fallbacks and secondary multiplicity families in advance. Probabilities of 0/100
and unchanged rounded slider values are not proof of unchanged latent beliefs.

Compare simple global-shift, surface-similarity and operation-sensitive predictive
models on held-out exemplars and people, with training-only preprocessing/tuning.
Contemporaneous liking/usefulness are diagnostic outcomes, not privileged causal
controls. Any model claiming incremental intelligence prediction must beat simple
success/context baselines without importing the user's other post-treatment ratings.

Reject/reframe the operation-specific account in the tested setting if a sufficiently
precise prespecified interaction is practically negligible, if irrelevant probes
move equally, or if a warmth-only condition reproduces the pattern. If only future
forecasts change and intelligence does not, report structured capability inference,
not an explanation of perceived intelligence. If perceived usefulness/effort differs,
report it; do not claim those experiences were held fixed merely because counts match.
An imprecise pilot cannot accept equivalence or establish a universal halo model.

## C. What can be done at zero monetary budget

1. Authors debug the recording, timing, source labels and schema. Their own ratings
   remain developer pilot data, never an independent confirmation sample.
2. Recruit genuinely external adult volunteers through an authorized channel;
   no recruitment has happened. Use neutral instructions and practical consent,
   storage and withdrawal arrangements agreed with the supervisor.
3. First collect cognitive interviews and a small feasibility pilot. Fix the
   number based on available volunteers and goals, without a false power claim.
   Establish whether source and capability distinctions are understood.
4. Freeze codebook and task materials. New external episodes, not used to improve
   rules, form held-out codebook validation; record coder familiarity explicitly.
5. Choose a smallest meaningful effect/precision target and simulate the exact
   clustered design before a confirmatory sample. No defensible N is currently
   established. If the required sample is unavailable, publish a pilot/protocol
   or narrow the claim rather than manufacture precision.

Local scripted text/audio/Wizard-of-Oz needs no paid API. Text observers do not
become live-voice participants. A later instrumented voice transfer study and
new model versions test generality; brand count is not the novel contribution.
The existing eight timer dialogues only debug access and stimulus interpretation.
