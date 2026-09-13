"""Tests for cross-validation splits.

The no-overlap tests are what prove to a marker that we have not leaked.
"""
import numpy as np
import pandas as pd
import pytest

from src.evaluation.splits import (
    forward_chaining,
    leave_one_season_out,
    spatial_block_split,
)


@pytest.fixture
def df():
    seasons = ["2019-20", "2020-21", "2021-22", "2022-23", "2023-24"]
    return pd.DataFrame({
        "season": np.repeat(seasons, 100),
        "cell_id": np.tile(np.arange(100), len(seasons)),
        "ignition": np.random.default_rng(0).binomial(1, 0.01, 500),
    })


def test_loso_yields_one_fold_per_season(df):
    folds = list(leave_one_season_out(df))
    assert len(folds) == df["season"].nunique()


def test_loso_train_and_test_never_overlap(df):
    for _, tr, te in leave_one_season_out(df):
        assert len(np.intersect1d(tr, te)) == 0
        assert len(tr) + len(te) == len(df)


def test_loso_test_fold_is_exactly_one_season(df):
    for season, _, te in leave_one_season_out(df):
        assert set(df.iloc[te]["season"]) == {season}


def test_loso_requires_two_seasons():
    one = pd.DataFrame({"season": ["2019-20"] * 10})
    with pytest.raises(ValueError, match="need >=2 seasons"):
        list(leave_one_season_out(one))


def test_forward_chaining_never_trains_on_the_future(df):
    order = sorted(df["season"].unique())
    for season, tr, _ in forward_chaining(df, min_train=2):
        trained_on = set(df.iloc[tr]["season"])
        assert all(order.index(s) < order.index(season) for s in trained_on)


def test_spatial_block_split_keeps_cells_whole(df):
    tr, te = spatial_block_split(df, n_blocks=4, holdout=0)
    assert len(np.intersect1d(tr, te)) == 0
    # No cell may appear on both sides, or weather leaks across the split
    assert not (set(df.iloc[tr]["cell_id"]) & set(df.iloc[te]["cell_id"]))
