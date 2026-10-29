# FireSight

Predicting where bushfires are likely to **start** across the Perth
peri-urban interface: calibrated ignition probability on a 3 km grid, 24 to
72 hours ahead.

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

`make pipeline` runs end to end in about two minutes and writes figures to
`reports/figures/` and metrics to `reports/`.

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

**1. The unit of analysis is the cell-day.** One 3 km cell on one date,
labelled 1 if a fire *started* there. Only the first detection of each fire
event counts, otherwise the model learns spread rather than ignition.

**2. The received 2019–2025 labels are 0.08174024% positive** under the
current main grid (2,822 of 3,452,400 cell-days); earlier ~0.3% figures describe
initial expectations/development data. This motivates checking `scale_pos_weight` at training time, PR-AUC and Brier
instead of accuracy, and isotonic calibration afterwards.

**3. Weather is lagged by one day, always.** To predict day D we may only use
data available before day D. `tests/test_leakage.py` asserts this, and CI
fails the build if it regresses.

## Metrics

| Metric | Answers | Note |
|---|---|---|
| PR-AUC | Can we rank cells? | Random baseline = the evaluated dataset/fold positive rate; full received-label rate is ~0.0008174 |
| Brier | Are the probabilities right? | Lower is better |
| Brier skill | Better than always guessing the base rate? | 0 = no skill |
| Reliability | Does "20%" mean 20%? | Plotted every run |
| Precision@k | Of the top k cells, how many burnt? | What DFES actually acts on |

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

Start at [Yian’s FS-35–FS-39 delivery index](docs/yian-delivery/README.md) for the current files and owners. The [30 October measured audit](docs/yian-delivery/Real_Data_Quality_Status.md) checks six supplied event tables and five raw weather batches: 2,846 event rows, 2,822 positive cell-days, and complete 56-point weather arrays. Reconstructed weather fails the strict bbox rule for 35 grid centres; forecast.csv and actual run provenance remain pending. No model scores were reproduced by this audit.

[Checker instructions](docs/data-quality.md) · [Source catalogue](docs/data-sources.md) · [Whole-team handoff](docs/yian-delivery/TEAM_HANDOFF.md). PR #7 awaits second-person review and upstream merge. Fixture/CI tests and measured data checks are distinct.
