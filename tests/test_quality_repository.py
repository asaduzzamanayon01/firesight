"""Integration regressions for the repository's real column and Parquet contracts."""

import json
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

from src.config import CFG
from src.quality.checks import read_table
from src.quality.repository import check_repository_frame

ROOT = Path(__file__).resolve().parents[1]


def events():
    return pd.DataFrame(
        {
            "event_id": [1, 2],
            "latitude": [-32.0, -32.0],
            "longitude": [116.0, 116.0],
            "acq_datetime": pd.to_datetime(["2025-01-01 01:00:00.123456", "2025-01-01 02:00:00"], format="mixed"),
            "date": pd.to_datetime(["2025-01-01"] * 2),
            "detections_in_event": [1, 2],
        }
    )


def weather():
    return pd.DataFrame(
        {
            "cell_id": [0],
            "date": pd.to_datetime(["2025-01-01"]),
            **{name: [1.0] for name in CFG.weather.variables},
        }
    )


def grid():
    return pd.DataFrame({"cell_id": [0], "centroid_lat": [-32.0], "centroid_lon": [116.0]})


def codes(result):
    return {item["code"] for item in result["issues"]}


def test_distinct_events_same_place_and_day_pass():
    assert check_repository_frame(events(), "ignitions")["passed"]


def test_event_day_disagreement_fails():
    frame = events()
    frame.loc[0, "date"] = pd.Timestamp("2025-01-02")
    assert "event_day_not_utc_acquisition_day" in codes(check_repository_frame(frame, "ignitions"))


def test_missing_repository_metadata_fails():
    assert not check_repository_frame(events().drop(columns="event_id"), "ignitions")["passed"]


def test_duplicate_event_id_fails():
    assert "duplicate_event_ids" in codes(
        check_repository_frame(events().assign(event_id=1), "ignitions")
    )


@pytest.mark.parametrize("count", [0, 1.5, float("inf"), None])
def test_invalid_detection_count_fails(count):
    assert "invalid_detection_counts" in codes(
        check_repository_frame(events().assign(detections_in_event=count), "ignitions")
    )


def test_weather_uses_configured_variables_and_centroid_grid():
    assert check_repository_frame(weather(), "weather", grid=grid())["passed"]
    assert not check_repository_frame(weather().drop(columns="kbdi"), "weather", grid=grid())[
        "passed"
    ]


def test_unknown_weather_cell_fails_without_dropping_rows():
    result = check_repository_frame(weather().assign(cell_id=99), "weather", grid=grid())
    assert "unknown_cell_ids" in codes(result)
    assert result["rows"] == 1


def test_grid_outside_box_and_duplicate_ids_fail():
    result = check_repository_frame(weather(), "weather", grid=grid().assign(centroid_lon=120))
    assert "grid_centres_outside_study_box_or_invalid" in codes(result)
    with pytest.raises(ValueError):
        check_repository_frame(weather(), "weather", grid=pd.concat([grid(), grid()]))


def test_parquet_keeps_subsecond_event_precision(tmp_path):
    frame = events()
    frame.loc[1, "acq_datetime"] = pd.Timestamp("2025-01-01 01:00:00.123457")
    path = tmp_path / "events.parquet"
    frame.to_parquet(path)
    assert check_repository_frame(read_table(path), "ignitions")["passed"]


def test_full_cli_reads_parquet_with_repository_defaults(tmp_path):
    events().to_parquet(tmp_path / "ignitions.parquet")
    weather().to_parquet(tmp_path / "weather.parquet")
    grid().to_parquet(tmp_path / "grid.parquet")
    pd.DataFrame(
        {
            "cell_id": [0],
            "lat": [-32.0],
            "lon": [116.0],
            "date": ["2025-01-01"],
            "probability": [0.1],
            "actual": [0],
            "season": ["2024-2025"],
        }
    ).to_csv(tmp_path / "forecast.csv", index=False)
    args = [
        sys.executable,
        str(ROOT / "scripts/check_data_quality.py"),
        "--data-mode",
        "test-fixture",
        "--output-dir",
        str(tmp_path / "report"),
    ]
    for kind, name in [
        ("ignitions", "ignitions.parquet"),
        ("weather", "weather.parquet"),
        ("grid", "grid.parquet"),
        ("forecast", "forecast.csv"),
    ]:
        args += [f"--{kind}", str(tmp_path / name)]
    run = subprocess.run(args, capture_output=True, text=True)
    assert run.returncode == 0, run.stderr
    report = json.loads((tmp_path / "report/quality-report.json").read_text())
    assert report["passed"] and report["data_mode"] == "test-fixture"
    assert report["settings"]["complete_input_set"]
    assert len(report["tables"]) == 3
