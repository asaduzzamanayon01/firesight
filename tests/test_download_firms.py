"""Unit tests for the FireSight FIRMS ingestion helper."""

from __future__ import annotations

import argparse
import sys
import unittest
from datetime import date
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src" / "ingest"))
import download_firms  # noqa: E402


class ParseBboxTests(unittest.TestCase):
    def test_parse_bbox_returns_west_south_east_north(self) -> None:
        self.assertEqual(
            download_firms.parse_bbox("115.4,-32.3,116.2,-31.5"),
            (115.4, -32.3, 116.2, -31.5),
        )

    def test_parse_bbox_rejects_reversed_longitudes(self) -> None:
        with self.assertRaises(argparse.ArgumentTypeError):
            download_firms.parse_bbox("116.2,-32.3,115.4,-31.5")


class UrlTests(unittest.TestCase):
    def test_api_key_is_not_in_redacted_manifest_url(self) -> None:
        bbox = (115.4, -32.3, 116.2, -31.5)
        url = download_firms.redacted_url("VIIRS_SNPP_NRT", bbox, 10, date(2026, 9, 13))
        self.assertIn("<redacted>", url)
        self.assertNotIn("secret-key", url)

    def test_build_area_url_contains_product_and_date(self) -> None:
        url = download_firms.build_area_url(
            "secret-key", "VIIRS_SNPP_NRT", (115.4, -32.3, 116.2, -31.5), 10, date(2026, 9, 13)
        )
        self.assertIn("VIIRS_SNPP_NRT", url)
        self.assertTrue(url.endswith("/10/2026-09-13"))


if __name__ == "__main__":
    unittest.main()

