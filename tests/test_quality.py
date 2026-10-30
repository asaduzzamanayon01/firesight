"""Behaviour tests for malformed data and CLI failure handling."""

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.quality.checks import check_frame, read_table  # noqa: E402

spec = importlib.util.spec_from_file_location(
    "download_firms", ROOT / "src/ingest/download_firms.py"
)
firms = importlib.util.module_from_spec(spec)
spec.loader.exec_module(firms)
BBOX = (115.4, -32.3, 116.2, -31.5)  # fixture, not an approved project extent


def forecast():
    return pd.DataFrame(
        {
            "cell_id": ["001", "002"],
            "lat": [-32.0, -31.9],
            "lon": [115.8, 115.9],
            "date": ["2025-01-01"] * 2,
            "probability": [0.1, 0.8],
            "actual": [0, 1],
            "season": ["2024-25"] * 2,
        }
    )


class QualityTests(unittest.TestCase):
    def check(self, frame, kind="forecast", **kwargs):
        return check_frame(frame, kind, BBOX, **kwargs)

    def codes(self, frame, **kwargs):
        return {issue["code"] for issue in self.check(frame, **kwargs)["issues"]}

    def test_valid_forecast(self):
        result = self.check(forecast())
        self.assertTrue(result["passed"])
        self.assertEqual(result["summary"]["positive_rows"], 1)

    def test_missing_schema(self):
        self.assertIn("missing_required_columns", self.codes(forecast().drop(columns="season")))

    def test_duplicate_keys_even_when_probability_differs(self):
        frame = pd.concat([forecast(), forecast().iloc[[0]].assign(probability=0.2)])
        self.assertIn("duplicate_record_keys", self.codes(frame))

    def test_nonfinite_coordinates(self):
        frame = forecast()
        frame.loc[0, "lat"] = float("inf")
        self.assertIn("coordinates_outside_study_box_or_invalid", self.codes(frame))

    def test_outside_box(self):
        frame = forecast()
        frame.loc[0, "lon"] = 120
        self.assertFalse(self.check(frame)["passed"])

    def test_invalid_calendar_date(self):
        frame = forecast()
        frame.loc[0, "date"] = "2025-02-30"
        self.assertIn("invalid_timestamps", self.codes(frame))

    def test_numeric_timestamp_rejected(self):
        self.assertIn("invalid_timestamps", self.codes(forecast().assign(date=123)))

    def test_empty_table_fails(self):
        self.assertIn("empty_table", self.codes(forecast().iloc[:0]))

    def test_missing_values(self):
        frame = forecast()
        frame.loc[0, "cell_id"] = " "
        self.assertIn("missing_required_values", self.codes(frame))

    def test_probability_range(self):
        self.assertIn("probability_outside_0_1", self.codes(forecast().assign(probability=1.1)))

    def test_probability_nonfinite(self):
        self.assertIn(
            "non_numeric_or_nonfinite_probability",
            self.codes(forecast().assign(probability=float("inf"))),
        )

    def test_risk_percentile_accepts_endpoints_without_changing_input(self):
        frame = forecast().assign(risk_percentile=[0.0, 1.0])
        before = frame.copy(deep=True)
        self.assertTrue(self.check(frame)["passed"])
        pd.testing.assert_frame_equal(frame, before)

    def test_risk_percentile_rejects_values_outside_unit_interval(self):
        for value in (-0.1, 1.1):
            with self.subTest(value=value):
                result = self.check(forecast().assign(risk_percentile=value))
                self.assertFalse(result["passed"])
                self.assertIn("risk_percentile_outside_0_1", {i["code"] for i in result["issues"]})

    def test_risk_percentile_rejects_non_numeric_missing_and_nonfinite_values(self):
        for value in (None, "bad", float("nan"), float("inf")):
            with self.subTest(value=value):
                result = self.check(forecast().assign(risk_percentile=value))
                self.assertFalse(result["passed"])
                self.assertIn("non_numeric_or_nonfinite_risk_percentile",
                              {i["code"] for i in result["issues"]})

    def test_actual_binary(self):
        self.assertIn("actual_not_binary", self.codes(forecast().assign(actual=2)))

    def test_requested_range(self):
        self.assertIn(
            "timestamps_before_requested_start", self.codes(forecast(), start=date(2025, 2, 1))
        )

    def test_checks_do_not_mutate_inputs(self):
        frame = forecast()
        before = frame.copy(deep=True)
        self.check(frame)
        pd.testing.assert_frame_equal(frame, before)

    def test_weather_features_required(self):
        with self.assertRaises(ValueError):
            self.check(forecast(), kind="weather")

    def test_weather_missing_coordinates_fails(self):
        frame = forecast().assign(temp_c=20).drop(columns=["lat", "lon"])
        self.assertIn(
            "missing_coordinate_columns",
            {
                i["code"]
                for i in self.check(frame, kind="weather", weather_features=("temp_c",))["issues"]
            },
        )

    def test_weather_invalid_feature(self):
        result = self.check(
            forecast().assign(temp_c="bad"), kind="weather", weather_features=("temp_c",)
        )
        self.assertFalse(result["passed"])

    def test_timestamp_offsets_normalised_for_duplicates(self):
        frame = pd.DataFrame(
            {
                "lat": [-32.0, -32.0],
                "lon": [115.8, 115.8],
                "date": ["2025-01-01T08:00:00+08:00", "2025-01-01T00:00:00Z"],
            }
        )
        result = self.check(frame, kind="ignitions")
        self.assertIn("duplicate_record_keys", {i["code"] for i in result["issues"]})

    def test_explicit_column_mapping(self):
        frame = forecast().rename(columns={"lat": "latitude", "lon": "longitude"})
        self.assertTrue(
            self.check(frame, column_map={"latitude": "lat", "longitude": "lon"})["passed"]
        )

    def test_conflicting_mapping_fails(self):
        frame = forecast().assign(latitude=-32.0)
        self.assertIn("duplicate_column_names", self.codes(frame, column_map={"latitude": "lat"}))

    def test_grid_cell_coordinate_consistency(self):
        frame = pd.concat([forecast(), forecast().iloc[[0]].assign(date="2025-01-02", lon=116.0)])
        self.assertIn("cell_ids_with_inconsistent_coordinates", self.codes(frame))

    def test_identifiers_keep_leading_zeros(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "forecast.csv"
            forecast().to_csv(path, index=False)
            self.assertEqual(read_table(path).cell_id.iloc[0], "001")

    def test_duplicate_csv_headers_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "bad.csv"
            path.write_text("date,date\na,b\n")
            with self.assertRaises(ValueError):
                read_table(path)

    def test_cli_creates_failure_report_for_missing_file(self):
        with tempfile.TemporaryDirectory() as temp:
            run = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts/check_data_quality.py"),
                    "--forecast",
                    str(Path(temp) / "missing.csv"),
                    "--bbox",
                    ",".join(map(str, BBOX)),
                    "--schema",
                    "canonical",
                    "--data-mode",
                    "test-fixture",
                    "--output-dir",
                    temp,
                ],
                capture_output=True,
            )
            self.assertEqual(run.returncode, 1)
            report = json.loads((Path(temp) / "quality-report.json").read_text())
            self.assertFalse(report["passed"])
            self.assertEqual(report["data_mode"], "test-fixture")


