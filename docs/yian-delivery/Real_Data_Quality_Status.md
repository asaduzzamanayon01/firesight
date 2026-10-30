# Real data receipt and quality check

Yian Wang · 30 October 2026 (Perth) · FS-35–FS-39 · supersedes the 29 October waiting-for-files checkpoint.

**The six seasonal event tables and five raw weather batches have been received and checked. Full three-table acceptance remains pending.** Ignition structural checks pass. Locally reconstructed weather has complete values but fails the current strict coordinate rule because 35 reconstructed grid centres lie outside the configured bbox. forecast.csv and run-specific provenance are still missing. Published metrics are now accessible, as described in the follow-up; no model training or prediction-based performance reproduction was performed.

## Current main population and result follow-up

Main has advanced to a86e39b through PR #15. The original input measurements below remain valid. Independently applying the new filter yields **1,573 cells, 3,448,016 cell-days and 2,684 positives (0.07784187%)**, exactly matching the new published result counts. Published CSV means are 0.01022567 spatial PR-AUC versus 0.00426083 paired baseline; top-5% capture arithmetic is 861/2,684 = 32.08%. Original predictions and a matching spatial MLflow run are still missing, so this is count/arithmetic reconciliation rather than model reproduction. Read the [full follow-up and review limits](Spatial_Update_2026-10-30.md). The older weather-only comparison is historical.

## Receipt and evidence

Victor forwarded ignitions.zip (82,048 bytes) and weather.zip (13,194,779 bytes) in WhatsApp at 23:41 on 29 October, describing them as real FIRMS and weather data. The exact local attachment bytes were copied unchanged on 30 October; ZIP CRC checks passed. The original archives and extracted observations remain local. Published evidence contains hashes, aggregate counts and response metadata.

- [Archive receipt and SHA256 values](Received_Archives_2026-10-30.json)
- [Detailed audit JSON, including every extracted file hash](Real_Data_Audit_2026-10-30.json)
- [Reproducible offline audit script](../../scripts/audit_received_data.py)
- Processing/validation code inspected: **e555d2aa41dd1be1d44d7bb9ebbe6be8feca3b54**, integrating upstream main cc00735. This identifies Yian's reconstruction code, not Ayon's unprovided model-run revision.

The forwarder's description is evidence of handoff, not independent authentication of source acquisition. Original FIRMS responses and request manifests were not in these archives. Weather JSON identifies units, returned coordinates and timezone, but does not establish the selected model, request parameters or original acquisition time.

## Supplied ignition tables

| July–June season | Event rows | Sum of detections_in_event | Required missing values | Within-file duplicate event IDs | Native structural result |
|---|---:|---:|---:|---:|---|
| 2019–20 | 620 | 5,025 | 0 | 0 | PASS |
| 2020–21 | 552 | 3,921 | 0 | 0 | PASS |
| 2021–22 | 523 | 5,115 | 0 | 0 | PASS |
| 2022–23 | 413 | 3,831 | 0 | 0 | PASS |
| 2023–24 | 350 | 3,547 | 0 | 0 | PASS |
| 2024–25 | 388 | 3,529 | 0 | 0 | PASS |
| **Total** | **2,846** | **24,968** | **0** | **0** | **All six pass** |

Each file contains event_id, latitude, longitude, acq_datetime, detections_in_event and date. The unchanged repository validator found no missing required fields/values, exact duplicate rows, duplicate event keys, invalid detection counts, invalid timestamps, event-day/UTC mismatch, out-of-season timestamps or out-of-bbox event coordinates. This is a structural result; the raw detections were not supplied to verify clustering or the recorded source-count sums independently.

**event_id is scoped to its seasonal file.** Bare IDs repeat across seasons (2,226 rows after the first occurrence), while (source season, event_id) is unique. Do not deduplicate the concatenation by bare event_id. Do not call these 2,846 rows independently confirmed ignition causes. The 24,968 number is the supplied grouped-detection-count sum, not a newly counted raw FIRMS table.

Before applying PR #15's static-cell filter, all 2,846 event rows receive a main-grid cell ID. They map to **2,822 positive cell-days**; 24 cell-days each contain multiple event rows. The original 1,575-cell × 2,192-day spine for 2019-07-01 through 2025-06-30 has **3,452,400 cell-days** and a positive proportion of **0.08174024%**, consistent with the author's earlier rounded 0.0817%. These are explicitly unfiltered measurements; the latest filtered model population is 1,573 cells / 2,684 positives, as reconciled above. Neither reconstruction reproduces model scores or verifies source-window completeness. An event-free day does not prove a successful zero-detection download.

## Raw weather and local reconstruction

