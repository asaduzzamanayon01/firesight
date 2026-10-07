# firesight-geo

Geospatial and evaluation module for FireSight (COMP6002, Group 14): 3 km grid, FIRMS ignition labels, validation splits and QA checks.

```
src/firesight_geo/
  projection.py   WGS84 <-> GDA2020 / MGA zone 50 (EPSG:7850)
  grid.py         3 km grid, point-to-cell assignment
  labels.py       FIRMS loading, event clustering, earliest-detection ignitions, cell-day labels
  splits.py       fire seasons, leave-one-season-out, spatial hold-out block with buffer
  qa.py           overlap, temporal leakage, cell-day and class-balance checks
tests/test_geo.py automated tests
docs/validation_protocol.md
```

## Setup
```
pip install -r requirements.txt
pytest -q
```

## Usage
```python
from firesight_geo.grid import build_grid, save_grid
from firesight_geo.labels import load_firms, ignition_events, cell_day_labels

grid = build_grid()
save_grid(grid, "data/processed/grid_3km.gpkg")
events = ignition_events(load_firms("data/raw/firms/viirs.csv"), grid)
labels = cell_day_labels(events, grid, "2019-07-01", "2025-06-30")
```
