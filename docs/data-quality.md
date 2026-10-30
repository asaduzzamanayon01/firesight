# FS-35 and FS-36 data quality integration

Owner: Yian Wang. Updated 30 October 2026. Current code integrates upstream main **a86e39b / PR #15**. The latest follow-up adds explicit expected cell/day coverage and passes **120 local tests + 6 subtests** and lint; use the [branch Actions](https://github.com/YIAN-WANG-W/firesight/actions) for revision-specific hosted evidence. PR #7 awaits review and upstream merge. Start at the [current handoff index](yian-delivery/README.md) and [spatial/filter reconciliation](yian-delivery/Spatial_Update_2026-10-30.md).

## Inputs and supported schemas

The CLI reads CSV and Parquet. Defaults come from config/config.yaml: bbox [115.45,-32.60,116.55,-31.40] and weather features t2m_max, rh_min, wind_speed_max, precip_24h, kbdi.

| Input | Required structure | Interpretation |
|---|---|---|
| Seasonal ignition events | event_id, latitude, longitude, acq_datetime, detections_in_event, date | Subsecond acquisition precision retained; date must match UTC acquisition day; detection counts must be positive integers |
| Weather | cell_id, date and all five configured numeric features | Supply a grid to resolve rows without coordinates |
| Grid | Unique cell_id and WGS84 centroid_lat/centroid_lon or lat/lon | Current strict rule checks every supplied centre against bbox; current main grid has 35 flagged edge centres |
| Forecast | cell_id, lat, lon, date, probability, actual, season | Finite probability in [0,1], binary actual, consistent cell coordinates and unique cell/date keys |
| Optional forecast extension | risk_percentile | If present, finite numeric values in [0,1]; daily relative rank, not a calibrated probability |

Event IDs reset in the six received seasonal files. Validate each file independently or use the received-data audit below. A combined key must include the source season; never deduplicate those files by bare event_id. The adapter follows main's UTC event-day contract. --date-timezone does not convert that repository event-day rule into the geography module's Perth-day convention.

## Run the ordinary validator

From a clone of the delivery branch after installing requirements.txt:

```bash
python -m pytest
ruff check src scripts tests
python scripts/check_data_quality.py \
  --ignitions data/raw/ignitions_ACTUAL_START.parquet \
  --weather data/processed/weather.parquet \
  --grid data/processed/grid.csv \
  --forecast data/processed/forecast.csv \
  --data-mode real --revision ACTUAL_DELIVERY_COMMIT \
  --output-dir reports/data-quality/ACTUAL_RUN
```

Replace placeholders with supplied filenames and the actual code revision. The example does not assert those files exist. Use Ayon's documented exporter rather than renaming an OOF-prediction file to forecast.csv.

Optional --start YYYY-MM-DD and --end YYYY-MM-DD constrain supplied dates; they do not establish complete coverage of every expected day. --bbox and --weather-features override config explicitly. --schema canonical supports earlier lat/lon/date ignition fixtures and explicit column maps. A caller-declared real mode does not authenticate acquisition provenance.

### Require an explicit complete daily population

Add **--require-complete-cell-days**, together with **--grid, --start and --end**, to require every supplied grid cell on every inclusive calendar day. It applies to supplied weather/forecast tables in either schema; sparse ignition-event tables are excluded. This opt-in requirement leaves ordinary validation unchanged.

```bash
python scripts/check_data_quality.py \
  --forecast data/processed/forecast.csv \
  --grid data/processed/ACTUAL_APPROVED_RUN_GRID.csv \
  --start ACTUAL_YYYY-MM-DD --end ACTUAL_YYYY-MM-DD \
  --require-complete-cell-days --data-mode real \
  --revision ACTUAL_DELIVERY_COMMIT \
  --output-dir reports/data-quality/ACTUAL_RUN
```

Replace every placeholder and use the **approved actual run population and its exact date window**. Do not use the unfiltered 1,575-cell grid to require coverage from an intentionally filtered 1,573-cell model export. The checker does not infer static-cell exclusions, edge-cell acceptance or the correct calendar-day rule. For outputs with different date windows, run separate commands. A future-horizon or otherwise different forecast contract needs explicit agreement before applying this retrospective daily contract.

