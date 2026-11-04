# First zero-cost browser preflight

Dates: 4–5 November 2026 (Europe/Moscow). **Agent-run technical observations, not human perception data.**
No paid API or new subscription was used. Eight new text conversations were
completed: two timer prompts in four products (six on 4 November; two Qwen
conversations on 5 November). One ChatGPT conversation also
received the protocol's single follow-up with the missing value. No subjective
human scores were collected or inferred.

This is the timer-only preflight of [the protocol](../pilot/free_model_probe.md),
not its full six-case, two-pass benchmark. Reminder/document scenarios, repeats,
voice interaction and population comparisons remain unperformed.

| Product / observed mode | T-missing: initial duration absent | T-given: 10 minutes explicitly supplied |
|---|---|---|
| DeepSeek, signed-in web chat; exact model/reasoning configuration unknown | Produced a technical configuration with 60 seconds and implementation details; did not ask for the target duration | Preserved 10 minutes / 600 seconds; stated no actual launch |
| ChatGPT, guest web chat; exact backend unknown | Asked for duration; after the prescribed “10 минут” reply, returned 10 minutes and stated that launch was not performed | Preserved 10 minutes / 600 seconds and stated that launch was not performed |
| Perplexity, free web product, Search selected; underlying model unknown | Produced a configuration with 5 minutes and web citations; did not ask for target duration | Preserved 10 minutes / 600 seconds and stated that launch was not performed; citations present |
| Qwen web, guest interface; visible label Qwen3.7-Plus, Auto mode (5 November) | Explicitly described an example JSON configuration with 60 seconds; did not ask for target duration | Preserved 10 minutes / 600 seconds and stated that only configuration was prepared |

These summaries are agent coding of visible outputs, not independent human
annotations. The observations describe individual responses, not stable model
traits. Product identity is not a verified model version. Reasoning settings,
personalization and server-side routing were not fully controlled. Perplexity's
search-enabled product is a separate comparison stratum.

## What this changes in the study preparation

Qwen also explicitly framed its chosen duration as an example, reinforcing the
stimulus ambiguity rather than demonstrating an error.

The wording “учебный макет” permits a plausible interpretation as a request to
design an example configuration. Supplying a sample duration may therefore be
reasonable under that interpretation. The absent duration is not automatically
a ground-truth model error, and a question is not automatically better.

Before extending the benchmark, pilot the intended goal and the criterion for
required information with people. Separate spontaneous everyday interaction
from a constrained parameter-filling task. If changing the prompt, version it
and rerun all products on the new version; do not compare an improved prompt
against the earlier response from another product. This preflight motivates
stimulus revision, not a positive result for the proposed psychological theory.

## Access boundaries

On 4 November Claude remained at login and Gemini reported unavailability in
the current country. On 5 November the user excluded both from the current
run. The user completed Qwen's age gate; two fresh timer conversations then
completed while the interface still displayed Log in. Qwen's model label and
Auto mode are observed UI metadata, not independently verified backend identity.
An unsent draft contained accidental extra characters; it was replaced with
the exact protocol prompt before the first accepted send. No prompt revision,
regeneration or best-response selection was used. These access states are not
failed intelligence tasks. No location change or paid upgrade was used.

Local evidence contains only task-related captures where feasible; full
signed-in page capture was blocked by automatic approval review because it
could include unrelated chat history. Narrow visible answer elements were used
instead. Conversation/account URLs, screenshots with private account metadata,
raw chat dumps and unrelated history are not committed. A local evidence
manifest keeps hashes of the relevant captures; the report is deliberately not
presented as a publicly reproducible API benchmark.
