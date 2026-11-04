# Exploratory lexical-content increment

Specified 2026-11-04 after the original results and independent critique. This is
not a preregistration or an untouched confirmatory sample. This specification preceded implementation. DeepSeek drafted the code; local
review, repairs and execution are recorded in SUMMARY.md.

Question: do recorded AI idea texts contain incremental linear predictive
information about the actual human intelligence rating beyond the existing
design/user/log block?

Use the same 142 known-condition sessions and frozen participant/condition outer
fold assignments. Concatenate AI-authored note content by session/turn. Do not
use ratings, adoption flags, comments, demographics or condition labels as text.
Those labels are excluded from text extraction; the documented design/user
variables remain in the separate baseline. Original outcome values are used only
as supervised training targets and held-out scoring labels.

Compare training mean, design/user/log ridge and the same block plus train-fitted
character TF-IDF (3–5 grams; min_df=2; maximum 10,000 features). Tune every learned
transformation and ridge penalty inside four-fold inner validation. Report every
model and both frozen outer validation schemes. Report paired point differences
from the design/user/log comparator; no uncalibrated CV confidence interval or
post-hoc significance threshold.

A positive increment supports the informativeness of this lexical representation
in these held-out samples, not objective creativity, causal quality or voice
generalization. A zero/negative increment does not demonstrate that semantic
quality is irrelevant: char TF-IDF is limited, the sample is small, and genuinely
semantic or independent human content measurements remain untested. All records
are from the original human study; no AI-generated outcomes are added.

The script must stay offline, preserve originals, write only under review_text,
and expose joins, folds, selected penalties and predictions. Existing article
results are not overwritten. Any generated code is reviewed before execution.
