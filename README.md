# FireSight

Bushfire **ignition** risk for the Perth / Darling Scarp region of Western Australia.
FireSight predicts, for every 3 km grid cell and every day, the probability that a fire
*starts* there, using only information available the day before.

COMP6002 Computer Science Project, Curtin University, Group 14.

> **This is a backtest, not a live forecast.** Every prediction was made by a model that
> never saw that fire season during training (leave-one-season-out). The dashboard replays
> past dates; it cannot warn about tomorrow.

## Contents

- [Results](#results)
- [How it works](#how-it-works)
- [Quick start: synthetic data](#quick-start-synthetic-data)
- [Reproduce with real data](#reproduce-with-real-data)
- [Dashboard](#dashboard)
- [Repository layout](#repository-layout)
- [Rules the code enforces](#rules-the-code-enforces)
- [Limitations](#limitations)
- [Team](#team)

## Results

Real data, six fire seasons (Jul 2019 to Jun 2025), 1,573 cells, 3.45 million cell-days,
2,822 ignition events (positive rate 0.08%). Mean over six leave-one-season-out folds:

| Model | PR-AUC | Lift over random | ROC-AUC | Brier skill |
|---|---|---|---|---|
| Climatology baseline (seasonal and per-cell average) | 0.0043 | 5.1x | 0.674 | -0.0014 |
| LightGBM, weather and season only | 0.0021 | 2.6x | 0.736 | +0.0005 |
| **LightGBM, plus spatial and recent-activity features** | **0.0102** | **12.3x** | **0.863** | **+0.0038** |

- With weather and season alone, LightGBM **does not beat** the climatology baseline. The
  weather data is about 20 km wide, so neighbouring 3 km cells look almost identical to it.
- Adding spatial and recent-activity features (see `src/features/spatial_priors.py`) beats
  the baseline in **6 of 6** seasons.
- Operational reading: if a planner watches only the day's top 5% of cells, they cover
  **32%** of the ignitions that happened (random would cover 5%). The top 10% cover **46%**.
  This falls in later seasons, from 40% in 2019-20 to 18% in 2024-25.
- Calibration (isotonic) preserves the ranking and leaves the Brier score almost unchanged
  on real data, because the positive rate is so low.

Per-season tables and figures are in [`results_real/`](results_real). Numbers on synthetic
data only check that the pipeline works; they are never reported as results.

## How it works

1. **Labels.** NASA FIRMS active-fire detections (VIIRS SNPP standard processing) are
   clustered with DBSCAN into fire events. The earliest detection of each event is the
   ignition. Using every detection would teach the model fire spread, not ignition.
2. **Cell-days.** One row per (3 km cell, date), label 1 if a fire started there that day.
   Cells with a permanent heat source (35 or more ignition days) are excluded.
3. **Weather.** Open-Meteo archive (ERA5-based) on a 0.2 degree lattice: max temperature,
   minimum humidity, max wind, 24 h rain and a simplified KBDI drought index. Each cell
   uses its nearest lattice point. Weather is lagged one day, with 3, 7 and 30 day rolling
   windows.
4. **Features.** Weather, season, cell location, recent ignitions nearby, and historical
   ignition rates of the cell and its neighbours. Historical rates use training seasons
   only.
5. **Models.** Climatology baseline, then LightGBM with leave-one-season-out validation
   and MLflow tracking, then isotonic calibration on out-of-fold predictions.
6. **Outputs.** SHAP importance, top-k capture statistics and `forecast.csv` for the
   dashboard.

Why each non-obvious choice was made is in [`docs/decisions.md`](docs/decisions.md).

## Quick start: synthetic data

No API key and no downloads. It checks that the whole pipeline runs and that the tests
pass; it does not produce scientific results.

```bash
git clone https://github.com/asaduzzamanayon01/firesight.git
cd firesight
python -m venv .venv && source .venv/bin/activate      # Python 3.10 or newer
make setup                  # pip install -r requirements.txt
make reset                  # clear any earlier data, so synthetic and real never mix
make synth                  # generate synthetic cell-days (about 0.3% positives)
make pipeline               # baseline -> LightGBM -> calibration -> SHAP
make test                   # unit and leakage tests
```

Outputs: metrics in `reports/`, figures in `reports/figures/`, models in `models/`.
`make compare` also compares logistic regression, random forest and gradient boosting.
View the experiment log with:

```bash
mlflow ui --backend-store-uri sqlite:///mlflow.db       # http://localhost:5000
```

`make help` lists every target.

## Reproduce with real data

Needs a free NASA FIRMS key and an internet connection. Weather needs no key.

**1. Set up and clear synthetic data.** Never mix synthetic and real data.

```bash
make setup
make reset
cp .env.example .env        # then paste your key: FIRMS_MAP_KEY=...
```

Get the key at <https://firms.modaps.eosdis.nasa.gov/api/map_key/>. `.env` is ignored by
git.

**2. Download labels and weather.**

```bash
make labels      # one FIRMS call per season, writes data/raw/ignitions_<season>-07-01.parquet
make weather     # Open-Meteo lattice, cached in data/raw/openmeteo/, writes weather.parquet
```

Both steps resume from what is already downloaded. If Open-Meteo answers HTTP 429, wait a
few minutes and run `make weather` again. The FIRMS client splits each season into
requests of at most 5 days. Per-season logs go to `logs/`.

**3. Build features.**

```bash
make features    # cell-day table, then lagged weather join -> cell_days_features.parquet
```

Check the printed positive rate (about 0.08%) and the cells excluded as static heat sources.

**4. Train, calibrate and explain.**

```bash
make pipeline    # baseline -> LightGBM (leave-one-season-out) -> calibration -> SHAP
make demo-stats  # top-5% and top-10% capture, per season
```

Expected: LightGBM beats the baseline in every season, as in [Results](#results). Exact
digits can differ slightly with library versions.

**5. Export the forecast for the dashboard.**

```bash
make dashboard-data   # writes data/processed/forecast.csv and copies it to dashboard/data/
```

`make real` runs steps 2 to 5 in one go (after `make reset` and setting up `.env`).

All of steps 2 to 5 are the same commands as the synthetic route, except the data source.

## Dashboard

A static map page that replays the backtest for 1 Dec 2024 to 28 Feb 2025: drag the
slider to see each cell's daily risk percentile, with red dots where a fire really started.

```bash
make serve-dashboard      # http://localhost:8000
```

See [`dashboard/README.md`](dashboard/README.md). It needs an internet connection for the
map tiles.

## Repository layout

```
config/config.yaml              All settings (region, seasons, model, paths)
src/
  config.py                     Config and .env loader
  ingest/firms_client.py        FIRMS download and event clustering
  ingest/download_firms.py      Standalone FIRMS area download with manifest
  features/grid.py              3 km grid
  features/build_cell_days.py   Cell-day table and labels
  features/join_weather.py      Lagged and rolling weather join
  features/spatial_priors.py    Location, recent-activity and historical-rate features
  models/baseline_climatology.py
  models/train_lgbm.py          LightGBM, leave-one-season-out, MLflow
  models/calibrate.py           Isotonic calibration
  models/compare_models.py      Model comparison harness
  models/convlstm.py            Unused scaffold for a gridded model
  evaluation/                   PR-AUC, Brier, reliability, top-k, season splits
  explain/shap_explain.py       SHAP importance
scripts/
  fetch_weather_openmeteo.py    Weather and KBDI
  make_synthetic.py             Synthetic data generator
  export_forecast.py            forecast.csv for the dashboard
  demo_stats.py                 Top-k capture statistics
dashboard/                      Static map page (HTML, CSS, JS)
firesight-geo/                  Separate geospatial and validation module, own tests
results_real/                   Saved real-data results (CSV, figures)
notebooks/                      Exploratory analysis
docs/                           Decision log and data-source record
tests/                          Unit and leakage tests
```

Generated, not committed: `data/`, `models/`, `reports/`, `results/`, `logs/`, `mlruns/`,
`mlflow.db`, `.env`.

## Rules the code enforces

- **Metrics:** PR-AUC, Brier score and reliability curves. Accuracy is never reported: with
  under 1% positives, predicting "no fire" everywhere scores over 99% accuracy. A test
  checks this.
- **Splits:** leave-one-season-out only. No random splits, because adjacent days and
  neighbouring cells share weather.
- **No leakage:** weather is lagged at least one day, and `n_ignitions` is never a feature.
  Historical rates come from training seasons only. `tests/test_leakage.py` and
  `tests/test_spatial_priors.py` guard this.
- **Early stopping** uses a validation season taken from the training data, never the test
  season.
- **Calibration** is fitted on out-of-fold predictions after training.

## Limitations

- Backtest on six seasons for one region; it says nothing about live performance.
- Labels are satellite detections. They include some non-ignition heat (planned burns,
  industrial sources), and a few permanent heat-source cells are removed.
- Weather resolution (0.2 degree lattice) is coarser than the 3 km grid, so most of the
  skill comes from location and recent activity rather than weather.
- The spatial features partly encode where fires burned in the past, and skill varies by
  season (PR-AUC 0.0227 in 2019-20 against 0.0038 in 2024-25).
- Forecast horizon is next-day only.
- No vegetation, fuel or human-activity layers yet.

## Team

Group 14, COMP6002 Semester 2 2026.

| Member | Area |
|---|---|
| Asaduzzaman Ayon | ML, labels, weather, model runs, forecast export |
| Sa-ad | Geospatial grid and evaluation |
| Yian Wang | Data catalogue and data-quality checks |
| Tabib | Report and presentation |
| Zarif | Dashboard |
