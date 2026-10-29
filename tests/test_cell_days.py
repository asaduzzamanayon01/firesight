"""Tests for the cell-day spine and season logic."""
import numpy as np
import pandas as pd

from src.config import CFG
from src.features.build_cell_days import add_temporal_features, build, season_of
from src.features.grid import assign_cells, grid_dimensions, n_cells

# A day inside the configured window (the season start month of start_year + 1 day 15).
IN_RANGE = f"{CFG.seasons.start_year + 1}-01-15"


def test_season_spans_the_new_year():
    """Nov 2019 and Feb 2020 are the SAME fire season."""
    d = pd.Series(pd.to_datetime(["2019-11-03", "2020-02-14", "2020-08-01"]))
    s = season_of(d)
    assert s.iloc[0] == s.iloc[1] == "2019-20"
    assert s.iloc[2] == "2020-21"


def test_grid_covers_the_bbox():
    n_cols, n_rows, dlon, dlat = grid_dimensions()
    assert n_cols > 0 and n_rows > 0
    assert n_cells() == n_cols * n_rows


def test_points_outside_bbox_get_minus_one():
    df = pd.DataFrame({"longitude": [116.0, 0.0], "latitude": [-32.0, 0.0]})
    out = assign_cells(df)
    assert out["cell_id"].iloc[0] >= 0
    assert out["cell_id"].iloc[1] == -1


def test_build_produces_one_row_per_cell_day():
    ign = pd.DataFrame({
        "latitude": [-32.0], "longitude": [116.0],
        "date": pd.to_datetime([IN_RANGE]),
    })
    out = build(ign)
    assert not out.duplicated(["cell_id", "date"]).any()
    assert out["ignition"].isin([0, 1]).all()


def test_ignition_flag_is_binary_even_with_two_fires_in_one_cell_day():
    ign = pd.DataFrame({
        "latitude": [-32.0, -32.0], "longitude": [116.0, 116.0],
        "date": pd.to_datetime([IN_RANGE, IN_RANGE]),
    })
    out = build(ign)
    hit = out[out["ignition"] == 1]
    assert len(hit) == 1
    assert hit["n_ignitions"].iloc[0] == 2
    assert hit["ignition"].iloc[0] == 1


def test_day_of_year_encoding_is_cyclical():
    """31 Dec and 1 Jan must be close in feature space."""
    df = pd.DataFrame({"date": pd.to_datetime(["2020-12-31", "2021-01-01"])})
    out = add_temporal_features(df)
    dist = np.hypot(out["doy_sin"].iloc[0] - out["doy_sin"].iloc[1],
                    out["doy_cos"].iloc[0] - out["doy_cos"].iloc[1])
    assert dist < 0.1
