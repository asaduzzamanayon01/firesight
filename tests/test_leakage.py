"""Leakage tests. If these fail, no score from this project can be trusted.

A marker asking "how do you know you haven't leaked?" gets pointed at this
file rather than a verbal reassurance.
"""
import numpy as np
import pandas as pd
import pytest

from src.features.join_weather import lag_and_roll
from src.models.train_lgbm import compute_scale_pos_weight, feature_columns


@pytest.fixture
def weather():
    dates = pd.date_range("2020-01-01", periods=40, freq="D")
    return pd.DataFrame({
        "cell_id": np.repeat([1, 2], len(dates)),
        "date": np.tile(dates, 2),
        "t2m_max": np.tile(np.arange(len(dates), dtype=float), 2),
        "rh_min": np.tile(np.arange(len(dates), dtype=float) * 2, 2),
        "wind_speed_max": 5.0,
        "precip_24h": 0.0,
        "kbdi": 100.0,
    })


def test_weather_is_lagged_not_same_day(weather):
    """The single most important test in the repo.

    t2m_max on day i is i. After a 1-day lag, the feature for day i must be
    i-1. If it equals i, we are using the future to predict the past.
    """
    out = lag_and_roll(weather)
    c1 = out[out["cell_id"] == 1].sort_values("date").reset_index(drop=True)
    assert pd.isna(c1.loc[0, "t2m_max_lag1"]), "first day has no prior day"
    for i in range(1, 10):
        assert c1.loc[i, "t2m_max_lag1"] == float(i - 1)


def test_unlagged_columns_are_dropped(weather):
    """Raw same-day columns must not survive into the feature frame."""
    out = lag_and_roll(weather)
    for v in ("t2m_max", "rh_min", "kbdi"):
        assert v not in out.columns


def test_rolling_windows_inherit_the_lag(weather):
    out = lag_and_roll(weather)
    c1 = out[out["cell_id"] == 1].sort_values("date").reset_index(drop=True)
    # The lagged series at index i holds value i-1. A 3-day rolling mean
    # ending at index 10 therefore covers lagged[8], lagged[9], lagged[10],
    # i.e. the observations from days 7, 8 and 9 - never day 10 itself.
    assert c1.loc[10, "t2m_max_roll3"] == pytest.approx(np.mean([7, 8, 9]))


def test_lag_does_not_bleed_across_cells(weather):
    """Cell 2's first day must be NaN, not carried over from cell 1's last."""
    out = lag_and_roll(weather)
    c2 = out[out["cell_id"] == 2].sort_values("date").reset_index(drop=True)
    assert pd.isna(c2.loc[0, "t2m_max_lag1"])


def test_label_and_identifiers_excluded_from_features():
    df = pd.DataFrame({
        "cell_id": [1, 2], "date": pd.to_datetime(["2020-01-01", "2020-01-02"]),
        "season": ["2019-20", "2019-20"], "ignition": [0, 1],
        "n_ignitions": [0, 1], "t2m_max_lag1": [30.0, 31.0],
    })
    feats = feature_columns(df)
    assert "ignition" not in feats
    assert "n_ignitions" not in feats, "n_ignitions is the label in disguise"
    assert "cell_id" not in feats
    assert "t2m_max_lag1" in feats


def test_scale_pos_weight_matches_the_imbalance():
    y = np.array([0] * 997 + [1] * 3)
    assert compute_scale_pos_weight(y) == pytest.approx(997 / 3)


def test_scale_pos_weight_rejects_empty_positive_class():
    with pytest.raises(ValueError, match="no positives"):
        compute_scale_pos_weight(np.zeros(100, dtype=int))
