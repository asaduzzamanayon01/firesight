"""Missing populations cannot be hidden by duplicates or unrelated rows."""

import json
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

from src.config import CFG
from src.quality.checks import file_sha256
from src.quality.coverage import check_cell_day_coverage

ROOT = Path(__file__).resolve().parents[1]
START, END = "2025-01-01", "2025-01-03"


def grid():
    return pd.DataFrame({"cell_id": ["001", "002"], "lat": [-32.0] * 2, "lon": [116.0] * 2})


def keys():
    return pd.MultiIndex.from_product(
        [grid().cell_id, pd.date_range(START, END).strftime("%Y-%m-%d")], names=["cell_id", "date"]
    ).to_frame(index=False)


def check(frame, expected=None):
    return check_cell_day_coverage(frame, grid() if expected is None else expected, start=START, end=END)


def test_complete_population_and_inputs_unchanged():
    frame, expected = keys(), grid()
    originals = frame.copy(deep=True), expected.copy(deep=True)
    result = check(frame, expected)
    assert result["passed"] and result["expected_cell_days"] == 6
    pd.testing.assert_frame_equal(frame, originals[0])
    pd.testing.assert_frame_equal(expected, originals[1])


def test_entire_missing_day_is_reported():
    result = check(keys().query("date != '2025-01-02'"))
    assert not result["passed"]
    assert result["missing_cell_days"] == 2
    assert result["dates_absent_all_expected_cells"] == 1
    assert result["cells_absent_entire_window"] == 0


def test_entire_missing_cell_is_reported():
    result = check(keys().query("cell_id == '001'"))
    assert result["missing_cell_days"] == 3
    assert result["cells_absent_entire_window"] == 1
    assert result["dates_absent_all_expected_cells"] == 0


def test_duplicates_cannot_hide_missing_pairs_with_same_row_count():
    frame = keys()
    result = check(pd.concat([frame.iloc[1:], frame.iloc[[1]]], ignore_index=True))
    assert result["missing_cell_days"] == 1
    assert result["duplicate_valid_pair_rows"] == 1
    assert result["observed_unique_expected_cell_days"] == 5


@pytest.mark.parametrize(
    "replacement,field",
    [
        ({"cell_id": "999"}, "unknown_or_missing_cell_rows"),
        ({"cell_id": None}, "unknown_or_missing_cell_rows"),
        ({"date": "2024-12-31"}, "out_of_window_rows"),
        ({"date": "2025-01-04"}, "out_of_window_rows"),
        ({"date": "2025-02-30"}, "invalid_daily_date_rows"),
        ({"date": "2025-01-01T00:00:00+08:00"}, "invalid_daily_date_rows"),
        ({"date": "2025-01-01 12:00:00"}, "invalid_daily_date_rows"),
    ],
)
def test_unrelated_or_invalid_rows_do_not_fill_gaps(replacement, field):
    frame = keys()
    for name, value in replacement.items():
        frame.loc[0, name] = value
    result = check(frame)
    assert not result["passed"]
    assert result["missing_cell_days"] == 1
    assert result[field] == 1


def test_empty_table_reports_full_gap():
    result = check(keys().iloc[:0])
    assert result["missing_cell_days"] == 6
    assert result["cells_absent_entire_window"] == 2
    assert result["dates_absent_all_expected_cells"] == 3


@pytest.mark.parametrize("ids", [[], ["001", "001"], [None], [""], ["  "]])
def test_invalid_expected_grid_is_rejected(ids):
    with pytest.raises(ValueError):
        check(keys(), pd.DataFrame({"cell_id": ids}))


def test_explicit_filtered_grid_is_the_expected_population():
    # The helper must not infer an unfiltered population or a static-cell exclusion.
    result = check(keys().query("cell_id == '002'"), grid().iloc[[1]])
    assert result["passed"] and result["expected_cell_days"] == 3


def test_naive_midnight_parquet_dates_and_leading_zero_ids():
    frame = keys()
    frame["date"] = pd.to_datetime(frame.date)
    assert check(frame)["passed"]
    assert check(frame.assign(cell_id="1"))["unknown_or_missing_cell_rows"] == 6


@pytest.mark.parametrize("schema,kind", [("repository", "weather"), ("canonical", "forecast")])
def test_cli_coverage_is_opt_in_and_failure_is_in_both_reports(tmp_path, schema, kind):
    frame = keys().iloc[1:].assign(lat=-32.0, lon=116.0)
    if kind == "weather":
        frame = frame.assign(**{name: 1.0 for name in CFG.weather.variables})
    else:
        frame = frame.assign(probability=0.1, actual=0, season="2024-2025")
    input_path, grid_path = tmp_path / "table.csv", tmp_path / "grid.csv"
    frame.to_csv(input_path, index=False)
    grid().to_csv(grid_path, index=False)
    args = [
        sys.executable, str(ROOT / "scripts/check_data_quality.py"),
        f"--{kind}", str(input_path), "--grid", str(grid_path),
        "--schema", schema, "--data-mode", "test-fixture",
        "--start", START, "--end", END, "--output-dir", str(tmp_path / "report"),
    ]
    default = subprocess.run(args, capture_output=True, text=True)
    assert default.returncode == 0, default.stderr
    strict = subprocess.run([*args, "--require-complete-cell-days"], capture_output=True, text=True)
    assert strict.returncode == 1, strict.stderr
    report = json.loads((tmp_path / "report/quality-report.json").read_text())
    table = report["tables"][0]
    assert table["expected_cell_day_coverage"]["missing_cell_days"] == 1
    assert table["grid_sha256"] == file_sha256(grid_path)
    assert report["settings"]["require_complete_cell_days"]
    assert "missing pairs: 1" in (tmp_path / "report/quality-summary.md").read_text()


@pytest.mark.parametrize("omitted", ["--grid", "--start", "--end", "--forecast"])
def test_cli_requires_explicit_coverage_contract(tmp_path, omitted):
    options = {"--forecast": "not-read.csv", "--grid": "not-read.csv", "--start": START, "--end": END}
    del options[omitted]
    # Keep an input when omitting forecast, so this tests the coverage prerequisites.
    if omitted == "--forecast":
        options["--ignitions"] = "not-read.parquet"
    args = [sys.executable, str(ROOT / "scripts/check_data_quality.py"),
            "--data-mode", "test-fixture", "--require-complete-cell-days"]
    for name, value in options.items():
        args += [name, value]
    run = subprocess.run(args, capture_output=True, text=True, cwd=tmp_path)
    assert run.returncode == 2
    assert "requires --grid, --start, --end and weather/forecast" in run.stderr
    assert not (tmp_path / "reports").exists()