| Check | Measured result |
|---|---|
| Raw batches | 5 JSON arrays: 12 + 12 + 12 + 12 + 8 points |
| Requested points / distinct returned coordinate pairs | 56 / 56 |
| Daily coverage at every point | 2,557 dates, 2018-07-01 through 2025-06-30; exact expected axis, no duplicates |
| Hourly coverage at every point | 61,368 hours; exact expected axis, no duplicates |
| Values and variable-array lengths | All expected lengths; 0 missing or nonfinite values in inspected variables |
| Timezone and units | Australia/Perth, UTC+08:00; daily maximum temperature °C, maximum wind m/s, rainfall mm; hourly relative humidity % |
| Observed raw ranges | Temperature 9.4–47.5 °C; wind 1.3–27.18 m/s; rainfall 0–96.6 mm/day; humidity 6–100% |
| Derived main weather | 3,452,400 unique cell-days, 2019-07-01 through 2025-06-30; 0 missing values in all five features |
| Grid mapping | Main grid uses 42 of the 56 request points; these are coarse weather inputs shared by many cells |

The received ZIP contains raw JSON, **not Ayon's processed weather.parquet**. The audit invokes the existing fetch_weather_openmeteo.py pure functions without making network requests: associate batches with the 0.2-degree request lattice, derive daily minimum humidity, compute the existing simplified KBDI, discard the 2018–19 spin-up year, and map main grid cells to their nearest request point. Mapping assumes the current script's batch order, inferred from filenames; a request manifest was not supplied. Returned provider coordinates are preserved in the audit because they differ from requested coordinates.

The reconstructed table has t2m_max, rh_min, wind_speed_max, precip_24h and kbdi. Its SHA256 is recorded in the audit JSON. It is a reproducible local reconstruction, not proof of byte identity with the model author's processed input.

**Weather validation result: FAIL under the existing strict bbox contract.** Main's reconstructed grid contains 35 centres outside bbox [115.45, -32.60, 116.55, -31.40], creating **76,720 weather rows** outside that rule. The unchanged checker reports both counts. No rows were deleted, coordinates moved, or rules loosened to manufacture a pass. Ayon and Sa-ad must approve whether intersecting edge cells are intended or change the grid, then regenerate/revalidate affected artefacts consistently.

## Remaining handoff and owners

| Owner | Required next action | Why it remains necessary |
|---|---|---|
| Ayon | Share forecast.csv, its manifest, actual model-run grid and processed weather hash/file, exact run revision, results_real metrics/plots and acquisition manifests | Forecast probabilities/labels, end-to-end joins, original retrieval completeness and model scores cannot be checked from these ZIPs |
| Ayon + Sa-ad | Confirm bbox/edge policy, event grouping and UTC event-day versus Perth weather-day interpretation; identify which of main and firesight-geo the run actually used | Two conventions coexist. Approving a documented edge-cell rule may be valid; current validation cannot assume that decision |
| Yian | Compare the author's artefacts with this reconstruction, validate forecast and agreed grid, publish final acceptance or remaining failures | Receipt and the checks above are complete; full run signoff remains conditional |
| Tabib | Integrate the refreshed report and slide and preserve the stated limitations | Use this dated evidence rather than earlier waiting-for-files attachments |
| Zarif | Integrate the supplied forecast into the dashboard and label it as historical backtest; retain offline demo evidence | These ZIPs contain no dashboard forecast export |

Main event dates follow UTC while supplied weather is grouped by Australia/Perth days. Reanalysis availability and simplified KBDI still require explicit retrospective interpretation. The earlier weather-only comparison (LightGBM 0.0021 versus climatology 0.0064) is historical. New spatial/filtered-baseline CSVs are now checked arithmetically in the linked follow-up; no predictions-based score reproduction is claimed.

## Reproduce offline

From this delivery branch's repository root, after extracting the archives without changing their member names into INPUTS/extracted/ignitions and INPUTS/extracted/weather:

```bash
PYTHONPATH=. python scripts/audit_received_data.py \
  --inputs INPUTS --output-dir LOCAL_OUTPUT \
  --source-revision e555d2aa41dd1be1d44d7bb9ebbe6be8feca3b54
```

The script writes reconstructed weather/grid/mapping locally and aggregate real-data-audit.json. Its successful process exit means the audit completed; **read overall_acceptance and each table's passed/issue fields**. It deliberately preserves a failing quality result and missing-forecast status. Do not interpret exit 0 as data acceptance.

## Publication and acceptance

This evidence, the audit script and refreshed report/slide belong on [PR #7](https://github.com/asaduzzamanayon01/firesight/pull/7) and FS-35–FS-39. The earlier 29 October ZIP and attachments remain historical snapshots. Root-suite and lint results establish code checks, separately from these observed data results. Second-person review, upstream merge, report/deck integration and actual rehearsal are still required where applicable. No automatic Jira Done command is requested.
