"""A permanent heat source must be removed before modelling."""
import pandas as pd

from src.features.build_cell_days import drop_static_sources


def make(cell_days: dict[int, int], n_days: int = 100) -> pd.DataFrame:
    rows = []
    dates = pd.date_range("2020-01-01", periods=n_days, freq="D")
    for cell, n_pos in cell_days.items():
        for i, d in enumerate(dates):
            rows.append({"cell_id": cell, "date": d, "ignition": int(i < n_pos)})
    return pd.DataFrame(rows)


def test_cell_with_many_ignition_days_is_removed():
    df = make({1: 50, 2: 3, 3: 0})
    out, removed = drop_static_sources(df, min_days=35)
    assert set(out["cell_id"]) == {2, 3}
    assert removed["cell_id"].tolist() == [1]
    assert removed["ignition_days"].tolist() == [50]


def test_normal_cells_are_kept_and_threshold_is_inclusive():
    df = make({1: 34, 2: 35})
    out, removed = drop_static_sources(df, min_days=35)
    assert set(out["cell_id"]) == {1}
    assert removed["cell_id"].tolist() == [2]
