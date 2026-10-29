# FS-7 Verification: 3 km grid, ignition labels, leakage checks

**Owner:** Saad · **Date:** 2026-10-29 · **Jira:** FS-7
**Run with:** `make test` (tests in `tests/test_grid_and_labels.py` and `tests/test_leakage.py`)

All checks below were run in code, not by eye. No real FIRMS data is in the
repository yet, so the label checks use hand-built detections with a known
answer.

## 1. Grid: passed

| Check | Result |
|---|---|
| Bounding box | 115.45 to 116.55 E, 32.60 to 31.40 S (`config.yaml`) |
| Grid size | 35 columns x 45 rows = **1,575 cells** |
| Cell width (east-west) | 2.98 km at the south edge, 3.00 km in the middle, 3.02 km at the north edge |
| Cell height (north-south) | 3.02 km everywhere |
| Coverage | Grid reaches every bbox edge. It overshoots by about 1.2 km east and 2.3 km north, so no strip is missed |
| Corners | All four bbox corners get a valid cell (SW = 0, NE = 1,574) |
| Stable IDs | Every cell centroid maps back to its own `cell_id` |

Cell size stays within 1% of 3 km across the whole box, so the equirectangular
approximation in `grid.py` is good enough at this scale. Note: the docstring in
`build_cell_days.py` says "~1,650 cells"; the real figure is 1,575.

## 2. Ignition labels: one problem found

What passes:
- Two fires far apart stay two separate events.
- Two fires in the same cell on the same day give one positive cell-day with
  `n_ignitions = 2` (`tests/test_cell_days.py`).
- Out-of-bbox points get `cell_id = -1` and are dropped.

**Problem.** `cluster_eps_hours: 24` is too short. DBSCAN scales 24 hours to
1.5 km, so two detections exactly one day apart are already at the limit. Any
spatial movement on top of that splits the fire. A fire that moves about 1 km
a day is labelled as a **new ignition every day**, which is the "learning
spread, not ignition" problem that decision D1 exists to prevent.

| Test case | 24 h (current) | 36 h | 48 h |
|---|---|---|---|
| Fire drifting ~1 km/day for 3 days | 3 events (wrong) | 1 | 1 |
| Fire staying still for 3 days | 1 | 1 | 1 |
| Fire missed for one overpass (cloud) | 2 events (wrong) | 2 | 1 |

**Recommendation.** Change `cluster_eps_hours` to 48 and re-run the real data
pull. Trade-off: two genuinely separate fires starting within 2 days and 1.5
km of each other would merge. That is rarer than a fire spreading or being
hidden by cloud. This is Ayon's decision (D1), so the config is not changed in
this commit. Two tests are marked `xfail(strict=True)`: they will fail loudly
once the config changes, as a reminder to delete the marker.

## 3. Leakage checks: passed

`tests/test_leakage.py` (8 tests) passes:
- Weather is lagged one day; no same-day weather survives.
- Rolling windows inherit the lag and do not bleed between cells.
- `ignition`, `n_ignitions` and `cell_id` are excluded from features.
- Early stopping uses the latest training season, never the test season.

## Result

Full suite: all tests pass, 2 expected failures (the label finding above).

