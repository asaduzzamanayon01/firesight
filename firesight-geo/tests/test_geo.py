"""Tests for grid, labels, splits and QA. Run with:  pytest -q"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from firesight_geo.grid import build_grid, assign_cells
from firesight_geo.labels import cluster_events, ignition_events, cell_day_labels
from firesight_geo.splits import fire_season, loso_splits, spatial_block_split
from firesight_geo import qa


def _det(lon, lat, when):
    return {"longitude": lon, "latitude": lat, "acq_datetime": pd.Timestamp(when, tz="UTC")}


# ---------- grid ----------
def test_grid_cells_are_3km_and_ids_unique():
    g = build_grid()
    assert len(g) > 0
    assert np.allclose(g["maxx"] - g["minx"], 3000)
    assert np.allclose(g["maxy"] - g["miny"], 3000)
    assert g["cell_id"].is_unique


def test_grid_covers_perth_cbd_and_rejects_outside_points():
    g = build_grid()
    ids = assign_cells([115.86, 0.0], [-31.95, 0.0], g)  # Perth CBD, then far away
    assert ids[0] >= 0 and ids[1] == -1


def test_point_falls_in_its_own_cell_centroid():
    g = build_grid()
    r = g.sample(5, random_state=0)
    assert (assign_cells(r["centroid_lon"], r["centroid_lat"], g) == r["cell_id"].values).all()


# ---------- labels ----------
def test_one_fire_over_several_days_is_one_event_with_earliest_kept():
    df = pd.DataFrame([
        _det(116.05, -32.05, "2025-01-10 05:00"),
        _det(116.06, -32.05, "2025-01-11 05:00"),   # ~1 km away, next day -> same fire
        _det(116.07, -32.05, "2025-01-12 05:00"),   # spreading further
        _det(115.80, -32.40, "2025-01-11 06:00"),   # far away -> separate fire
    ])
    g = build_grid()
    ev = ignition_events(df, g)
    assert len(ev) == 2
    spreading = ev.loc[ev["n_detections"] == 3].iloc[0]
    assert spreading["acq_datetime"] == pd.Timestamp("2025-01-10 05:00", tz="UTC")


def test_same_place_weeks_apart_is_two_events():
    df = pd.DataFrame([_det(116.05, -32.05, "2025-01-01 05:00"),
                       _det(116.05, -32.05, "2025-02-01 05:00")])
    assert cluster_events(df)["event_id"].nunique() == 2


def test_cell_day_labels_have_exactly_the_event_positives():
    g = build_grid()
    df = pd.DataFrame([_det(116.05, -32.05, "2025-01-10 05:00")])
    lab = cell_day_labels(ignition_events(df, g), g, "2025-01-09", "2025-01-11")
    assert len(lab) == len(g) * 3
    assert lab["ignition"].sum() == 1
    qa.check_cell_days(lab, g)


# ---------- splits ----------
def test_fire_season_spans_new_year():
    s = fire_season(["2024-12-15", "2025-02-01", "2025-08-01"])
    assert list(s) == ["2024-25", "2024-25", "2025-26"]


def test_loso_never_mixes_seasons():
    dates = pd.date_range("2023-11-01", "2025-03-31", freq="7D")
    df = pd.DataFrame({"date": dates, "cell_id": 0})
    seasons = fire_season(df["date"]).values
    for s, tr, te in loso_splits(df):
        qa.check_no_overlap(tr, te)
        assert set(seasons[te]) == {s} and s not in set(seasons[tr])


def test_spatial_block_has_buffer_and_no_overlap():
    g = build_grid()
    df = pd.DataFrame({"cell_id": g["cell_id"]})
    tr, te, buf = spatial_block_split(df, g, block_rows=(5, 10), block_cols=(5, 10))
    qa.check_no_overlap(tr, te)
    assert len(te) == 25 and len(buf) > 0
    assert not set(df["cell_id"].values[tr]) & buf


# ---------- QA ----------
def test_leakage_check_catches_future_feature():
    f = pd.DataFrame({"issue_time": ["2025-01-10 00:00"], "feature_obs_time": ["2025-01-10 06:00"]})
    try:
        qa.check_no_temporal_leakage(f)
    except qa.QAError:
        return
    raise AssertionError("leakage not detected")
