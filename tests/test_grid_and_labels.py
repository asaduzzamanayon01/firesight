"""FS-7: verify the 3 km grid and the ignition labels.

Owner: Saad
Jira: FS-7 (Verify 3 km grid, ignition labels and leakage checks)

The leakage checks themselves live in tests/test_leakage.py. This file covers
the two things those tests do not: that the grid really is ~3 km and covers
the study area, and that one fire becomes exactly one ignition label.
"""
import numpy as np
import pandas as pd
import pytest

from src.config import CFG
from src.features.build_cell_days import build
from src.features.grid import assign_cells, cell_centroids, grid_dimensions, n_cells
from src.ingest.firms_client import cluster_to_events


def _haversine_km(lat1, lon1, lat2, lon2):
    r = 6371.0088
    p1, p2 = np.radians(lat1), np.radians(lat2)
    dp, dl = p2 - p1, np.radians(lon2 - lon1)
    a = np.sin(dp / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(dl / 2) ** 2
    return 2 * r * np.arcsin(np.sqrt(a))


# ---------------------------------------------------------------- grid ----

@pytest.mark.parametrize("edge", ["south", "middle", "north"])
def test_cells_are_3km_across_the_whole_bbox(edge):
    """Cell width and height stay within 2% of 3 km from south to north."""
    w, s, _, n = CFG.region.bbox
    _, _, dlon, dlat = grid_dimensions()
    lat = {"south": s, "middle": (s + n) / 2, "north": n}[edge]
    km = CFG.region.grid_cell_km
    assert _haversine_km(lat, w, lat, w + dlon) == pytest.approx(km, rel=0.02)
    assert _haversine_km(lat, w, lat + dlat, w) == pytest.approx(km, rel=0.02)


def test_grid_reaches_every_edge_of_the_bbox():
    """No strip of the study area is left without a cell."""
    w, s, e, n = CFG.region.bbox
    n_cols, n_rows, dlon, dlat = grid_dimensions()
    assert w + n_cols * dlon >= e
    assert s + n_rows * dlat >= n


def test_all_four_bbox_corners_get_a_valid_cell():
    w, s, e, n = CFG.region.bbox
    corners = pd.DataFrame({"longitude": [w, e, w, e], "latitude": [s, s, n, n]})
    ids = assign_cells(corners)["cell_id"]
    assert (ids >= 0).all()
    assert ids.iloc[0] == 0
    assert ids.iloc[3] == n_cells() - 1


def test_cell_ids_are_unique_and_round_trip():
    """Each centroid maps back to its own cell, so cell_id is stable."""
    cc = cell_centroids()
    assert cc["cell_id"].is_unique
    assert len(cc) == n_cells()
    pts = cc.rename(columns={"centroid_lon": "longitude", "centroid_lat": "latitude"})
    assert (assign_cells(pts)["cell_id"].to_numpy() == cc["cell_id"].to_numpy()).all()


# -------------------------------------------------------------- labels ----

def _detections(rows):
    df = pd.DataFrame(rows, columns=["latitude", "longitude", "acq_datetime"])
    df["acq_datetime"] = pd.to_datetime(df["acq_datetime"])
    return df


@pytest.mark.xfail(strict=True, reason=(
    "FS-7 finding: cluster_eps_hours=24 splits a fire that moves ~1 km/day into "
    "a new event each day. Passes with 48. Decision for Ayon (D1) - when the "
    "config changes, delete this marker."))
def test_one_spreading_fire_becomes_one_ignition_at_its_first_detection():
    """A fire burning 3 days and drifting east is ONE event, labelled where it began."""
    det = _detections([
        (-32.000, 116.000, "2020-01-10 02:00"),
        (-32.000, 116.010, "2020-01-10 14:00"),
        (-32.000, 116.020, "2020-01-11 02:00"),
        (-32.000, 116.030, "2020-01-12 02:00"),
    ])
    events = cluster_to_events(det)
    assert len(events) == 1
    assert events["acq_datetime"].iloc[0] == pd.Timestamp("2020-01-10 02:00")
    assert events["longitude"].iloc[0] == pytest.approx(116.000)
    assert events["detections_in_event"].iloc[0] == 4


def test_two_far_apart_fires_stay_separate():
    det = _detections([
        (-32.00, 116.00, "2020-01-10 02:00"),
        (-31.60, 115.70, "2020-01-10 02:00"),
    ])
    assert len(cluster_to_events(det)) == 2


@pytest.mark.xfail(strict=True, reason=(
    "FS-7 finding: cluster_eps_hours=24 splits a fire that moves ~1 km/day into "
    "a new event each day. Passes with 48. Decision for Ayon (D1) - when the "
    "config changes, delete this marker."))
def test_later_days_of_a_fire_are_not_labelled_as_ignitions():
    """Only the start day is a positive. Spread days must stay 0."""
    det = _detections([
        (-32.000, 116.000, "2020-01-10 02:00"),
        (-32.000, 116.010, "2020-01-11 02:00"),
        (-32.000, 116.020, "2020-01-12 02:00"),
    ])
    out = build(cluster_to_events(det))
    pos = out[out["ignition"] == 1]
    assert len(pos) == 1
    assert pos["date"].iloc[0] == pd.Timestamp("2020-01-10")
