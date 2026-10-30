# Yian independent spatial model replay

30 October 2026 (Perth). This is Yian's independently executed reproduction of the current main method, using received seasonal events and locally reconstructed weather. It is a provisional historical backtest. It does not authenticate Ayon's original run or approve unresolved modelling/boundary policies.

## Ready to use

- **Dashboard export:** [forecast.csv.zip](forecast.csv.zip), containing forecast.csv for **10–23 January 2025**. Extract and point the existing dashboard loader to it. There are **22,022 rows = 1,573 cells × 14 days**, including three positive cell-days.
- **Export grid:** [grid.csv](grid.csv). Use this filtered 1,573-cell grid with this export, not the unfiltered 1,575-cell grid.
- **Full output bundle prepared locally:** `Yian_Replay_Outputs_2026-10-30.zip` contains both models' held-out predictions, reconstructed weather/grid, the final model and run/validation records. Upload to Jira FS-37 is **pending explicit payload authorization** after automatic review rejected the full-data upload. In the meantime, **Yian_Replay_Summary_2026-10-30.zip** in [FS-37](https://asaduzzamanayon001.atlassian.net/browse/FS-37) contains only aggregate metrics, hashes and documentation. Original received ZIPs/event files remain local.
- **Run provenance:** [manifest](run-manifest.json) and [portable MLflow run record](mlflow-run-record.json). Run **328aaa7e10cd4f55873fd0598c704ed3**, status **FINISHED**. Core code is based on 501495d, which integrates main a86e39b; the new runner's own SHA256 and per-file hashes identify the exact executed source. A later publication commit does not change the run's recorded source snapshot.
- **Checks:** [prediction audit](prediction-audit.json), [strict forecast quality](forecast-quality.md), [quality JSON](forecast-quality.json).

## Measured result

All **3,448,016** six-season held-out predictions are present, finite, unique and complete on the supplied grid/date lattice. Recomputed prediction-level metrics match the saved result CSVs. Seasonal spatial and baseline PR-AUC values exactly reproduce the published CSV values at their stored precision. Spatial mean PR-AUC is **0.0102256655**, paired baseline **0.0042608292**; daily top-5% capture is **861/2,684 = 32.08%**. [Spatial CSV](lgbm_cv.csv), [baseline CSV](baseline_cv.csv), [capture CSV](demo_stats.csv).

The compact baseline implementation aggregates the same modulo-365 smoothing counts as the existing 31-fold row expansion. A regression includes leap/year boundaries and agrees with the original predictions to 1e-15. This saves memory without changing the baseline method. No sampling or shortened LightGBM estimator limit was used.

## Scope and acceptance

The CSV uses the existing exporter, raw uncalibrated held-out scores, its **0.00001 floor**, and daily risk_percentile. Use percentile for relative map ranking. Do not describe these values as calibrated probabilities or live future forecasts. No isotonic calibrator was fitted or applied in this replay.

Every forecast key and value check passes except the existing strict bbox rules: **35 edge centres / 490 forecast rows** are flagged, with none dropped or moved. Full original reconstructed weather retains the previously measured **76,720** flagged rows. Key coverage is complete; overall acceptance remains pending. Initial lag/rolling feature gaps are recorded in the manifest and handled by LightGBM's missing-value support.

The current main method retains an all-season label-derived static mask, spatial priors built before inner validation, UTC event days alongside Perth weather days, and LOSO training that can include future seasons. Reproduction confirms what this implementation produces; it does not resolve those evaluation/availability limits. Ayon/Sa-ad need to agree the policy and review these limits. Original acquisition-window manifests, selected weather-model attribution and Ayon's original spatial-run provenance remain unverified.

## Reproduce from the source branch

Use received `ignitions_*.parquet` files matching manifest hashes and the locally reconstructed weather matching its SHA256. Keep originals separate. Install the repository requirements in an isolated environment; on macOS LightGBM also needs an OpenMP runtime. The local replay used Python 3.12.14, pandas 2.2.3, LightGBM 4.7.0 and MLflow 3.17.2; the manifest records exact selected versions.

```bash
python -m scripts.reproduce_received_run \
  --events-dir PATH_TO_RECEIVED_SEASONAL_EVENTS \
  --weather PATH_TO_MATCHING_RECONSTRUCTED_WEATHER_PARQUET \
  --output-dir NEW_EMPTY_RUN_DIRECTORY \
  --source-revision ACTUAL_CHECKED_OUT_COMMIT \
  --forecast-start 2025-01-10 --forecast-days 14
```

The runner refuses to overwrite an existing directory and keeps process-local output paths. It builds labels/features, runs the unchanged spatial model, computes the equivalent baseline and capture summaries, exports forecast.csv, validates it and records MLflow provenance. Model artifacts and full-size data are prepared in the local full bundle pending upload authorization; the Jira summary contains no row-level predictions, weather/grid tables or model files. [Runner](../../../scripts/reproduce_received_run.py).

## Next owners

**Zarif:** test the provisional export with map/date/actual/ranking controls and label the demo as a historical backtest. **Tabib:** use the **2026-10-30_Replay** report/slide/notes and integrate/review them. **Ayon/Sa-ad:** review methodology, edge/calendar-day/event rules and original-source provenance. **Yian:** address agreed changes, obtain second-person review/upstream merge and rehearse. No Jira task is automatically moved to Done.
