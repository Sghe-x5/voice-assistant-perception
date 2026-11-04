# Reproduction audit — 2026-11-04

The repository was exported without ignored local files into a separate temporary
directory. A new Python 3.12 virtual environment was created without system site
packages; requirements were installed and all nine pinned public originals were
downloaded again. Every SHA256 matched. The initial clean run completed, and all
ten versioned aggregate CSVs matched the working results numerically exactly.

The audited version was then run with generated results removed and verified raw
inputs retained. All nine stages completed, including the lexical check, 1,000
training/test bootstrap draws per voice-transfer direction, 32 tests and PDF
generation. Aggregate row labels, missingness and values were checked again.
The final editorial revision was rebuilt in the same isolated environment.

## Repairs

- The runner now records the current attempt before executing steps and persists
  preflight/child/launch failures. A failed rerun cannot retain the previous
  successful status in the tested failure cases. Four focused tests cover this.
- An explicit regression check protects E4's design/user comparator.
- The full pipeline includes the lexical check; the paper now reports its tiny
  point increments and the limits of that representation.
- The direct Novikova et al. (2017) predecessor is cited with verified authors and
  methods. Predicting perceived intelligence from interaction features is not a
  new general idea.
- The article explicitly notes the latency source's 63 post-assignment fidelity
  exclusions; a full intention-to-treat effect cannot be recovered from that release.
- The abstract no longer implies calibrated inferential support for text-CV gains.

## Scope

The audit covers source integrity, executable reproduction, numeric consistency,
document generation, tested pilot-parser behavior and repository contents.
Raw questionnaires, individual predictions, transcripts, credentials, caches and
working conversations are not tracked. Local model inputs and failure handling
are tested; this is not a comprehensive security certification.

Successful tests do not establish construct validity, representative sampling,
causal mechanisms, measurement invariance, CV interval coverage or worldwide
priority. No new human pilot was collected. The broader live-voice research goal
remains unvalidated; see TASKS.md and the prospective protocol.
