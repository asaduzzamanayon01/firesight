"""Generate synthetic FireSight data so the whole pipeline runs TODAY.

Owner: Ayon
Not a Jira story - this is development scaffolding.

WHY THIS EXISTS
---------------
Real FIRMS and ERA5 downloads take hours and need API keys and Yian's work.
But the pipeline, the metrics harness and the CI tests all need to run NOW,
today, before any of that lands. This generator produces a small cell-day
table with the same SCHEMA and the same ~0.3% positive rate as the real thing.

It is deliberately generated from a known relationship (heat + dryness +
human proximity raise ignition probability) so we can sanity-check that the
pipeline recovers a signal it is supposed to recover. If LightGBM cannot beat
climatology on synthetic data where a signal definitely exists, the bug is in
our code, not in the world.

NEVER put synthetic results in the proposal or the report as if they were
real. Label every figure produced from this as synthetic.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.config import CFG
from src.features.build_cell_days import add_temporal_features, season_of

RNG = np.random.default_rng(CFG.project.random_seed)

# Small grid and short span so the whole pipeline runs in about a minute
N_CELLS = 300
N_SEASONS = 6


def generate() -> tuple[pd.DataFrame, pd.DataFrame]:
    m = CFG.seasons.season_start_month
    start = pd.Timestamp(year=2019, month=m, day=1)
    end = start + pd.DateOffset(years=N_SEASONS) - pd.Timedelta(days=1)
    dates = pd.date_range(start, end, freq="D")

    cells = pd.DataFrame({"cell_id": np.arange(N_CELLS)})
    base = cells.merge(pd.DataFrame({"date": dates}), how="cross")
    base["season"] = season_of(base["date"])

    n = len(base)
    doy = base["date"].dt.dayofyear.to_numpy()
    # Summer peak in the southern hemisphere: warmest around day 15
    seasonal = np.cos(2 * np.pi * (doy - 15) / 365.25)

    # Per-cell static character
    cell_heat = RNG.normal(0, 2.0, N_CELLS)[base["cell_id"].to_numpy()]
    dist_road = np.abs(RNG.lognormal(0.5, 0.8, N_CELLS))[base["cell_id"].to_numpy()]
    dist_powerline = np.abs(RNG.lognormal(0.8, 0.9, N_CELLS))[base["cell_id"].to_numpy()]
    elevation = RNG.uniform(0, 400, N_CELLS)[base["cell_id"].to_numpy()]

    t2m_max = 24 + 9 * seasonal + cell_heat + RNG.normal(0, 3.0, n)
    rh_min = np.clip(55 - 22 * seasonal + RNG.normal(0, 9, n), 5, 100)
    wind = np.clip(RNG.gamma(2.0, 3.0, n), 0, 45)
    precip = np.where(RNG.random(n) < (0.30 - 0.16 * seasonal),
                      RNG.gamma(1.4, 4.0, n), 0.0)
    kbdi = np.clip(95 + 75 * seasonal + RNG.normal(0, 28, n), 0, 203)

    weather = pd.DataFrame({
        "cell_id": base["cell_id"], "date": base["date"],
        "t2m_max": t2m_max, "rh_min": rh_min, "wind_speed_max": wind,
        "precip_24h": precip, "kbdi": kbdi,
    })

    # KNOWN GENERATING PROCESS - this is the signal the model must recover
    logit = (
        -6.55
        + 0.085 * (t2m_max - 24)
        - 0.022 * (rh_min - 55)
        + 0.012 * (kbdi - 95)
        + 0.030 * wind
        - 0.30 * np.log1p(dist_road)
        - 0.22 * np.log1p(dist_powerline)
        + 0.0009 * elevation
    )
    p = 1 / (1 + np.exp(-logit))
    base["ignition"] = RNG.binomial(1, p)
    base["n_ignitions"] = base["ignition"]

    base = add_temporal_features(base)
    base["dist_road_km"] = dist_road
    base["dist_powerline_km"] = dist_powerline
    base["elevation_m"] = elevation

    return base, weather


def main() -> None:
    from src.features.join_weather import join

    cell_days, weather = generate()
    proc = CFG.path("processed")

    cell_days.to_parquet(proc / "cell_days.parquet", index=False)
    weather.to_parquet(proc / "weather.parquet", index=False)

    feats = join(cell_days, weather)
    feats.to_parquet(proc / "cell_days_features.parquet", index=False)

    rate = cell_days["ignition"].mean()
    print("=== SYNTHETIC DATA (development only - never report as real) ===")
    print(f"  rows            {len(cell_days):,}")
    print(f"  cells           {cell_days['cell_id'].nunique():,}")
    print(f"  seasons         {cell_days['season'].nunique()}")
    print(f"  positives       {cell_days['ignition'].sum():,}")
    print(f"  positive rate   {rate*100:.3f}%   <- the class imbalance")
    print(f"  imbalance ratio 1 : {int((1-rate)/rate)}")
    print(f"  feature columns {feats.shape[1]}")
    print(f"\n  -> {proc}\n")


if __name__ == "__main__":
    main()
