"""FS-15: Climatology baseline. THE NUMBER EVERYTHING ELSE IS COMPARED TO.

Owner: Ayon
Jira: FS-15 (Implement climatology baseline)

WHY A BASELINE COMES FIRST
--------------------------
"Our model scored PR-AUC 0.08" is meaningless on its own. It is only a result
once you can say "against a climatology baseline of 0.03". This module is
deliberately built and locked BEFORE any LightGBM work, so the comparison
cannot be tuned after the fact.

WHAT CLIMATOLOGY MEANS HERE
---------------------------
For each (cell, day-of-year) we ask: historically, how often did a fire start
in this cell around this time of year? No weather, no satellite, no learning.
Just the long-run seasonal and spatial average.

It is a genuinely strong baseline. Fire risk in Perth is overwhelmingly
seasonal and some cells simply burn more than others. If gradient boosting
cannot beat this, weather and vegetation are adding nothing, which is itself
a reportable finding.
"""
from __future__ import annotations

import logging
import pickle

import numpy as np
import pandas as pd

from src.config import CFG
from src.evaluation.metrics import evaluate, plot_pr_curve, plot_reliability
from src.evaluation.splits import leave_one_season_out

log = logging.getLogger(__name__)


class ClimatologyBaseline:
    """P(ignition | cell, day-of-year) smoothed over a +/- window of days.

    Parameters
    ----------
    window_days : half-width of the day-of-year smoothing window. 15 means a
        31-day window centred on the target day. Without smoothing, most
        (cell, doy) pairs have zero historical fires and the estimate is 0.
    prior_strength : pseudo-count for Laplace smoothing toward the global
        rate. Stops cells with two historical fires claiming a huge
        probability off a tiny sample.
    """

    def __init__(self, window_days: int = 15, prior_strength: float = 50.0):
        self.window_days = window_days
        self.prior_strength = prior_strength
        self.global_rate_: float | None = None
        self.cell_doy_rate_: pd.Series | None = None

    def fit(self, df: pd.DataFrame) -> ClimatologyBaseline:
        self.global_rate_ = float(df["ignition"].mean())
        doy = df["date"].dt.dayofyear

        # Expand each observation across its smoothing window so a fire on
        # day 300 also informs days 285..315.
        offsets = np.arange(-self.window_days, self.window_days + 1)
        frames = []
        for off in offsets:
            frames.append(pd.DataFrame({
                "cell_id": df["cell_id"].to_numpy(),
                "doy": ((doy.to_numpy() + off - 1) % 365) + 1,
                "ignition": df["ignition"].to_numpy(),
            }))
        expanded = pd.concat(frames, ignore_index=True)

        agg = expanded.groupby(["cell_id", "doy"])["ignition"].agg(["sum", "count"])
        # Laplace / Bayesian smoothing toward the global rate
        agg["rate"] = (
            (agg["sum"] + self.prior_strength * self.global_rate_)
            / (agg["count"] + self.prior_strength)
        )
        self.cell_doy_rate_ = agg["rate"]
        log.info(
            "fitted climatology: global rate %.5f, %d (cell,doy) pairs",
            self.global_rate_, len(self.cell_doy_rate_),
        )
        return self

    def predict_proba(self, df: pd.DataFrame) -> np.ndarray:
        if self.cell_doy_rate_ is None:
            raise RuntimeError("call fit() first")
        key = pd.MultiIndex.from_arrays([df["cell_id"], df["date"].dt.dayofyear])
        return self.cell_doy_rate_.reindex(key).fillna(self.global_rate_).to_numpy()

    def save(self, path) -> None:
        with open(path, "wb") as f:
            pickle.dump(self, f)

    @staticmethod
    def load(path) -> ClimatologyBaseline:
        with open(path, "rb") as f:
            return pickle.load(f)


def cross_validate(df: pd.DataFrame) -> pd.DataFrame:
    """Leave-one-season-out evaluation of the baseline."""
    rows = []
    for season, tr, te in leave_one_season_out(df):
        model = ClimatologyBaseline().fit(df.iloc[tr])
        p = model.predict_proba(df.iloc[te])
        s = evaluate(df.iloc[te]["ignition"].to_numpy(), p)
        log.info("held-out %s | %s", season, s)
        rows.append({"season": season, **s.to_dict()})
    return pd.DataFrame(rows)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    proc = CFG.path("processed")
    src = proc / "cell_days_features.parquet"
    if not src.exists():
        src = proc / "cell_days.parquet"
    df = pd.read_parquet(src)
    df["date"] = pd.to_datetime(df["date"])

    results = cross_validate(df)
    out = CFG.path("reports") / "baseline_cv.csv"
    results.to_csv(out, index=False)

    print("\n=== CLIMATOLOGY BASELINE (leave-one-season-out) ===")
    print(results[["season", "pr_auc", "pr_auc_lift", "brier", "brier_skill"]]
          .to_string(index=False))
    print(f"\nmean PR-AUC {results['pr_auc'].mean():.4f} "
          f"+/- {results['pr_auc'].std():.4f}")
    print("THIS IS THE NUMBER TO BEAT.\n")

    # Fit on everything and persist, plus figures for the report
    full = ClimatologyBaseline().fit(df)
    full.save(CFG.path("models") / "baseline_climatology.pkl")
    p = full.predict_proba(df)
    fig = CFG.path("figures")
    plot_reliability(df["ignition"], p, fig / "baseline_reliability.png",
                     "Climatology baseline: reliability")
    plot_pr_curve(df["ignition"], p, fig / "baseline_pr_curve.png",
                  "Climatology baseline: precision-recall")
    print(f"figures -> {fig}")


if __name__ == "__main__":
    main()
