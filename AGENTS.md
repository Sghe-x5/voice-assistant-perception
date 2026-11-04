# Research repository

Read README.md and ARCHITECTURE.md. Use Python 3.12.

```bash
.venv/bin/python scripts/run_all.py --download
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python src/predict_voice.py --input examples/voice_input.json
```

Without study data, the pilot parser can be tested separately:

```bash
python3 -m unittest discover -s tests -p test_pilot_analysis.py -v
```

## Scientific boundaries

- Preserve originals and source hashes. Never invent participants, ratings or citations.
- Keep video observers, text users, live voice users and agent runs distinct.
- Fit preprocessing and tuning only within training folds.
- Keep duplicate bootstrap copies of a person in one inner-validation group.
- OOF-row resampling does not establish calibrated CV confidence coverage.
- Nonsignificance is not equivalence; fit improvement is not construct validation.
- Report exploratory changes and negative results. Do not promise worldwide priority.
- Never commit questionnaires, participant exports, transcripts, credentials or chat dumps.
- External messages, access changes and data publication require explicit authorization.

## Definition of done

Run the affected analysis and relevant tests. Check numerical changes against
predictions; update tables and article together. Rebuild the article only after
its result inputs exist and inspect affected PDF pages. Review staged changes
and file list before committing; .gitignore intentionally uses an allowlist.
Use codex/ branches for new work and focused pull requests. No secret environment
variables or model-service accounts are required to reproduce the analyses.
