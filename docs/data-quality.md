# FS-35 / FS-36 data quality integration

Owner: Yian Wang. Local integration candidate based on main ad480505e229fc118b6e8b1a1a9796c2d48bb550, inspected 29 October 2026. Not a merged commit. Real data validation remains pending.

The CLI defaults to config/config.yaml's bbox and five weather columns. Repository ignition inputs use event_id, latitude, longitude, acq_datetime, detections_in_event, date. The adapter checks that the date equals the UTC acquisition day, preserves subsecond event precision, and checks IDs and positive integer detection counts. Weather inputs use cell_id, date and the configured numeric fields; supply a grid with unique cell_id plus centroid_lat/centroid_lon or lat/lon. Forecast inputs use cell_id, lat, lon, date, probability, actual, season. Do not use an OOF predictions file as forecast.csv without Ayon's documented exporter.

From the integrated repository root, after installing requirements.txt:

```bash
python -m pytest
ruff check src scripts tests
python scripts/check_data_quality.py \
  --ignitions data/raw/ignitions_ACTUAL_START.parquet \
  --weather data/processed/weather.parquet \
  --grid data/processed/grid.csv \
  --forecast data/processed/forecast.csv \
  --data-mode real --output-dir reports/data-quality/ACTUAL_RUN
```

Replace example filenames with the actual supplied files. This command is not a claim that those files exist. Add --start YYYY-MM-DD and --end YYYY-MM-DD to check an agreed interval; these check supplied rows against the bounds, not that every expected day exists. Optional --revision should contain the actual integrated commit, not the unmodified base SHA. --bbox and --weather-features explicitly override config. --schema canonical supports the earlier lat/lon/date ignition fixture schema and explicit column maps. The repository adapter currently follows main's UTC event-day rule; --date-timezone does not switch that event-day contract to PR #3's Perth-day protocol.

Results: quality-report.json and quality-summary.md, with file SHA256, missing counts, timestamps, duplicate and coordinate errors, label summaries, and the caller-declared data mode. Exit 0 means supplied inputs passed configured checks; 1 means a failure, including an unreadable file; 2 means invalid arguments. Fewer than all three tables may be checked, but complete_input_set remains false. A pass does not authenticate provenance, confirm full seasonal coverage, establish feature availability at issue time or certify a scientifically correct event definition.

Validation on this candidate: 75 tests passed (32 original tests, with corrected downloader date expectations, plus 43 added checks). Controlled CSV and Parquet fixtures only. Ruff passes for Python source/scripts/tests. Full-repository Ruff still reports eight pre-existing notebook findings. No real API request, model training or hosted CI run was performed.

Read data-sources.md before collecting real data. Reconcile PR #3's differing bbox, timezone, clustering and grid with Ayon and Sa-ad. Preserve provider responses and source manifests; do not count missing downloads as zero-fire seasons. Reports and raw files remain local unless explicitly selected for evidence submission.

## Latest upstream integration

Main 41584f9 now supplies CI, weather acquisition and forecast export scripts. The refreshed combined candidate passes 83 local tests and ruff check . with the upstream notebook exclusion. See [latest evidence](yian-delivery/Latest_Integration_Status.md) for the current result; the 75-test evidence above is the earlier snapshot. Hosted fork CI passed on code revision 61851c4 (Python 3.10); review, upstream merge and real-data checks remain pending.

## Current checkpoint after cc00735

Sa-ad’s geography module is now merged. This refresh passed 83 root tests plus 10 separately run geography tests with pyproj, and fixed five new geography lint findings. Actual real inputs are still needed for FS-37 despite FS-21–FS-24 being Done. See [checkpoint](yian-delivery/Progress_Check_2026-10-29.md).


## Real-file audit on 30 October

The forwarded six-season ignition files and five raw weather JSON batches were checked offline. See [measured report](yian-delivery/Real_Data_Quality_Status.md) and [audit script](../scripts/audit_received_data.py). Event checks pass; reconstructed weather retains the existing strict bounds failure (35 grid centres / 76,720 rows). No forecast was supplied. The earlier waiting-for-files notes describe historical checkpoints.


## PR 15 forecast extension and current evidence

The exporter now adds `risk_percentile` to the seven required fields. If present, FS-36 validates that it is numeric, finite and in [0,1], while retaining support for the agreed seven-field format. It is a relative daily rank, not a calibrated probability. The actual export remains absent. See [current spatial update](yian-delivery/Spatial_Update_2026-10-30.md) for filtered population reconciliation and methodological review limits.
