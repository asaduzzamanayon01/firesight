"""Ignition labels from NASA FIRMS active-fire detections.

One fire is often detected many times across several days and cells. If every
detection were a positive, the model would learn where fires are *visible*,
not where they *start*. So we:

1. Link detections that are close in space (<= `max_dist_m`) AND time
   (<= `max_gap_days`) into the same fire event (connected components).
2. Keep only the earliest detection of each event as the ignition.
3. Assign that ignition to a 3 km cell and a date -> positive cell-day.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
from scipy.spatial import cKDTree

from .grid import assign_cells
from .projection import to_projected

MAX_DIST_M = 2000.0
MAX_GAP_DAYS = 2


def load_firms(path: str, min_confidence: str | None = "n") -> pd.DataFrame:
    """Read a FIRMS VIIRS CSV, parse acquisition time (UTC) and drop low confidence."""
    df = pd.read_csv(path)
    hhmm = df["acq_time"].astype(int).astype(str).str.zfill(4)
    df["acq_datetime"] = pd.to_datetime(df["acq_date"] + " " + hhmm, format="%Y-%m-%d %H%M", utc=True)
    if min_confidence and "confidence" in df:
        keep = {"n": {"n", "h", "nominal", "high"}, "h": {"h", "high"}}[min_confidence]
        df = df[df["confidence"].astype(str).str.lower().isin(keep)]
    return df.reset_index(drop=True)


def cluster_events(df: pd.DataFrame, max_dist_m: float = MAX_DIST_M,
                   max_gap_days: float = MAX_GAP_DAYS) -> pd.DataFrame:
    """Add an `event_id` column grouping detections into fire events."""
    df = df.copy()
    if df.empty:
        df["event_id"] = pd.Series(dtype=int)
        return df
    x, y = to_projected(df["longitude"].values, df["latitude"].values)
    t_days = (df["acq_datetime"] - df["acq_datetime"].min()).dt.total_seconds().values / 86400
    tree = cKDTree(np.column_stack([x, y]))
    pairs = tree.query_pairs(r=max_dist_m, output_type="ndarray")
    if len(pairs):
        close_in_time = np.abs(t_days[pairs[:, 0]] - t_days[pairs[:, 1]]) <= max_gap_days
        pairs = pairs[close_in_time]
    n = len(df)
    adj = coo_matrix((np.ones(len(pairs)), (pairs[:, 0], pairs[:, 1])), shape=(n, n)) if len(pairs) \
        else coo_matrix((n, n))
    _, df["event_id"] = connected_components(adj, directed=False)
    return df


def ignition_events(df: pd.DataFrame, grid: pd.DataFrame, local_tz: str = "Australia/Perth") -> pd.DataFrame:
    """One row per event: its earliest detection, cell and local ignition date."""
    clustered = cluster_events(df)
    first = (clustered.sort_values("acq_datetime")
             .groupby("event_id", as_index=False).first())
    sizes = clustered.groupby("event_id").size().rename("n_detections")
    first = first.merge(sizes, on="event_id")
    first["cell_id"] = assign_cells(first["longitude"], first["latitude"], grid)
    first["date"] = first["acq_datetime"].dt.tz_convert(local_tz).dt.date
    return first[first["cell_id"] >= 0].reset_index(drop=True)


def cell_day_labels(events: pd.DataFrame, grid: pd.DataFrame, start, end) -> pd.DataFrame:
    """Full cell x day table with `ignition` = 1 where an event started, else 0."""
    dates = pd.date_range(start, end, freq="D").date
    idx = pd.MultiIndex.from_product([grid["cell_id"].values, dates], names=["cell_id", "date"])
    labels = pd.DataFrame(index=idx).reset_index()
    pos = events[["cell_id", "date"]].drop_duplicates().assign(ignition=1)
    labels = labels.merge(pos, on=["cell_id", "date"], how="left")
    labels["ignition"] = labels["ignition"].fillna(0).astype(int)
    return labels
