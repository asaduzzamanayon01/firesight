"""FS-23: ConvLSTM prototype. STRETCH GOAL, Sprint 4.

Owner: Ayon
Jira: FS-23 (ConvLSTM prototype)
Status: SCAFFOLD ONLY. Do not start until FS-18..FS-21 are Done.

WHY THIS IS A STRETCH GOAL AND NOT A COMMITMENT
-----------------------------------------------
1. It needs a different data shape. The tabular pipeline produces one row per
   cell-day; ConvLSTM needs a (time, height, width, channels) raster stack.
   That is FS-22, a full story on its own.
2. Training is 2-3 hours per run versus 3-5 minutes, so we get perhaps 5
   experiments instead of 50.
3. More hyperparameters on ~15,000 positives across the whole dataset is a
   real overfitting risk.

WHAT IT WOULD BUY US
--------------------
Gradient boosting sees each cell-day independently. Any spatial structure has
to be hand-engineered into features. A ConvLSTM learns spatial neighbourhood
and temporal sequence directly, so a dry corridor propagating across cells is
something it can represent and the tabular model cannot.

Worth testing. Not worth betting the unit on. If the comparison in FS-20 shows
LightGBM already near the ceiling, we report that and stop.
"""
from __future__ import annotations

import logging

import numpy as np

from src.features.grid import grid_dimensions

log = logging.getLogger(__name__)


def build_raster_stack(df, feature_cols: list[str]) -> tuple[np.ndarray, np.ndarray]:
    """FS-22: reshape the flat cell-day table into (T, H, W, C) rasters.

    Returns
    -------
    X : (n_days, n_rows, n_cols, n_features)
    y : (n_days, n_rows, n_cols)
    """
    n_cols, n_rows, _, _ = grid_dimensions()
    dates = np.sort(df["date"].unique())
    date_idx = {d: i for i, d in enumerate(dates)}

    X = np.full((len(dates), n_rows, n_cols, len(feature_cols)), np.nan, dtype=np.float32)
    y = np.zeros((len(dates), n_rows, n_cols), dtype=np.float32)

    t = df["date"].map(date_idx).to_numpy()
    r, c = np.divmod(df["cell_id"].to_numpy(), n_cols)
    X[t, r, c, :] = df[feature_cols].to_numpy(dtype=np.float32)
    y[t, r, c] = df["ignition"].to_numpy(dtype=np.float32)

    log.info("raster stack %s, labels %s", X.shape, y.shape)
    return X, y


def make_sequences(X: np.ndarray, y: np.ndarray, lookback: int = 7):
    """Slide a lookback window: predict day t from days t-lookback..t-1."""
    xs = np.stack([X[i - lookback:i] for i in range(lookback, len(X))])
    ys = y[lookback:]
    return xs, ys


def build_model(input_shape, filters: int = 32):
    """Small ConvLSTM. Deliberately small: ~15k positives cannot support more.

    Requires tensorflow, which is NOT in requirements.txt by design - we do
    not install a 500MB dependency until FS-20 justifies it.
    """
    try:
        from tensorflow import keras
        from tensorflow.keras import layers
    except ImportError as exc:
        raise ImportError(
            "tensorflow not installed. This is intentional: only install it "
            "in Sprint 4 if FS-20 shows the tabular models have plateaued.\n"
            "  pip install tensorflow"
        ) from exc

    model = keras.Sequential([
        layers.Input(shape=input_shape),
        layers.ConvLSTM2D(filters, (3, 3), padding="same", return_sequences=True),
        layers.BatchNormalization(),
        layers.ConvLSTM2D(filters // 2, (3, 3), padding="same", return_sequences=False),
        layers.BatchNormalization(),
        layers.Conv2D(1, (1, 1), activation="sigmoid"),
    ])
    model.compile(
        optimizer=keras.optimizers.Adam(1e-3),
        # Same imbalance problem, same solution: reweight the positive class.
        loss=keras.losses.BinaryFocalCrossentropy(alpha=0.95, gamma=2.0),
        metrics=[keras.metrics.AUC(curve="PR", name="pr_auc")],
    )
    return model


if __name__ == "__main__":
    raise SystemExit(
        "ConvLSTM is a Sprint 4 stretch goal. Complete FS-18 through FS-21 "
        "and run FS-20 model comparison first."
    )
