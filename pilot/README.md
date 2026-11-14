# Study materials and tools

| Purpose | Materials |
|---|---|
| Study expectations about an assistant's performance on new tasks | [Assistant and module experiment](process_transfer/README.md) |
| Record and annotate real interactions | [Observation guide](../docs/fieldwork_start_ru.md) and [annotation codebook](../docs/dialogue_codebook_ru.md) |
| Collect ratings after interactions with two assistants | Form and instructions below |

## Comparing two assistants

1. Read the [study instructions](protocol.txt).
2. Open the [HTML form](rating_form.html) locally in a browser.
3. Complete the [six scenarios](prompts_ru.txt) with each assistant.
4. Record your ratings after each dialogue and export the responses as JSON.
5. Process the export using the [analysis instructions](analysis_readme.txt).

The form stores responses locally. Use `scoring_key.json` for annotation after
recording subjective ratings. The scripts specify fixed prompts. To study open
dialogue with clarification, use follow-up prompts that depend on the assistant's
response.

The [pair planner](plan_comparison.py) generates assignments across a panel of
assistants:

```bash
.venv/bin/python pilot/plan_comparison.py --models pilot/model_panel.example.json --seed 20261104 --output pilot/local-comparison-plan
```

Edit the [example panel](model_panel.example.json) to choose configurations.
Transfer the assignments to the form manually and record the product settings
used in each interaction. The planner generates assignments offline.
[Technical probe instructions](free_model_probe.md) cover test runs.

Record repeated dialogues under the same participant ID. Track automated runs
separately from participant ratings. Store transcripts and exports outside Git.
