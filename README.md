# FireSight

Historical bushfire ignition-risk backtests across the Perth peri-urban
interface, using daily satellite-derived event labels on a nominal 3 km grid.
The current implementation uses one-day-lagged weather. Additional forecast
horizons remain planned under FS-25; source availability and calibrated
probability quality still require review.

Group 14 · COMP6002 Semester 2 2026 · Master of AI, Curtin University

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
data generation and the baseline stage; see the [current CI run](https://github.com/YIAN-WANG-W/firesight/actions/runs/40979703928).

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

Start at [Yian’s FS-35–FS-39 delivery index](docs/yian-delivery/README.md) for current files and owners, then the [latest spatial/filter reconciliation](docs/yian-delivery/Spatial_Update_2026-10-30.md). The original [received-file audit](docs/yian-delivery/Real_Data_Quality_Status.md) checks 2,846 event rows and 56 raw weather points; its 2,822 positive cell-days are explicitly unfiltered. Latest filtered model counts are 2,684 positives over 1,573 cells. Strict coordinate validation retains 35 outside-bbox centres; Sa-ad documents intended edge coverage, while approval of the acceptance rule remains pending. Actual forecast and run provenance are still required. Published summary arithmetic has been checked; prediction-level model scores have not been reproduced.

[Checker instructions](docs/data-quality.md) · [Source catalogue](docs/data-sources.md) · [Whole-team handoff](docs/yian-delivery/TEAM_HANDOFF.md). PR #7 awaits second-person review and upstream merge. Fixture/CI tests and measured data checks are distinct.


### Latest spatial/filter update

Main a86e39b / PR #15 is integrated. See [current evidence](docs/yian-delivery/Spatial_Update_2026-10-30.md): static-source filtering reproduces 1,573 cells / 3,448,016 cell-days / 2,684 positives (0.07784187%), replacing the unfiltered population only for the new model run. Published spatial/baseline CSV means are 0.01022567 / 0.00426083; summary arithmetic and counts are checked, with selection/validation limits retained. The forecast exporter adds risk_percentile. Local root suite: 95 passed + 6 subtests; geography: 10 separately; lint passed. Current hosted smoke/CI status is linked from PR #7.
