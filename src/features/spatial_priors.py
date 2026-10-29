"""Spatial and recent-activity features that tell the model WHERE fires start.

Owner: Ayon
Jira: FS-23 (real-data model run)

WHY THIS FILE EXISTS
--------------------
On real data the climatology baseline (PR-AUC 0.0064) beat LightGBM trained on
weather and season only (PR-AUC 0.0021). The baseline knows which cells burn;
the weather lattice is about 20 km wide, so neighbouring 3 km cells get almost
the same weather and the model cannot tell them apart. These features give the
model the same "where" information, without leaking any held-out label.

THREE GROUPS OF FEATURES
------------------------
1. cell_lat, cell_lon      Static. Cell centre. No labels used.
2. recent_*                Ignitions in the last 1 / 7 days nearby and in the
                           whole region. Uses ONLY earlier days of the same
                           season (shifted by one day, never day D itself), so
                           it is information a forecaster would have had.
3. cell_rate, nbr_rate_*   Historical ignition rate of the cell and of its
                           neighbourhood. Computed from TRAINING seasons only.
                           A training row in season s gets a rate computed from
                           the other training seasons, so a row's own label
                           never feeds its own feature. A test row gets a rate
                           from all training seasons and never from its own
                           season.

Tests: tests/test_spatial_priors.py proves all three rules.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

RADII_KM = (7.0, 16.0)          # neighbourhood sizes for the historical rate
RECENT_RADIUS_KM = 16.0         # neighbourhood for recent activity
PRIOR_DAYS = 1000.0             # pseudo-days pulling a rate toward the global rate

STATIC_COLS = ["cell_lat", "cell_lon"]
RECENT_COLS = ["recent_nbr_1d", "recent_nbr_7d", "recent_all_7d"]
PRIOR_COLS = ["cell_rate"] + [f"nbr_rate_{int(r)}km" for r in RADII_KM]


def _centroids(df: pd.DataFrame, centroids: pd.DataFrame | None):
    """Cell ids present in df and their centre coordinates, in sorted id order."""
    if centroids is None:
        from src.features.grid import cell_centroids
        centroids = cell_centroids()
    ids = np.sort(df["cell_id"].unique())
    c = centroids.set_index("cell_id").reindex(ids)
    if c[["centroid_lat", "centroid_lon"]].isna().any().any():
        raise ValueError("some cell_id values have no centroid")
    return ids, c["centroid_lat"].to_numpy(), c["centroid_lon"].to_numpy()


def _within(lat: np.ndarray, lon: np.ndarray, radius_km: float) -> np.ndarray:
    """Matrix W[i, j] = 1 if cell j is within radius_km of cell i (self included)."""
    kx = 111.32 * np.cos(np.radians(float(lat.mean())))
    x, y = lon * kx, lat * 110.57
    d2 = (x[:, None] - x[None, :]) ** 2 + (y[:, None] - y[None, :]) ** 2
    return (d2 <= radius_km ** 2).astype(np.float32)


def add_static_and_recent(df: pd.DataFrame, centroids: pd.DataFrame | None = None
                          ) -> pd.DataFrame:
    """Add cell_lat, cell_lon and the recent_* columns. Safe to run on all data."""
    ids, lat, lon = _centroids(df, centroids)
    ci = np.searchsorted(ids, df["cell_id"].to_numpy())
    out = df.copy()
    out["cell_lat"] = lat[ci].astype(np.float32)
    out["cell_lon"] = lon[ci].astype(np.float32)

    dates = np.sort(df["date"].unique())
    di = np.searchsorted(dates, df["date"].to_numpy())
    season_of_date = (
        df.groupby("date")["season"].first().reindex(dates).to_numpy()
    )

    ign = np.zeros((len(dates), len(ids)), dtype=np.float32)
    ign[di, ci] = df["ignition"].to_numpy(dtype=np.float32)

    nbr = ign @ _within(lat, lon, RECENT_RADIUS_KM)      # ignitions near each cell, per day
    region = ign.sum(axis=1)                             # ignitions anywhere, per day

    nbr1 = np.zeros_like(nbr)
    nbr7 = np.zeros_like(nbr)
    reg7 = np.zeros_like(region)
    for s in pd.unique(season_of_date):
        idx = np.where(season_of_date == s)[0]
        a, b = idx[0], idx[-1] + 1
        block, rblock = nbr[a:b], region[a:b]
        n = b - a
        # exclusive running sums: cs[i] = sum of block[:i], so day i sees only days before it
        cs = np.vstack([np.zeros((1, block.shape[1]), np.float32), np.cumsum(block, axis=0)])
        rcs = np.concatenate([[0.0], np.cumsum(rblock)]).astype(np.float32)
        i = np.arange(n)
        lo = np.maximum(i - 7, 0)
        nbr7[a:b] = cs[i] - cs[lo]
        reg7[a:b] = rcs[i] - rcs[lo]
        nbr1[a + 1:b] = block[:-1]                       # yesterday only; day 0 stays 0

    out["recent_nbr_1d"] = nbr1[di, ci]
    out["recent_nbr_7d"] = nbr7[di, ci]
    out["recent_all_7d"] = reg7[di]
    return out


def fold_priors(df: pd.DataFrame, train_idx: np.ndarray, test_idx: np.ndarray,
                centroids: pd.DataFrame | None = None
                ) -> tuple[np.ndarray, np.ndarray]:
    """Historical-rate features for one cross-validation fold.

    Returns (train_values, test_values), arrays shaped (len(idx), len(PRIOR_COLS)).
    Pass an empty test_idx to get priors for every row (final model).
    """
    ids, lat, lon = _centroids(df, centroids)
    ci = np.searchsorted(ids, df["cell_id"].to_numpy())
    seasons = np.sort(df["season"].unique())
    si = np.searchsorted(seasons, df["season"].to_numpy())

    pos = np.zeros((len(ids), len(seasons)))
    days = np.zeros((len(ids), len(seasons)))
    np.add.at(pos, (ci, si), df["ignition"].to_numpy(dtype=float))
    np.add.at(days, (ci, si), 1.0)

    train_idx = np.asarray(train_idx)
    test_idx = np.asarray(test_idx)
    train_seasons = np.unique(si[train_idx])
    weights = [None] + [_within(lat, lon, r).astype(np.float64) for r in RADII_KM]

    def rates(use: np.ndarray) -> np.ndarray:
        """Matrix (n_cells, len(PRIOR_COLS)) of smoothed rates from the given seasons."""
        p, d = pos[:, use].sum(axis=1), days[:, use].sum(axis=1)
        g = p.sum() / max(d.sum(), 1.0)
        cols = []
        for w in weights:
            pp = p if w is None else w @ p
            dd = d if w is None else w @ d
            cols.append((pp + PRIOR_DAYS * g) / (dd + PRIOR_DAYS))
        return np.column_stack(cols)

    train_out = np.full((len(train_idx), len(PRIOR_COLS)), np.nan, dtype=np.float32)
    for s in train_seasons:
        rows = np.where(si[train_idx] == s)[0]
        others = train_seasons[train_seasons != s]
        if len(others) == 0:
            continue
        train_out[rows] = rates(others)[ci[train_idx][rows]]

    test_out = np.full((len(test_idx), len(PRIOR_COLS)), np.nan, dtype=np.float32)
    if len(test_idx):
        test_out[:] = rates(train_seasons)[ci[test_idx]]
    return train_out, test_out
