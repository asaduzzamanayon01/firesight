"""Headline numbers for the demo and the report, computed on ALL held-out seasons.

Owner: Ayon

For every day, rank the cells by predicted probability and flag the top q
share (default 5%). Then count what share of the real ignitions fell inside the
flagged cells. A random ranking captures about q. This is the operational
question a planner asks: "if I watch the top 5% of cells, how many fires do I
cover?" It uses out-of-fold predictions only, so every number is honest.

Run:
    PYTHONPATH=. python -m scripts.demo_stats
    PYTHONPATH=. python -m scripts.demo_stats --top 0.05 0.10 --calibrated
Writes reports/demo_stats.csv and prints a table.
"""
from __future__ import annotations

import argparse

import numpy as np
import pandas as pd

from src.config import CFG


def capture_rates(oof: pd.DataFrame, top: float, seed: int = 42) -> pd.DataFrame:
    """Per season: share of ignitions that fall in each day's top-`top` cells.

    Ties are broken at random (fixed seed) so a flat prediction cannot look good.
    """
    rng = np.random.default_rng(seed)
    d = oof.dropna(subset=["y_prob"]).copy()
    d["_r"] = rng.random(len(d))
    d["rank_pct"] = (
        d.sort_values(["y_prob", "_r"], ascending=[False, True])
        .groupby("date").cumcount() + 1
    )
    n_cells = d.groupby("date")["cell_id"].transform("count")
    d["flagged"] = d["rank_pct"] <= np.ceil(top * n_cells)
    rows = []
    for season, g in d.groupby("season"):
        pos = int(g["ignition"].sum())
        hit = int(g.loc[g["flagged"], "ignition"].sum())
        rows.append({"season": season, "top_share": top, "ignitions": pos,
                     "captured": hit, "capture_rate": hit / pos if pos else np.nan,
                     "random_expectation": top})
    return pd.DataFrame(rows)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--top", type=float, nargs="+", default=[0.05, 0.10])
    ap.add_argument("--calibrated", action="store_true")
    args = ap.parse_args()

    name = "oof_predictions_calibrated.parquet" if args.calibrated else "oof_predictions.parquet"
    oof = pd.read_parquet(CFG.path("processed") / name)
    oof["date"] = pd.to_datetime(oof["date"])

    out = pd.concat([capture_rates(oof, q) for q in args.top], ignore_index=True)
    dest = CFG.path("reports") / "demo_stats.csv"
    out.to_csv(dest, index=False)
    print("\n=== SHARE OF REAL IGNITIONS FALLING IN EACH DAY'S TOP CELLS ===")
    print(out.round(3).to_string(index=False))
    for q in args.top:
        tot = out[out["top_share"] == q]
        rate = tot["captured"].sum() / tot["ignitions"].sum()
        print(f"\nTop {q:.0%} of cells per day captured {rate:.1%} of all ignitions "
              f"(random would capture about {q:.0%}) -> {rate / q:.1f}x random")
    print(f"\nwrote {dest}")


if __name__ == "__main__":
    main()
