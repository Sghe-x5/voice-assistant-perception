# Data flow

Pinned manifest → download/checksums → ignored data/raw/ → independent source
analyses → generated participant predictions and aggregate results → article.

src/analyze_voice.py, analyze_cocreation.py and analyze_latency.py keep units and
outcomes separate. compare_information.py compares information sets on the same
held-out people. bootstrap_voice_training.py includes empirical training variation.
predict_voice.py uses a separately saved final model and explicit input schema.

scripts/run_all.py orders analysis dependencies and tests before article creation.
review_stats/ provides independent arithmetic and ordinal diagnostics; review_text/
adds a limited lexical baseline. Only selected aggregates and the PDF are versioned.

The pilot is separate: local form → exported JSON → strict validator → descriptive
report. It never silently merges observations into the published-study analyses
or treats agent evaluations as human data.