Both reports show expected/observed unique cell-days, missing pairs, cells absent throughout the window, dates absent across all expected cells and a grid SHA256. Duplicate rows, unknown cells, out-of-window dates and malformed daily dates cannot fill gaps. Bad coverage returns exit **1**; missing required coverage arguments return **2**. Key presence does not approve coordinates, feature values, acquisition completeness or model performance. Issue counts overlap and must not be summed as a count of distinct bad rows.

The [coverage addendum and reproduction steps](yian-delivery/Cell_Day_Coverage_Update_2026-10-30.md) record a full check of the locally reconstructed, unfiltered weather: **3,452,400 / 3,452,400 unique expected pairs**, no gaps or duplicates. This is a key-coverage result; the existing strict bbox failure remains.

Outputs are quality-report.json and quality-summary.md with SHA256 values, missing counts, time coverage, duplicate/coordinate errors and label summaries. Ordinary CLI exits: **0** configured checks pass, **1** invalid/unreadable input, **2** invalid arguments. A partial table set can be checked, but complete_input_set stays false. No source rows are repaired or deleted.

## Reproduce the supplied-file audits

[Original received-data audit](../scripts/audit_received_data.py) checks all six event tables and five weather JSON batches, reconstructing weather with existing main transformations. Its processing-code snapshot is recorded in the [original audit](yian-delivery/Real_Data_Quality_Status.md). Originals remain local; archive/member hashes and aggregate evidence are shared.

[Spatial update audit](../scripts/audit_spatial_update.py) applies the new static-cell filter to the same received events and reconciles published CSV arithmetic. It independently reproduces **1,573 cells / 3,448,016 cell-days / 2,684 positives (0.07784187%)**. The original unfiltered population remains **1,575 cells / 3,452,400 cell-days / 2,822 positives (0.08174024%)**. Full commands and input hashes are in the [spatial checkpoint](yian-delivery/Spatial_Update_2026-10-30.md) and its linked audit JSON.

These audit scripts exit successfully when execution completes; inspect table passed/issue fields and overall_acceptance. Successful audit execution does not override the preserved strict weather-boundary failure, missing forecast or methodological review gates. No model is retrained by either audit.

## Verification and acceptance still open

The latest coverage follow-up passes **120 local root tests + 6 subtests** and lint, including 25 new regressions for missing days/cells/pairs, duplicate masking, invalid keys, explicit filtered grids and CLI behavior. [Hosted CI on the earlier code revision c72d464 passed](https://github.com/YIAN-WANG-W/firesight/actions/runs/40979703928): **95 tests**, lint, synthetic-data generation and baseline smoke. See [branch Actions](https://github.com/YIAN-WANG-W/firesight/actions) and PR #7 for the latest exact-revision hosted result. Geography tests: **10 passed separately with pyproj** on c72d464, outside the hosted root suite. Sa-ad's pending PR #14 examples were checked separately: **7 passed / 2 expected failures** documenting clustering limits. These are separate scopes; do not add them into a single hosted-test total.

Received event structural checks pass. Raw weather point time axes are complete, with zero missing/nonfinite inspected values. Locally reconstructed weather still flags **35 outside-bbox grid centres / 76,720 rows**. Sa-ad's draft explains intended edge overshoot; the team must approve an explicit edge-cell acceptance rule and calendar-day/event definition. Preserve this result until that decision, rather than dropping rows or moving centres to manufacture a pass.

Ayon/Sa-ad also need to review the all-season label-derived static mask and spatial priors built before inner validation. Actual forecast.csv, held-out predictions, matching spatial-run provenance and source manifests remain absent. Passing tests and checking published summary arithmetic do not establish acquisition completeness, prediction-time availability, calibrated probabilities or unbiased model generalisation.

Read the [catalogue](data-sources.md) for provenance/attribution and the [current team index](yian-delivery/README.md) for next owners. Earlier 32/75/83-test integration snapshots are historical; they remain in the original archive and dated checkpoint files.
