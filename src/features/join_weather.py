"""FS-11: Join weather features onto the cell-day table.

Owner: Ayon
Jira: FS-11 (Join weather features to cell-day table)
Depends on: Yian's ERA5 download (FS-4)

THE LEAKAGE RULE
----------------
To predict whether a fire starts on day D, we may only use weather we would
actually have had BEFORE day D. Every weather column is therefore shifted by
`lag_days` (default 1). If you skip this you get a model with a beautiful
PR-AUC that cannot be deployed, because on the real morning of day D nobody
knows day D's observed maximum temperature yet.

This is the single easiest way to ruin the project, and the single easiest
thing for a marker to catch. The shift happens in `lag_and_roll()` below and
is unit-tested in tests/test_join_weather.py.
"""
from __future__ import annotations

import logging

import pandas as pd

from src.config import CFG

log = logging.getLogger(__name__)


def lag_and_roll(weather: pd.DataFrame) -> pd.DataFrame:
    """Shift every weather variable back by lag_days, then add rolling windows.

    Parameters
    ----------
    weather : DataFrame with [cell_id, date, <variables...>], one row per
        cell-day, sorted arbitrarily.

    Returns
    -------
    DataFrame with lagged columns suffixed `_lag{N}` and rolling aggregates
    suffixed `_roll{W}`. The unlagged originals are dropped so they cannot
    leak by accident.
    """
    lag = CFG.weather.lag_days
    variables = [v for v in CFG.weather.variables if v in weather.columns]
    missing = set(CFG.weather.variables) - set(variables)
    if missing:
        log.warning("weather variables absent from input: %s", sorted(missing))

    df = weather.sort_values(["cell_id", "date"]).copy()
    g = df.groupby("cell_id", sort=False)

    out = df[["cell_id", "date"]].copy()

    for v in variables:
        lagged = g[v].shift(lag)
        out[f"{v}_lag{lag}"] = lagged
        # Rolling windows are computed ON THE LAGGED SERIES, so they inherit
        # the shift and cannot see day D either.
        for w in CFG.weather.rolling_windows:
            out[f"{v}_roll{w}"] = (
                lagged.groupby(df["cell_id"], sort=False)
                .rolling(w, min_periods=max(1, w // 2))
                .mean()
                .reset_index(level=0, drop=True)
            )

    # Dryness streak: consecutive days with negligible rain, also lagged
    if "precip_24h" in variables:
        dry = (g["precip_24h"].shift(lag) < 1.0).astype(int)
        out["dry_spell_days"] = (
            dry.groupby(df["cell_id"], sort=False)
            .apply(lambda s: s * (s.groupby((s != s.shift()).cumsum()).cumcount() + 1))
            .reset_index(level=0, drop=True)
        )

    return out


def join(cell_days: pd.DataFrame, weather: pd.DataFrame) -> pd.DataFrame:
    """Left-join lagged weather onto the cell-day spine."""
    feats = lag_and_roll(weather)
    before = len(cell_days)
    out = cell_days.merge(feats, on=["cell_id", "date"], how="left")
    assert len(out) == before, "join changed row count - duplicate weather keys?"

    null_frac = out[[c for c in feats.columns if c not in ("cell_id", "date")]].isna().mean()
    worst = null_frac.sort_values(ascending=False).head(3)
    log.info("joined %d weather features. Highest null rates:\n%s",
             len(feats.columns) - 2, worst.to_string())
    return out


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    proc = CFG.path("processed")
    cell_days = pd.read_parquet(proc / "cell_days.parquet")
    weather = pd.read_parquet(proc / "weather.parquet")
    out = join(cell_days, weather)
    dest = proc / "cell_days_features.parquet"
    out.to_parquet(dest, index=False)
    print(f"wrote {len(out):,} rows x {out.shape[1]} cols -> {dest}")


if __name__ == "__main__":
    main()
