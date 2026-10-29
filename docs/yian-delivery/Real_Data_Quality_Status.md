# FS-37 real-data quality status

**Waiting for accessible real-run files, not for Ayon to start work.** Refreshed 29 October 2026 after main cc00735.

Ayon's FS-21, FS-22, FS-23 and FS-24 are now Done. Commits report six seasons of labels, weather integration, a real model run and forecast-related fixes. The corresponding actual input / output files were not obtained from Jira or tracked GitHub data directories.

| Required input | Current handoff state |
|---|---|
| Actual ignition events and source manifests | Not shared in the inspected sources |
| Actual weather.parquet and source manifest / units | Not shared |
| Actual forecast.csv | Not shared |
| Grid used by that run, cell IDs, bbox / date / event contract | Run-specific evidence not shared; two differing implementations now coexist in main |
| Run revision, coverage and per-season counts | Exact run evidence not shared |
| results_real metrics and plots | Mentioned by the author; no result files obtained |

[Detailed checkpoint and source links](Progress_Check_2026-10-29.md).

The model-run commit reports PR-AUC 0.0021 for LightGBM and 0.0064 for climatology, so the author reports that the baseline wins. The label commit reports 0.0817% positives. These are author-reported values, not Yian's measured quality results.

Once files arrive, follow [the validator instructions](../data-quality.md), keep hashes / revision, and separately check expected cell-day and seasonal coverage. Publish counts, missingness, failures and limitations; then update the report and slide. Fixtures prove tool execution only.
