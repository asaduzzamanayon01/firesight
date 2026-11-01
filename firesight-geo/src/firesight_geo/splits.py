"""Validation splits: leave-one-season-out (LOSO) and a spatial hold-out block.

Random train/test splits leak information because neighbouring cells and
nearby days share weather, terrain and land use. These splits keep test data
separated in time (a whole fire season) and in space (a held-out block of
cells, with a buffer ring removed from training).
"""
from __future__ import annotations

from collections.abc import Iterator

import numpy as np
import pandas as pd

SEASON_START_MONTH = 7  # fire year runs July -> June, so one summer is one season


def fire_season(dates) -> pd.Series:
    """Season label, e.g. Dec 2024 and Feb 2025 are both season '2024-25'."""
    d = pd.to_datetime(pd.Series(dates))
    start_year = np.where(d.dt.month >= SEASON_START_MONTH, d.dt.year, d.dt.year - 1)
    return pd.Series([f"{y}-{str(y + 1)[-2:]}" for y in start_year], index=d.index)


def loso_splits(df: pd.DataFrame) -> Iterator[tuple[str, np.ndarray, np.ndarray]]:
    """Yield (season, train_idx, test_idx), holding out one full season each time."""
    seasons = fire_season(df["date"]).values
    for s in sorted(set(seasons)):
        test = np.where(seasons == s)[0]
        train = np.where(seasons != s)[0]
        yield s, train, test


def spatial_block_split(df: pd.DataFrame, grid: pd.DataFrame, block_rows: tuple[int, int],
                        block_cols: tuple[int, int], buffer_cells: int = 1):
    """Hold out a rectangular block of cells (row/col ranges, end exclusive).

    Cells within `buffer_cells` of the block are dropped from BOTH sets so the
    model can't learn the test area from its immediate neighbours.
    Returns (train_idx, test_idx, buffer_cell_ids).
    """
    r0, r1 = block_rows
    c0, c1 = block_cols
    in_block = grid["row"].between(r0, r1 - 1) & grid["col"].between(c0, c1 - 1)
    in_buffer = (grid["row"].between(r0 - buffer_cells, r1 - 1 + buffer_cells)
                 & grid["col"].between(c0 - buffer_cells, c1 - 1 + buffer_cells) & ~in_block)
    test_cells = set(grid.loc[in_block, "cell_id"])
    buffer_cells_ids = set(grid.loc[in_buffer, "cell_id"])
    cell = df["cell_id"].values
    test = np.where(np.isin(cell, list(test_cells)))[0]
    train = np.where(~np.isin(cell, list(test_cells | buffer_cells_ids)))[0]
    return train, test, buffer_cells_ids
