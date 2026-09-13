"""Grid construction. INTERFACE OWNED BY SAAD (FS-2) - Ayon depends on it.

This module defines the contract Ayon's cell-day builder relies on. Saad's
real implementation replaces the body; the function signature and the returned
column names must not change without telling Ayon, because build_cell_days.py
joins on `cell_id`.

Contract:
    make_grid() -> GeoDataFrame with columns [cell_id, geometry]
    assign_cells(points_df) -> adds a `cell_id` column
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.config import CFG


def grid_dimensions() -> tuple[int, int, float, float]:
    """Return (n_cols, n_rows, dlon, dlat) for the configured bbox and cell size."""
    w, s, e, n = CFG.region.bbox
    km = CFG.region.grid_cell_km
    lat0 = (s + n) / 2.0
    dlat = km / 110.57
    dlon = km / (111.32 * np.cos(np.radians(lat0)))
    n_cols = int(np.ceil((e - w) / dlon))
    n_rows = int(np.ceil((n - s) / dlat))
    return n_cols, n_rows, dlon, dlat


def n_cells() -> int:
    c, r, _, _ = grid_dimensions()
    return c * r


def assign_cells(df: pd.DataFrame, lon_col: str = "longitude",
                 lat_col: str = "latitude") -> pd.DataFrame:
    """Attach a `cell_id` to each point by integer binning on the bbox.

    cell_id = row * n_cols + col, so it is stable across runs.
    Points outside the bbox get cell_id = -1 and should be dropped.
    """
    w, s, e, n = CFG.region.bbox
    n_cols, n_rows, dlon, dlat = grid_dimensions()

    col = np.floor((df[lon_col].to_numpy() - w) / dlon).astype(int)
    row = np.floor((df[lat_col].to_numpy() - s) / dlat).astype(int)

    inside = (col >= 0) & (col < n_cols) & (row >= 0) & (row < n_rows)
    cell_id = np.where(inside, row * n_cols + col, -1)
    return df.assign(cell_id=cell_id)


def cell_centroids() -> pd.DataFrame:
    """One row per cell with its centre lon/lat. Used for spatial features."""
    w, s, _, _ = CFG.region.bbox
    n_cols, n_rows, dlon, dlat = grid_dimensions()
    ids = np.arange(n_cols * n_rows)
    rows, cols = np.divmod(ids, n_cols)
    return pd.DataFrame({
        "cell_id": ids,
        "centroid_lon": w + (cols + 0.5) * dlon,
        "centroid_lat": s + (rows + 0.5) * dlat,
    })
