"""Export a forecast file for the dashboard from the out-of-fold predictions.

Owner: Ayon. This is the agreed hand-off file between the model and the dashboard.

Every row is a prediction made by a model that never saw that season during
training (leave-one-season-out), so the dashboard can show honest "forecast
versus what happened" maps for past dates. This is a backtest, not a live
forecast, and the dashboard must say so.

Columns
-------
cell_id        grid cell (see src/features/grid.py)
lat, lon       cell centre (EPSG:4326)
date           the day the forecast is for
probability    predicted chance of an ignition in that cell on that day
actual         1 if a fire really started in that cell that day, else 0
season         fire season label, for example 2024-25

Run:
    PYTHONPATH=. python -m scripts.export_forecast --days 14
    PYTHONPATH=. python -m scripts.export_forecast --start 2025-01-10 --days 7 --calibrated
"""
from __future__ import annotations

import argparse

import pandas as pd

from src.config import CFG
from src.features.grid import cell_centroids


def export(oof: pd.DataFrame, start: str | None, days: int, calibrated: bool) -> pd.DataFrame:
    """Pick a date window from the out-of-fold predictions and add cell centres."""
    oof = oof.copy()
    oof["date"] = pd.to_datetime(oof["date"])
    if start is None:
        first = oof["date"].max() - pd.Timedelta(days=days - 1)
    else:
        first = pd.Timestamp(start)
    last = first + pd.Timedelta(days=days - 1)
    win = oof[(oof["date"] >= first) & (oof["date"] <= last)].copy()
    if win.empty:
        raise SystemExit(f"no predictions between {first.date()} and {last.date()}")

    if calibrated:
        from src.models.calibrate import IsotonicCalibrator

        cal = IsotonicCalibrator.load(CFG.path("models") / "calibrator.pkl")
        win["y_prob"] = cal.transform(win["y_prob"].to_numpy())

    cent = cell_centroids().rename(columns={"centroid_lat": "lat", "centroid_lon": "lon"})
    out = win.merge(cent, on="cell_id", how="left")
    out = out.rename(columns={"y_prob": "probability", "ignition": "actual"})
    cols = ["cell_id", "lat", "lon", "date", "probability", "actual", "season"]
    return out[cols].sort_values(["date", "cell_id"]).reset_index(drop=True)


def main() -> None:
    ap = argparse.ArgumentParser(description="Export forecast.csv for the dashboard")
    ap.add_argument("--start", default=None, help="first date YYYY-MM-DD (default: last N days)")
    ap.add_argument("--days", type=int, default=14)
    ap.add_argument("--calibrated", action="store_true", help="apply the isotonic calibrator")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    oof = pd.read_parquet(CFG.path("processed") / "oof_predictions.parquet")
    oof = oof.dropna(subset=["y_prob"])
    out = export(oof, args.start, args.days, args.calibrated)
    dest = args.out or str(CFG.path("processed") / "forecast.csv")
    out.to_csv(dest, index=False)
    print(f"wrote {len(out):,} rows, {out['date'].nunique()} days -> {dest}")
    print(f"mean probability {out['probability'].mean():.5f}, actual rate {out['actual'].mean():.5f}")


if __name__ == "__main__":
    main()
