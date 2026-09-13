# Ayon's runbook

Everything you personally own, in the order to do it.

## Today (before you push anything)

```bash
cd firesight
pip install -r requirements.txt
make synth && make test        # 28 tests must pass
make pipeline                  # ~2 min, writes reports/figures/
```

If all three succeed, your Sprint 1 and 2 code is demonstrably working and you
can say so honestly.

## What to commit, ticket by ticket

Commit in this order. One commit per ticket, ticket key first so Jira links it.

| Order | Ticket | Files | Commit message |
|---|---|---|---|
| 1 | — | `.gitignore`, `requirements.txt`, `Makefile`, `config/`, `src/config.py` | `FS-25 add project scaffold and configuration` |
| 2 | FS-24 | `.github/workflows/ci.yml` | `FS-24 add CI pipeline running lint and tests` |
| 3 | FS-1 | `src/ingest/firms_client.py`, `.env.example` | `FS-1 add FIRMS client with event clustering` |
| 4 | FS-2 | `src/features/grid.py` | `FS-2 add grid interface (stub for Saad)` |
| 5 | FS-10 | `src/features/build_cell_days.py` | `FS-10 build cell-day base table` |
| 6 | FS-11 | `src/features/join_weather.py` | `FS-11 join lagged weather features` |
| 7 | FS-16 | `src/evaluation/metrics.py`, `src/evaluation/splits.py` | `FS-16 add evaluation harness` |
| 8 | — | `scripts/make_synthetic.py` | `FS-25 add synthetic data generator` |
| 9 | — | `tests/` | `FS-24 add unit and leakage tests` |
| 10 | FS-14 | `notebooks/01_eda_ignitions.ipynb` | `FS-14 add EDA notebook` |
| 11 | FS-15 | `src/models/baseline_climatology.py` | `FS-15 add climatology baseline` |
| 12 | FS-18 | `src/models/train_lgbm.py` | `FS-18 train LightGBM with MLflow tracking` |
| 13 | FS-20 | `src/models/compare_models.py` | `FS-20 add systematic model comparison` |
| 14 | FS-19 | `src/models/calibrate.py` | `FS-19 add isotonic calibration` |
| 15 | FS-21 | `src/explain/shap_explain.py` | `FS-21 add SHAP explanations` |
| 16 | FS-23 | `src/models/convlstm.py` | `FS-23 add ConvLSTM scaffold (Sprint 4)` |
| 17 | — | `README.md`, `docs/` | `FS-25 add README and decision log` |

Because `main` is protected, work on a branch:

```bash
git checkout -b feat/ml-pipeline
# ... commits above ...
git push -u origin feat/ml-pipeline
# open a PR, get one approval, merge
```

## Ticket status after this

Move to **Done** (code written, tested, will be merged):
FS-1, FS-10, FS-11, FS-14, FS-15, FS-16, FS-18, FS-19, FS-21, FS-24

Move to **In Progress**: FS-20 (runs, awaiting real data)

Leave in **Backlog**: FS-22, FS-23 (Sprint 4 stretch)

**Do not mark FS-1 Done until you have actually registered the API key** at
firms.modaps.eosdis.nasa.gov/api. The code is written; the key is not.

## Screenshots to post by Friday

Zarif needs these for Section 5 of the proposal and is blocked without them.

1. Jira board showing Sprint 1 with tickets across columns
2. Jira backlog showing all 8 epics
3. Burndown chart (Reports → Burndown)
4. Gantt / timeline view
5. GitHub Actions showing a green CI run
6. `reports/figures/calibration_before.png` and `calibration_after.png`

## When real data arrives

Nothing in the modelling code changes. Replace the synthetic step only:

```bash
export FIRMS_MAP_KEY=...
python -m src.ingest.firms_client --start 2012-07-01 --days 10   # loop this
python -m src.features.build_cell_days
python -m src.features.join_weather      # needs Yian's weather.parquet
make baseline train calibrate explain
```

That substitutability is the point of the pipeline design, and it is worth
saying out loud if a marker asks why you built on synthetic data.
