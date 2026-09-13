"""FS-1: Download NASA FIRMS active-fire detections and cluster into ignition events.

Owner: Ayon
Jira: FS-1 (Register NASA FIRMS API key and document access)

WHY THIS MATTERS
----------------
FIRMS gives us one row per satellite *detection*. A single fire burning for
three days across six grid cells produces dozens of detections. If we label
every one of those as an ignition, the model learns fire SPREAD, not fire
STARTS - which is the whole point of the project.

So we cluster detections in space and time (DBSCAN over x, y, t) and keep only
the EARLIEST detection per cluster. That earliest point is our ignition label.

Run:
    export FIRMS_MAP_KEY=...
    python -m src.ingest.firms_client --start 2023-01-01 --days 30
"""
from __future__ import annotations

import argparse
import logging
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

from src.config import CFG, firms_key

log = logging.getLogger(__name__)

# FIRMS caps each request at 10 days
MAX_DAYS_PER_REQUEST = 10


def build_url(start: date, days: int) -> str:
    """FIRMS area API URL.

    Format: /api/area/csv/KEY/SOURCE/WEST,SOUTH,EAST,NORTH/DAYS/START
    """
    w, s, e, n = CFG.region.bbox
    return (
        f"{CFG.firms.base_url}/{firms_key()}/{CFG.firms.source}/"
        f"{w},{s},{e},{n}/{days}/{start.isoformat()}"
    )


def fetch_window(start: date, days: int) -> pd.DataFrame:
    """Fetch one <=10 day window from FIRMS."""
    if days > MAX_DAYS_PER_REQUEST:
        raise ValueError(f"FIRMS allows max {MAX_DAYS_PER_REQUEST} days per request")
    url = build_url(start, days)
    log.info("FIRMS request: %s .. +%dd", start, days)
    # pandas reads the CSV straight from the URL
    return pd.read_csv(url)


def fetch_range(start: date, end: date) -> pd.DataFrame:
    """Fetch an arbitrary date range by chunking into 10-day windows."""
    frames, cursor = [], start
    while cursor < end:
        days = min(MAX_DAYS_PER_REQUEST, (end - cursor).days)
        try:
            frames.append(fetch_window(cursor, days))
        except Exception as exc:  # noqa: BLE001 - one bad window must not kill the run
            log.warning("window %s failed: %s", cursor, exc)
        cursor += timedelta(days=days)
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


def clean(df: pd.DataFrame) -> pd.DataFrame:
    """Standardise columns and drop low-confidence detections."""
    if df.empty:
        return df
    df = df.copy()
    df["acq_datetime"] = pd.to_datetime(
        df["acq_date"].astype(str) + " " + df["acq_time"].astype(str).str.zfill(4),
        format="%Y-%m-%d %H%M",
        errors="coerce",
    )
    df = df.dropna(subset=["acq_datetime", "latitude", "longitude"])

    # VIIRS confidence is categorical: l / n / h
    if CFG.firms.min_confidence == "nominal" and "confidence" in df:
        df = df[df["confidence"].astype(str).str.lower().str[0].isin(["n", "h"])]

    return df.reset_index(drop=True)


def cluster_to_events(df: pd.DataFrame) -> pd.DataFrame:
    """Cluster detections into fire events, return one ignition row per event.

    Space and time are on different scales, so we convert both to kilometres:
    time is scaled so that `cluster_eps_hours` maps onto `cluster_eps_km`.
    That lets a single DBSCAN eps govern both dimensions.
    """
    from sklearn.cluster import DBSCAN

    if df.empty:
        return df

    eps_km = CFG.firms.cluster_eps_km
    eps_h = CFG.firms.cluster_eps_hours

    # Local equirectangular projection to km - fine over a 100km bbox
    lat0 = float(df["latitude"].mean())
    x_km = df["longitude"].to_numpy() * 111.32 * np.cos(np.radians(lat0))
    y_km = df["latitude"].to_numpy() * 110.57

    t_hours = (
        df["acq_datetime"] - df["acq_datetime"].min()
    ).dt.total_seconds().to_numpy() / 3600.0
    t_scaled = t_hours * (eps_km / eps_h)

    coords = np.column_stack([x_km, y_km, t_scaled])
    labels = DBSCAN(
        eps=eps_km, min_samples=CFG.firms.cluster_min_samples, metric="euclidean"
    ).fit_predict(coords)

    df = df.assign(event_id=labels)
    df = df[df["event_id"] >= 0]  # DBSCAN marks noise as -1

    # The ignition is the earliest detection in each event
    ignitions = (
        df.sort_values("acq_datetime")
        .groupby("event_id", as_index=False)
        .first()[["event_id", "latitude", "longitude", "acq_datetime"]]
    )
    ignitions["detections_in_event"] = (
        df.groupby("event_id").size().reindex(ignitions["event_id"]).to_numpy()
    )
    ignitions["date"] = ignitions["acq_datetime"].dt.normalize()

    log.info(
        "clustered %d detections into %d ignition events", len(df), len(ignitions)
    )
    return ignitions.reset_index(drop=True)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    ap = argparse.ArgumentParser(description="Download and cluster FIRMS detections")
    ap.add_argument("--start", required=True, help="YYYY-MM-DD")
    ap.add_argument("--days", type=int, default=10)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    start = date.fromisoformat(args.start)
    raw = fetch_range(start, start + timedelta(days=args.days))
    events = cluster_to_events(clean(raw))

    out = Path(args.out) if args.out else CFG.path("raw") / f"ignitions_{args.start}.parquet"
    events.to_parquet(out, index=False)
    print(f"wrote {len(events)} ignition events -> {out}")


if __name__ == "__main__":
    main()
