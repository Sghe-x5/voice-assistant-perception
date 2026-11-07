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

## Recorded access and limits

Claude and Gemini were not included in these eight conversations because access
was unavailable in the tested setup. These are access limitations, not failed
intelligence tasks. The product modes in the table are observed interface metadata;
the exact model behind a service was not independently verified.

The repository contains aggregate observations, not account URLs, private chat
histories or raw exports. Local records cover the task-related visible answers.
This small manual check is not a publicly reproducible API benchmark. New model
comparisons require fresh access checks, a fixed protocol and recorded settings.