class FirmsTests(unittest.TestCase):
    def test_nasa_date_is_start_not_end(self):
        url = firms.build_area_url("test-key", "VIIRS_SNPP_SP", BBOX, 5, date(2025, 1, 5))
        self.assertTrue(url.endswith("/5/2025-01-01"))

    def test_api_limit(self):
        with self.assertRaises(ValueError):
            firms.build_area_url("test-key", "VIIRS_SNPP_SP", BBOX, 6, date(2025, 1, 5))

    def test_raw_not_overwritten_and_manifest_has_no_key(self):
        with tempfile.TemporaryDirectory() as temp:
            args = (
                b"latitude,longitude,acq_date,acq_time\n",
                Path(temp),
                "VIIRS_SNPP_SP",
                BBOX,
                5,
                date(2025, 1, 5),
            )
            raw, meta = firms.write_download(*args)
            content = json.loads(meta.read_text())
            self.assertEqual(content["start_date"], "2025-01-01")
            self.assertIn("<redacted>", content["query_url"])
            with self.assertRaises(FileExistsError):
                firms.write_download(*args)
            self.assertEqual(raw.read_bytes(), args[0])

    def test_request_errors_hide_credential_url(self):
        from urllib.error import URLError

        with patch.object(firms, "urlopen", side_effect=URLError("https://example/secret-key")):
            with self.assertRaises(RuntimeError) as error:
                firms.download_csv("https://example/secret-key", 1)
            self.assertNotIn("secret-key", str(error.exception))


class IntegrationTests(unittest.TestCase):
    def run_quality(self, directory, extra=None):
        fixtures = ROOT / "tests/fixtures"
        args = [
            sys.executable,
            str(ROOT / "scripts/check_data_quality.py"),
            "--ignitions",
            str(fixtures / "ignitions.csv"),
            "--weather",
            str(fixtures / "weather.csv"),
            "--grid",
            str(fixtures / "grid.csv"),
            "--forecast",
            str(fixtures / "forecast.csv"),
            "--weather-features",
            "temp_c,rh,wind_kmh,rain_mm",
            "--bbox",
            ",".join(map(str, BBOX)),
            "--schema",
            "canonical",
            "--data-mode",
            "test-fixture",
            "--output-dir",
            str(directory),
        ]
        return subprocess.run(args + (extra or []), capture_output=True, text=True)

    def test_all_three_tables_and_grid_join_pass(self):
        with tempfile.TemporaryDirectory() as temp:
            run = self.run_quality(temp)
            self.assertEqual(run.returncode, 0, run.stderr)
            result = json.loads((Path(temp) / "quality-report.json").read_text())
            self.assertEqual([t["rows"] for t in result["tables"]], [1, 2, 2])
            self.assertIn("grid_sha256", result["tables"][1])
            self.assertEqual(result["tables"][1]["missing"]["lat"], 0)

    def test_unmatched_weather_cell_fails(self):
        with tempfile.TemporaryDirectory() as temp:
            grid_path = Path(temp) / "bad_grid.csv"
            grid_path.write_text("cell_id,lat,lon\n001,-32,115.8\n")
            run = self.run_quality(temp, ["--grid", str(grid_path)])
            self.assertEqual(run.returncode, 1)
            result = json.loads((Path(temp) / "quality-report.json").read_text())
            self.assertFalse(result["tables"][1]["passed"])


if __name__ == "__main__":
    unittest.main()
