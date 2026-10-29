"""Tests for the Open-Meteo weather fetcher. No network needed."""
import numpy as np
import pandas as pd

from scripts.fetch_weather_openmeteo import (
    build_point_table,
    kbdi,
    lattice,
    nearest_point,
    to_daily,
)
from src.features.grid import cell_centroids


def fake_response(days=10):
    t = pd.date_range("2022-01-01", periods=days, freq="D")
    hours = pd.date_range("2022-01-01", periods=days * 24, freq="h")
    return {
        "daily": {
            "time": [d.strftime("%Y-%m-%d") for d in t],
            "temperature_2m_max": [35.0] * days,
            "wind_speed_10m_max": [6.0] * days,
            "precipitation_sum": [0.0] * days,
        },
        "hourly": {
            "time": [h.strftime("%Y-%m-%dT%H:%M") for h in hours],
            "relative_humidity_2m": [20.0 + (h.hour % 24) for h in hours],
        },
    }


def test_rh_min_is_the_daily_minimum():
    out = to_daily(fake_response())
    assert len(out) == 10
    assert (out["rh_min"] == 20.0).all()


def test_kbdi_stays_in_range_and_rises_in_hot_dry_spell():
    q = kbdi(np.full(120, 38.0), np.zeros(120), annual_rain=800.0)
    assert q.min() >= 0 and q.max() <= 800
    assert q[-1] > q[10] > 0


def test_kbdi_drops_after_heavy_rain():
    tmax = np.full(80, 36.0)
    rain = np.zeros(80)
    rain[60] = 60.0
    q = kbdi(tmax, rain, annual_rain=800.0)
    assert q[60] < q[59]


def test_small_rain_below_threshold_does_not_reduce_kbdi():
    tmax = np.full(40, 36.0)
    rain = np.zeros(40)
    rain[30] = 3.0
    q = kbdi(tmax, rain, annual_rain=800.0)
    assert q[30] >= q[29]


def test_every_cell_gets_a_point():
    pts = lattice(0.2)
    m = nearest_point(cell_centroids(), pts)
    assert len(m) == len(cell_centroids())
    assert m["point_id"].isin(pts["point_id"]).all()


def test_spin_up_days_are_dropped():
    raw = {0: fake_response(10)}
    out = build_point_table(raw, pd.Timestamp("2022-01-06"))
    assert out["date"].min() == pd.Timestamp("2022-01-06")
    assert {"t2m_max", "rh_min", "wind_speed_max", "precip_24h", "kbdi"} <= set(out.columns)


def test_forecast_export_has_the_agreed_columns():
    from scripts.export_forecast import export

    dates = pd.date_range("2024-01-01", periods=10, freq="D")
    oof = pd.DataFrame({
        "cell_id": np.tile([0, 1], 10), "date": np.repeat(dates, 2),
        "season": "2023-24", "ignition": 0, "y_prob": 0.003,
    })
    out = export(oof, start=None, days=3, calibrated=False)
    assert list(out.columns) == ["cell_id", "lat", "lon", "date", "probability", "actual", "season"]
    assert out["date"].nunique() == 3
    assert out["lat"].notna().all()
