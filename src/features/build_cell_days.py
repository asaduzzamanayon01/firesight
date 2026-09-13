"""FS-10: Build the cell-day base table for all seasons.

Owner: Ayon
Jira: FS-10 (Build cell-day base table for all seasons)

WHAT THIS PRODUCES
------------------
The spine of the entire project. One row per (cell_id, date), labelled 1 if a
fire STARTED in that cell on that date, else 0.

    cell_id | date       | season  | ignition
    ------- | ---------- | ------- | --------
    421     | 2019-11-03 | 2019-20 | 0
    422     | 2019-11-03 | 2019-20 | 1

Size check: ~1,650 cells x 365 days x 13 seasons = ~7.8M rows if we keep the
whole year. We keep only the fire season window, which cuts it to ~4.5M.
Positive rate lands around 0.3%.

THE CLASS IMBALANCE LIVES HERE. Everything downstream (scale_pos_weight,
PR-AUC, calibration) exists because of the ratio this file produces.
"""
from __future__ import annotations

import logging

import numpy as np
import pandas as pd

from src.config import CFG
from src.features.grid import assign_cells, n_cells

log = logging.getLogger(__name__)


def season_of(dates: pd.Series) -> pd.Series:
    """Map a date to its Australian fire season label, e.g. '2019-20'.

    Season starts in July, so 2019-11-03 and 2020-02-14 are both '2019-20'.
    """
    m = CFG.seasons.season_start_month
    start_year = np.where(dates.dt.month >= m, dates.dt.year, dates.dt.year - 1)
    return pd.Series(
        [f"{y}-{str(y + 1)[-2:]}" for y in start_year], index=dates.index
    )


def date_spine() -> pd.DataFrame:
    """Every date in the configured season range."""
    m = CFG.seasons.season_start_month
    start = pd.Timestamp(year=CFG.seasons.start_year, month=m, day=1)
    end = pd.Timestamp(year=CFG.seasons.end_year, month=m, day=1) - pd.Timedelta(days=1)
    dates = pd.date_range(start, end, freq="D")
    out = pd.DataFrame({"date": dates})
    out["season"] = season_of(out["date"])
    return out


def build(ignitions: pd.DataFrame) -> pd.DataFrame:
    """Cross-join cells x dates, then left-join the ignition labels.

    Parameters
    ----------
    ignitions : DataFrame with [latitude, longitude, date] - output of
        firms_client.cluster_to_events().
    """
    dates = date_spine()
    cells = pd.DataFrame({"cell_id": np.arange(n_cells())})

    log.info("building spine: %d cells x %d dates", len(cells), len(dates))
    base = cells.merge(dates, how="cross")

    ign = assign_cells(ignitions.copy())
    ign = ign[ign["cell_id"] >= 0]
    ign["date"] = pd.to_datetime(ign["date"]).dt.normalize()

    # One flag per cell-day, even if two fires started in the same cell that day
    flags = (
        ign.groupby(["cell_id", "date"], as_index=False)
        .size()
        .rename(columns={"size": "n_ignitions"})
    )

    out = base.merge(flags, on=["cell_id", "date"], how="left")
    out["n_ignitions"] = out["n_ignitions"].fillna(0).astype(int)
    out["ignition"] = (out["n_ignitions"] > 0).astype(int)

    rate = out["ignition"].mean()
    log.info(
        "cell-day table: %s rows, %s positives, positive rate %.4f%%",
        f"{len(out):,}", f"{out['ignition'].sum():,}", rate * 100,
    )
    if rate > 0.05:
        log.warning(
            "Positive rate %.2f%% is suspiciously high. Did the event "
            "clustering run? Un-clustered detections inflate this.", rate * 100
        )
    return out


def add_temporal_features(df: pd.DataFrame) -> pd.DataFrame:
    """Cyclical day-of-year plus a simple season index.

    Day-of-year is circular: 31 Dec and 1 Jan are one day apart, but 365 and 1
    are far apart numerically. sin/cos encoding fixes that.
    """
    doy = df["date"].dt.dayofyear
    return df.assign(
        doy_sin=np.sin(2 * np.pi * doy / 365.25),
        doy_cos=np.cos(2 * np.pi * doy / 365.25),
        month=df["date"].dt.month,
        is_summer=df["date"].dt.month.isin([12, 1, 2]).astype(int),
    )


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    raw_dir = CFG.path("raw")
    files = sorted(raw_dir.glob("ignitions_*.parquet"))
    if not files:
        raise SystemExit(
            f"No ignition files in {raw_dir}. Run src.ingest.firms_client first, "
            "or `make synth` to generate synthetic data."
        )
    ignitions = pd.concat([pd.read_parquet(f) for f in files], ignore_index=True)
    out = add_temporal_features(build(ignitions))
    dest = CFG.path("processed") / "cell_days.parquet"
    out.to_parquet(dest, index=False)
    print(f"wrote {len(out):,} rows -> {dest}")


if __name__ == "__main__":
    main()
