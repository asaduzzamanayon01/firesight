"""Leakage tests for the where-features. If these fail, the new scores cannot be trusted."""
import numpy as np
import pandas as pd

from src.features.spatial_priors import (
    PRIOR_COLS,
    add_static_and_recent,
    fold_priors,
)

# Three cells far apart (no neighbour overlap), so each behaves independently.
CENT = pd.DataFrame({
    "cell_id": [0, 1, 2],
    "centroid_lat": [-32.0, -31.0, -30.0],
    "centroid_lon": [115.0, 116.0, 117.0],
})


def make_df(pos_by_season: dict[str, list[tuple[int, int]]], n_days: int = 10) -> pd.DataFrame:
    """pos_by_season: season -> list of (cell_id, day_index) that are ignitions."""
    rows = []
    for k, season in enumerate(sorted(pos_by_season)):
        start = pd.Timestamp(2020 + k, 7, 1)
        for d in range(n_days):
            for c in (0, 1, 2):
                rows.append({
                    "cell_id": c, "date": start + pd.Timedelta(days=d), "season": season,
                    "ignition": int((c, d) in pos_by_season[season]),
                })
    return pd.DataFrame(rows)


def test_test_rows_never_see_their_own_season():
    # Cell 0 ignites only in the held-out season 3. Training seasons have no fires.
    df = make_df({"s1": [], "s2": [], "s3": [(0, 2), (0, 3), (0, 4)]})
    te = np.where(df["season"] == "s3")[0]
    tr = np.where(df["season"] != "s3")[0]
    _, te_vals = fold_priors(df, tr, te, CENT)
    assert np.allclose(te_vals, 0.0), "test rows must use training seasons only"


def test_train_rows_never_see_their_own_season():
    # Cell 0 ignites only in training season s1. Rows of s1 must not see that fire.
    df = make_df({"s1": [(0, 1), (0, 2)], "s2": [], "s3": []})
    tr = np.where(df["season"] != "s3")[0]
    te = np.where(df["season"] == "s3")[0]
    tr_vals, te_vals = fold_priors(df, tr, te, CENT)
    seasons_tr = df.iloc[tr]["season"].to_numpy()
    cells_tr = df.iloc[tr]["cell_id"].to_numpy()
    own = tr_vals[(seasons_tr == "s1") & (cells_tr == 0), 0]
    other = tr_vals[(seasons_tr == "s2") & (cells_tr == 0), 0]
    assert np.allclose(own, 0.0), "a row's own label must not feed its own feature"
    assert (other > 0).all(), "other seasons may use that history"
    assert (te_vals[df.iloc[te]["cell_id"].to_numpy() == 0, 0] > 0).all()


def test_prior_columns_present_and_finite():
    df = make_df({"s1": [(0, 1)], "s2": [(1, 2)], "s3": []})
    tr = np.where(df["season"] != "s3")[0]
    te = np.where(df["season"] == "s3")[0]
    a, b = fold_priors(df, tr, te, CENT)
    assert a.shape == (len(tr), len(PRIOR_COLS)) and b.shape == (len(te), len(PRIOR_COLS))
    assert np.isfinite(a).all() and np.isfinite(b).all()


def test_recent_activity_uses_only_earlier_days():
    df = make_df({"s1": [(0, 3)], "s2": []})
    out = add_static_and_recent(df, CENT).set_index(["season", "cell_id", "date"])
    d3 = pd.Timestamp(2020, 7, 1) + pd.Timedelta(days=3)
    same_day = out.loc[("s1", 0, d3)]
    next_day = out.loc[("s1", 0, d3 + pd.Timedelta(days=1))]
    assert same_day["recent_nbr_1d"] == 0 and same_day["recent_nbr_7d"] == 0
    assert next_day["recent_nbr_1d"] == 1 and next_day["recent_nbr_7d"] == 1
    assert next_day["recent_all_7d"] == 1


def test_recent_activity_does_not_cross_seasons():
    # Fire on the last day of s1 must not show up on the first day of s2.
    df = make_df({"s1": [(0, 9)], "s2": []})
    out = add_static_and_recent(df, CENT)
    first_s2 = out[(out["season"] == "s2") & (out["date"] == pd.Timestamp(2021, 7, 1))]
    assert (first_s2["recent_nbr_1d"] == 0).all()
    assert (first_s2["recent_all_7d"] == 0).all()


def test_recent_window_is_seven_days():
    df = make_df({"s1": [(0, 0)], "s2": []}, n_days=12)
    out = add_static_and_recent(df, CENT)
    c0 = out[(out["season"] == "s1") & (out["cell_id"] == 0)].sort_values("date")
    r = c0["recent_nbr_7d"].to_numpy()
    assert r[0] == 0 and r[1:8].tolist() == [1] * 7 and r[8] == 0


def test_capture_rate_of_perfect_and_flat_predictions():
    from scripts.demo_stats import capture_rates

    n_cells, n_days = 100, 5
    rows = []
    for d in range(n_days):
        for c in range(n_cells):
            rows.append({"cell_id": c, "date": pd.Timestamp(2024, 1, 1 + d), "season": "s",
                         "ignition": int(c == 7), "y_prob": 0.9 if c == 7 else 0.001})
    perfect = pd.DataFrame(rows)
    assert capture_rates(perfect, 0.05)["capture_rate"].iloc[0] == 1.0
    flat = perfect.assign(y_prob=0.001)
    rate = capture_rates(flat, 0.05)["capture_rate"].iloc[0]
    assert rate < 0.5, "a flat prediction must not look good"
