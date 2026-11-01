"""Exact baseline equivalence and safe output-directory handling for the replay."""

import numpy as np
import pandas as pd
import pytest

from scripts.reproduce_received_run import compact_baseline_fit, main
from src.models.baseline_climatology import ClimatologyBaseline


def test_compact_baseline_matches_original_including_year_and_leap_boundaries():
    dates = pd.date_range("2019-12-01", "2021-01-31")
    frame = pd.MultiIndex.from_product([[0, 1], dates], names=["cell_id", "date"]).to_frame(index=False)
    frame["ignition"] = np.random.default_rng(42).binomial(1, 0.05, len(frame))
    original = ClimatologyBaseline().fit(frame)
    compact = compact_baseline_fit(frame)
    np.testing.assert_allclose(compact.predict_proba(frame), original.predict_proba(frame), rtol=0, atol=1e-15)


def test_existing_run_directory_is_never_overwritten(tmp_path):
    inputs = tmp_path / "inputs"
    inputs.mkdir()
    for i in range(6):
        (inputs / f"ignitions_{i}.parquet").touch()
    weather = tmp_path / "weather.parquet"
    weather.touch()
    sentinel = tmp_path / "existing/keep.txt"
    sentinel.parent.mkdir()
    sentinel.write_text("previous run")
    with pytest.raises(SystemExit) as exc:
        main(["--events-dir", str(inputs), "--weather", str(weather), "--output-dir", str(sentinel.parent),
              "--source-revision", "test", "--forecast-start", "2025-01-10"])
    assert exc.value.code == 2
    assert sentinel.read_text() == "previous run"
