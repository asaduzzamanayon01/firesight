"""Quality-assurance checks that fail loudly. Run them before every training run."""
from __future__ import annotations

import numpy as np
import pandas as pd


class QAError(AssertionError):
    pass


def check_no_overlap(train_idx, test_idx, name: str = "split") -> None:
    """Train and test must not share any row."""
    shared = np.intersect1d(train_idx, test_idx)
    if len(shared):
        raise QAError(f"{name}: {len(shared)} rows appear in both train and test")


def check_no_temporal_leakage(features: pd.DataFrame, issue_col: str = "issue_time",
                              obs_col: str = "feature_obs_time") -> None:
    """Every predictor value must be observed BEFORE the forecast is issued."""
    bad = features[pd.to_datetime(features[obs_col]) >= pd.to_datetime(features[issue_col])]
    if len(bad):
        raise QAError(f"temporal leakage: {len(bad)} feature rows observed at/after issue time")


def check_cell_days(labels: pd.DataFrame, grid: pd.DataFrame) -> None:
    """Cell-day table must be unique, use valid cells and have binary labels."""
    if labels.duplicated(["cell_id", "date"]).any():
        raise QAError("duplicate cell-day rows")
    if not labels["cell_id"].isin(grid["cell_id"]).all():
        raise QAError("cell_id not in grid")
    if not labels["ignition"].isin([0, 1]).all():
        raise QAError("ignition label must be 0/1")


def class_balance(labels: pd.DataFrame, idx) -> dict:
    """Positives and positive rate in a fold — report it, rare events vary a lot."""
    y = labels["ignition"].values[idx]
    return {"n": int(len(y)), "positives": int(y.sum()), "rate": float(y.mean()) if len(y) else 0.0}
