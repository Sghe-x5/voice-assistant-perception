# Assistant and module experiment

A participant reads a fictional scenario in which an assistant and a separate
module each perform one of two operations. The assignment of operations varies
while the final answer stays the same. The participant rates the assistant and
forecasts success on four new tasks. Module availability on those tasks varies
independently. The [protocol in Russian](PROTOCOL.md) specifies the design,
contrasts and limits of interpretation.

The implementation uses scripted text, an offline HTML form and an analysis
script. Participant recruitment and data collection for this design are pending.

## Generate pages

Run from the repository root with Python 3.12. The script uses the standard library.
The following command creates a batch for the authors to check the procedure:

```bash
python3.12 pilot/process_transfer/study.py build \
  --seed 20261105 --batch-id author-debug-v02 --output pilot/local-process-v02 \
  --role developer_pilot --origin human_observer \
  --study-info 'Author walkthrough. Responses are downloaded locally and can be kept or deleted.'
```

The output contains the assignment plan, instructions and 256 HTML pages covering
the combinations of conditions. Each page is filled out in a browser and exports
a local JSON file. Refreshing the page clears unsaved responses. The 256 pages
describe the allocation design. Sample size requires a separate calculation.

For data collection, issue one unused page per person in the assigned sequence.
Each block of four balances the two main factors. Incomplete blocks and refusals
can affect balance. Keep the assignment log and participant codes separate from
the pages. Reserve `developer_pilot` for authors. For external volunteers, use
`--role volunteer` and a separate batch ID with the contact, participation,
retention and withdrawal arrangements in `--study-info`.

## Import responses

```bash
python3.12 pilot/process_transfer/study.py analyze \
  --plan pilot/local-process-v02/plan.json \
  --exports /absolute/private/path/S001-P-0123456789ab.json \
  --output pilot/local-process-report-v02.json
```

The importer checks each export against the original plan and preserves missing
answers. Comprehension checks are reported separately. Intelligence, liking,
usefulness, reading effort and credit are reported separately, with the credit
item shown after the forecasts.

The descriptive report records differences in forecasts, coverage and bounds
for missing answers. `common_block_crossover` uses blocks with coverage in both
conditions. `full_design_crossover` stays `null` until the full planned design is
covered. Missing-answer bounds give possible ranges over submitted exports.
The report separates sample roles, data origins, presentation order and module
availability.

## Software checks

Use a new output directory and label automated responses `synthetic_test`:

```bash
python3.12 pilot/process_transfer/study.py build \
  --seed 20261105 --batch-id synthetic-v02 --origin synthetic_test \
  --study-info 'Software check with synthetic responses.' \
  --output pilot/local-process-synthetic
python3.12 -m unittest discover -s tests -p 'test_process_transfer*.py' -v
python3.12 pilot/process_transfer/diagnostics.py
```

`diagnostics.py` calculates mathematical examples in which aggregate forecasts
appear to change by operation even though individual changes reflect general
impressions.

An optional browser check requires Playwright and Chromium, or `CHROME_PATH`:

```bash
node tests/process_transfer_browser.cjs pilot/local-process-synthetic
```

It checks completed and partial exports, import, narrow-screen layout, network
requests and JavaScript errors. Use a directory without existing `export-*.json`
files.

## Versioning and storage

Version 0.2 changes the conditions and response fields. Use a separate checkout
at commit `be517c13ff8066422f2886c41b2c1b6c0f9f682c` to read version 0.1 exports.
Keep each allocation plan with its original instrument version and build a new
batch when the instrument changes. Store plans, exports and individual reports
outside Git.
