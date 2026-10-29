"""Fetch daily weather from Open-Meteo (ERA5-based) and write weather.parquet.

Owner: Ayon. Needs no account and no API key, so the real-data run does not
depend on anyone else. Open-Meteo's historical archive serves ERA5 reanalysis.

Output columns match config/config.yaml (weather.variables):
    cell_id, date, t2m_max, rh_min, wind_speed_max, precip_24h, kbdi

How it works
------------
ERA5 weather is coarse (tens of km), so every 3 km cell does not need its own
request. We fetch a lattice of points (default every 0.2 degrees, about 36
points over the Perth study region) and give each cell the weather of its
nearest lattice point. Raw responses are cached under data/raw/openmeteo/, so
a rerun after an error resumes instead of starting again.

KBDI (Keetch-Byram Drought Index) is not provided by Open-Meteo, so it is
computed here from daily maximum temperature and rainfall (simplified form,
see kbdi()). Start-up values are discarded: weather is fetched from one year
before the first season and the first year is used as spin-up only.

Run:
    PYTHONPATH=. python -m scripts.fetch_weather_openmeteo            # config seasons
    PYTHONPATH=. python -m scripts.fetch_weather_openmeteo --start-year 2023 --end-year 2024 --step 0.4
"""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from src.config import CFG
from src.features.grid import cell_centroids

log = logging.getLogger(__name__)

API = "https://archive-api.open-meteo.com/v1/archive"
DAILY = "temperature_2m_max,wind_speed_10m_max,precipitation_sum"
HOURLY = "relative_humidity_2m"


def lattice(step: float) -> pd.DataFrame:
    """Regular lattice of weather points covering the study bbox."""
    w, s, e, n = CFG.region.bbox
    lons = np.arange(w, e + step, step)
    lats = np.arange(s, n + step, step)
    pts = [(la, lo) for la in lats for lo in lons]
    out = pd.DataFrame(pts, columns=["lat", "lon"])
    out.insert(0, "point_id", np.arange(len(out)))
    return out


def nearest_point(centroids: pd.DataFrame, points: pd.DataFrame) -> pd.DataFrame:
    """Map every cell to its nearest lattice point (longitude scaled to km)."""
    kx = 111.32 * np.cos(np.radians(float(centroids["centroid_lat"].mean())))
    cx = centroids["centroid_lon"].to_numpy()[:, None] * kx
    cy = centroids["centroid_lat"].to_numpy()[:, None] * 110.57
    px = points["lon"].to_numpy()[None, :] * kx
    py = points["lat"].to_numpy()[None, :] * 110.57
    idx = ((cx - px) ** 2 + (cy - py) ** 2).argmin(axis=1)
    return pd.DataFrame({
        "cell_id": centroids["cell_id"].to_numpy(),
        "point_id": points["point_id"].to_numpy()[idx],
    })


def request(points: pd.DataFrame, start: date, end: date, retries: int = 5) -> list[dict]:
    """One archive request for a batch of points. Retries on HTTP 429 and 5xx."""
    import requests

    params = {
        "latitude": ",".join(f"{v:.4f}" for v in points["lat"]),
        "longitude": ",".join(f"{v:.4f}" for v in points["lon"]),
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "daily": DAILY,
        "hourly": HOURLY,
        "wind_speed_unit": "ms",
        "timezone": "Australia/Perth",
    }
    for attempt in range(retries):
        resp = requests.get(API, params=params, timeout=120)
        if resp.status_code == 429 or resp.status_code >= 500:
            wait = 30 * (attempt + 1)
            log.warning("HTTP %s, waiting %ds (attempt %d)", resp.status_code, wait, attempt + 1)
            time.sleep(wait)
            continue
        resp.raise_for_status()
        data = resp.json()
        return data if isinstance(data, list) else [data]
    raise RuntimeError("Open-Meteo kept refusing the request. Wait an hour and rerun.")


def to_daily(js: dict) -> pd.DataFrame:
    """Turn one point's response into daily t2m_max, rh_min, wind, rain."""
    d = js["daily"]
    daily = pd.DataFrame({
        "date": pd.to_datetime(d["time"]),
        "t2m_max": d["temperature_2m_max"],
        "wind_speed_max": d["wind_speed_10m_max"],
        "precip_24h": d["precipitation_sum"],
    })
    h = js["hourly"]
    hourly = pd.DataFrame({
        "date": pd.to_datetime([t[:10] for t in h["time"]]),
        "rh": h["relative_humidity_2m"],
    })
    rh_min = hourly.groupby("date", as_index=False)["rh"].min().rename(columns={"rh": "rh_min"})
    return daily.merge(rh_min, on="date", how="left")


