# FireSight

Historical bushfire ignition-risk backtests across the Perth peri-urban
interface, using daily satellite-derived event labels on a nominal 3 km grid.
The current implementation uses one-day-lagged weather. Additional forecast
horizons remain planned under FS-25; source availability and calibrated
probability quality still require review.

Group 14 · COMP6002 Semester 2 2026 · Master of AI, Curtin University

## Data delivery ready for team review

Yian's FS-35–FS-39 core files are delivered. Start with the [current handoff index](docs/yian-delivery/README.md) and [independent replay evidence](docs/yian-delivery/Yian_Replay_2026-10-30/README.md). The replay produced **3,448,016 held-out predictions**, reproduced the published spatial and baseline metrics, and exported **22,022 rows for 10–23 January 2025**. The **25.6 MB full output package** is uploaded to [Jira FS-37](https://asaduzzamanayon001.atlassian.net/browse/FS-37), attachment **10036**; it includes predictions, reconstructed weather/grid, the model and run/verification records.

Use the **2026-10-30_Replay** report, editable slide and speaking notes. **122 root tests and hosted CI passed**; local verification also includes six subtests. [PR #7](https://github.com/asaduzzamanayon01/firesight/pull/7) still needs a second member's review and upstream merge. Strict boundary, calendar-day and evaluation-methodology acceptance remains open; the export is an uncalibrated historical backtest.

## The problem in one paragraph

Australia's Fire Danger Rating System tells agencies how dangerous a fire
would be *if one started*. It does not estimate *where one is likely to
start*. Fire behaviour is largely physics; ignition in peri-urban areas is
largely human. FireSight targets the ignition question directly.

## Quick start

```bash
pip install -r requirements.txt
make synth        # synthetic data - no API key needed
make pipeline     # baseline -> train -> calibrate -> explain
make test
```

`make pipeline` runs baseline, training, calibration and explanation stages,
writing figures to `reports/figures/` and metrics to `reports/`. Runtime depends
on the data and machine. The current hosted smoke test verifies synthetic
data generation and the baseline stage; see the [latest verified 122-test CI run](https://github.com/YIAN-WANG-W/firesight/actions/runs/41079491271) and [branch Actions](https://github.com/YIAN-WANG-W/firesight/actions).

## Repository layout

```
config/config.yaml            All settings. No magic numbers in code.
scripts/make_synthetic.py     Development data generator
src/config.py                 Config loader + MLflow URI override
src/ingest/firms_client.py    FIRMS download + event clustering
src/features/grid.py          3 km grid (interface owned by Saad)
src/features/build_cell_days.py   Cell-day base table
src/features/join_weather.py  Lagged weather join
src/models/baseline_climatology.py   The number to beat
src/models/train_lgbm.py      LightGBM + MLflow
src/models/compare_models.py  Systematic model comparison
src/models/calibrate.py       Isotonic calibration
src/models/convlstm.py        Stretch goal, Sprint 4
src/evaluation/metrics.py     PR-AUC, Brier, reliability, top-k
src/evaluation/splits.py      LOSO, forward chaining, spatial blocks
src/explain/shap_explain.py   SHAP + leakage diagnostics
notebooks/01_eda_ignitions.ipynb   EDA
tests/                        Root suite plus data-quality and leakage checks
docs/decisions.md             Why every non-obvious choice was made
```

## Three things to understand before reading the code

**1. The unit of analysis is the cell-day.** A cell/date is positive when it
contains the first observation of a supplied grouped event. These labels
are satellite-derived proxies for ignition. Sa-ad's pending PR #14 documents
cases where the current 24-hour clustering can split a spreading fire; the
team's label-definition decision remains open.

**2. The latest filtered model population is 0.07784187% positive:**
2,684 of 3,448,016 cell-days over 1,573 cells. The original unfiltered
received-label audit has 2,822 of 3,452,400 positives (0.08174024%) over
1,575 cells. Keep those populations separate when reporting model metrics.
Earlier ~0.3% figures describe initial expectations/development data.

**3. Weather features use a one-day lag.** Implementation tests exercise the
lag and rolling windows. They do not establish historical reanalysis
availability or resolve UTC event days versus Perth weather days. The
[current review gates](docs/yian-delivery/Spatial_Update_2026-10-30.md) also
cover static-cell selection and the inner-validation priors.

## Metrics

| Metric | Answers | Note |
|---|---|---|
| PR-AUC | Can we rank cells? | Random reference is the evaluated population/fold positive fraction; full filtered population ~0.0007784, unfiltered ~0.0008174 |
| Brier | Are the probabilities right? | Lower is better |
| Brier skill | Better than always guessing the base rate? | 0 = no skill |
| Reliability | Does "20%" mean 20%? | Plotted every run |
| Precision@k | How many top-ranked cell-days have positive labels? | Existing pooled ranking; published daily capture statistics are reported separately |

Accuracy is not reported. See `docs/decisions.md` D2.

## Model selection

No algorithm is committed to in advance. `src/models/compare_models.py` runs
logistic regression, random forest, gradient boosting and (conditionally)
ConvLSTM through one shared harness; the best held-out PR-AUC wins.

```bash
python -m src.models.compare_models --sample 200000
```

## Definition of Done

A ticket moves to Done only when: reviewed by a second member · tests pass in
CI · documented · merged to `main` · any model run logged in MLflow.

## Environment

```bash
export FIRMS_MAP_KEY=YOUR_LOCAL_KEY  # replace locally; never commit the key
export MLFLOW_TRACKING_URI=sqlite:///mlflow.db
mlflow ui                     # http://localhost:5000
```


## Data quality and current delivery

The [source-file audit](docs/yian-delivery/Real_Data_Quality_Status.md) checks 2,846 supplied event rows and 56 weather point series. Before the existing static-source filter, labels contain 2,822 positives over 1,575 cells. The independently reproduced model uses **1,573 cells / 3,448,016 cell-days / 2,684 positives**. Keep both population definitions explicit.

The [Yian replay](docs/yian-delivery/Yian_Replay_2026-10-30/README.md) now supplies full held-out predictions, forecast.csv, matching input/output/code hashes and finished MLflow run **328aaa7e10cd4f55873fd0598c704ed3**. Spatial/baseline seasonal metrics reproduce the published CSVs, with mean PR-AUC **0.0102256655 / 0.0042608292** and daily top-5% capture **32.08%**. These results retain the current method's documented selection/validation limits. Original acquisition-window manifests and selected weather-model attribution remain unverified.

The non-mutating checker validates fields, values, duplicates, dates, coordinates and optional risk_percentile. With an explicit grid and inclusive date window, **--require-complete-cell-days** also detects missing whole days/cells/pairs. The actual 14-day export has complete coverage; strict bounds still flag **35 edge centres / 490 export rows**. The original full reconstructed weather has **76,720** flagged rows. No edge rows were dropped or moved to hide this result.

[Checker instructions](docs/data-quality.md) · [Source catalogue](docs/data-sources.md) · [Whole-team handoff](docs/yian-delivery/TEAM_HANDOFF.md) · [Full-package upload receipt](docs/yian-delivery/Yian_Replay_2026-10-30/Jira_Full_Package_Receipt_2026-10-30.json).

## Remaining acceptance

- Ayon/Sa-ad review edge/calendar-day/event rules, all-season label-derived static selection, priors before inner validation and LOSO future-season use.
- Another member reviews PR #7; merge and green upstream CI follow the repository's Definition of Done.
- Tabib integrates/reviews the Replay report and slide. Zarif tests the historical dashboard export. Yian and the team rehearse.
- The original acquisition provenance and the final submission receipts remain separate evidence requirements.

Jira's current workflow has only To Do, In Progress and Done. Delivered work awaiting review/integration is labelled explicitly; it remains In Progress until its actual acceptance conditions are met. This does not mean the delivered files are missing.
