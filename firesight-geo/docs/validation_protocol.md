# FireSight — Grid, Label and Validation Protocol

Owner: S M Nuayman Sa-ad (Geospatial & Evaluation Lead) · Status: draft for team review

## 1. Analysis grid
- Study area: Perth metropolitan area and Darling Scarp, lon 115.65–116.30, lat −32.60 to −31.60 (configurable in `grid.py`).
- Projection: GDA2020 / MGA zone 50 (EPSG:7850), so every cell is a true 3 km × 3 km square.
- Origin snapped to a multiple of 3 km → the grid is identical on every run.
- Each cell has a stable `cell_id`, `row`, `col`, bounds and centroid.
- Unit of analysis: **cell-day** (one cell on one local Perth date).

## 2. Ignition labels (FIRMS VIIRS 375 m)
1. Load detections, parse UTC acquisition time, drop low-confidence detections.
2. Link detections within **2 km** and **2 days** of each other into one fire event.
3. Keep the **earliest** detection per event as the ignition; later detections are spread, not new ignitions.
4. Assign it to a cell and a local (Australia/Perth) date → `ignition = 1`; all other cell-days are 0.

Known limits: a satellite detection is not the exact ignition point or time; small/short fires and cloud-covered periods can be missed; prescribed burns must be filtered against DBCA burn records (with Yian).

## 3. Validation design
- **Leave-one-season-out (LOSO):** fire season = July–June, so one summer stays together. Each season is held out once.
- **Spatial hold-out block:** a rectangular block of cells is the test area; a **1-cell buffer ring** around it is removed from training so neighbouring cells can't leak information.
- No random train/test splits.

## 4. Metrics
- **PR-AUC** — discrimination for the rare positive class (accuracy is not used as a primary metric).
- **Brier score** — accuracy of the predicted probabilities.
- **Reliability curves** — do predicted probabilities match observed frequencies?
- All reported against the **seasonal climatology baseline**, per season and per spatial block.

## 5. QA checks (`qa.py`, run before every training run)
| Check | Fails when |
|---|---|
| `check_no_overlap` | a row is in both train and test |
| `check_no_temporal_leakage` | a feature was observed at/after the forecast issue time |
| `check_cell_days` | duplicate cell-days, unknown cell_id, or non-binary label |
| `class_balance` | (report) positives and rate per fold |

## 6. Testing evidence
`tests/test_geo.py` — 10 automated tests covering grid size and ids, point-to-cell assignment, event clustering, earliest-detection selection, cell-day labels, season boundaries, LOSO separation, spatial buffer, and leakage detection.

## 7. Next steps
- Run on the real FIRMS archive and report events per season.
- Agree the spatial hold-out block with the team.
- Tune the 2 km / 2 day clustering thresholds with a sensitivity check.