def kbdi(tmax: np.ndarray, rain: np.ndarray, annual_rain: float) -> np.ndarray:
    """Simplified Keetch-Byram Drought Index (0 = saturated, 800 = extreme drought).

    Daily drought factor from maximum temperature and mean annual rainfall,
    reduced by rainfall above 5 mm per rain event (consecutive wet days count as
    one event). Q is in hundredths of an inch, so 1 mm of net rain removes
    about 3.94 points.
    """
    q = 0.0
    out = np.empty(len(tmax))
    wet_run = 0.0
    for i, (t, r) in enumerate(zip(tmax, rain, strict=True)):
        t = 0.0 if np.isnan(t) else t
        r = 0.0 if np.isnan(r) else r
        if r > 0.0:
            before = wet_run
            wet_run += r
            net = max(wet_run - 5.0, 0.0) - max(before - 5.0, 0.0)
            q = max(q - net * 3.937, 0.0)
        else:
            wet_run = 0.0
        drought = (800.0 - q) * (0.968 * np.exp(0.0875 * t + 1.5552) - 8.3) \
            / (1.0 + 10.88 * np.exp(-0.001736 * annual_rain)) * 0.001
        q = float(np.clip(q + max(drought, 0.0), 0.0, 800.0))
        out[i] = q
    return out


def build_point_table(raw: dict[int, dict], first_day: pd.Timestamp) -> pd.DataFrame:
    """Daily weather per point, with KBDI computed and spin-up days dropped."""
    frames = []
    for pid, js in raw.items():
        df = to_daily(js).sort_values("date").reset_index(drop=True)
        years = max(len(df) / 365.25, 1.0)
        annual = float(df["precip_24h"].fillna(0).sum() / years)
        df["kbdi"] = kbdi(df["t2m_max"].to_numpy(float), df["precip_24h"].to_numpy(float), annual)
        df["point_id"] = pid
        frames.append(df[df["date"] >= first_day])
    return pd.concat(frames, ignore_index=True)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    ap = argparse.ArgumentParser(description="Fetch Open-Meteo weather and write weather.parquet")
    ap.add_argument("--start-year", type=int, default=CFG.seasons.start_year)
    ap.add_argument("--end-year", type=int, default=CFG.seasons.end_year)
    ap.add_argument("--step", type=float, default=0.2, help="lattice spacing in degrees")
    ap.add_argument("--batch", type=int, default=12, help="points per request")
    ap.add_argument("--sleep", type=float, default=2.0, help="seconds between requests")
    args = ap.parse_args()

    m = CFG.seasons.season_start_month
    first_day = pd.Timestamp(args.start_year, m, 1)
    last_day = pd.Timestamp(args.end_year, m, 1) - pd.Timedelta(days=1)
    spin_start = (first_day - pd.Timedelta(days=365)).date()
    end = min(last_day.date(), date.today() - timedelta(days=7))

    pts = lattice(args.step)
    cache = CFG.path("raw") / "openmeteo"
    cache.mkdir(parents=True, exist_ok=True)
    log.info("%d lattice points, %s to %s", len(pts), spin_start, end)

    raw: dict[int, dict] = {}
    for b in range(0, len(pts), args.batch):
        batch = pts.iloc[b:b + args.batch]
        f = cache / f"{spin_start}_{end}_{args.step}_{b}.json"
        if f.exists():
            res = json.loads(f.read_text())
        else:
            res = request(batch, spin_start, end)
            f.write_text(json.dumps(res))
            time.sleep(args.sleep)
        for pid, js in zip(batch["point_id"], res, strict=True):
            raw[int(pid)] = js
        log.info("batch %d done", b // args.batch + 1)

    table = build_point_table(raw, first_day)
    mapping = nearest_point(cell_centroids(), pts)
    out = mapping.merge(table, on="point_id", how="left").drop(columns="point_id")
    cols = ["cell_id", "date", "t2m_max", "rh_min", "wind_speed_max", "precip_24h", "kbdi"]
    out = out[cols].sort_values(["cell_id", "date"]).reset_index(drop=True)

    dest = CFG.path("processed") / "weather.parquet"
    out.to_parquet(dest, index=False)
    manifest = {
        "source_provider": "Open-Meteo historical archive (ERA5-based)",
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),  # noqa: UP017
        "endpoint": API,
        "daily": DAILY, "hourly": HOURLY,
        "lattice_step_degrees": args.step, "n_points": len(pts),
        "first_day": str(first_day.date()), "last_day": str(end),
        "kbdi_note": "simplified Keetch-Byram, one year spin-up discarded",
        "sha256": hashlib.sha256(Path(dest).read_bytes()).hexdigest(),
    }
    Path(str(dest) + ".manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"wrote {len(out):,} rows x {out.shape[1]} cols -> {dest}")
    print(f"missing values per column:\n{out.isna().sum().to_string()}")


if __name__ == "__main__":
    main()
