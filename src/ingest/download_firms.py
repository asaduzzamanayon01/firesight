"""Download a NASA FIRMS area report and record reproducibility metadata.

This script is maintained by Yian Wang, Data & Pipeline, for FireSight.
It writes an unchanged FIRMS CSV and a sidecar JSON manifest. API credentials are
read from FIRMS_MAP_KEY and are never written to output or logs.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Sequence
from urllib.parse import quote


FIRMS_AREA_API = "https://firms.modaps.eosdis.nasa.gov/api/area/csv"


def parse_date(value: str) -> date:
    """Parse an ISO-8601 calendar date for the FIRMS query endpoint."""
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("end date must be YYYY-MM-DD") from exc


def parse_bbox(value: str) -> tuple[float, float, float, float]:
    """Validate a west,south,east,north bounding box."""
    try:
        west, south, east, north = (float(part.strip()) for part in value.split(","))
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            "bbox must be four numbers: west,south,east,north"
        ) from exc

    if not (-180 <= west < east <= 180 and -90 <= south < north <= 90):
        raise argparse.ArgumentTypeError("bbox values are outside valid longitude/latitude ranges")
    return west, south, east, north


def build_area_url(
    map_key: str,
    source: str,
    bbox: tuple[float, float, float, float],
    days: int,
    end_date: date,
) -> str:
    """Build the FIRMS area endpoint URL without logging its credential."""
    if not map_key:
        raise ValueError("FIRMS_MAP_KEY is required; set it in .env or the environment")
    if days < 1 or days > 365:
        raise ValueError("days must be between 1 and 365")

    bounds = ",".join(f"{coordinate:.6f}" for coordinate in bbox)
    return "/".join(
        (
            FIRMS_AREA_API,
            quote(map_key, safe=""),
            quote(source, safe=""),
            quote(bounds, safe=","),
            str(days),
            end_date.isoformat(),
        )
    )


def redacted_url(source: str, bbox: tuple[float, float, float, float], days: int, end_date: date) -> str:
    """Return a manifest-safe FIRMS URL with no API key."""
    bounds = ",".join(f"{coordinate:.6f}" for coordinate in bbox)
    return "/".join(
        (FIRMS_AREA_API, "<redacted>", source, bounds, str(days), end_date.isoformat())
    )


def download_csv(url: str, timeout_seconds: int) -> bytes:
    """Fetch a FIRMS CSV and reject empty responses."""
    try:
        import requests
    except ImportError as exc:
        raise RuntimeError(
            "requests is required; install dependencies with python -m pip install -r requirements.txt"
        ) from exc

    response = requests.get(url, timeout=timeout_seconds)
    response.raise_for_status()
    if not response.content.strip():
        raise RuntimeError("FIRMS returned an empty response")
    return response.content


def write_download(
    content: bytes,
    output_dir: Path,
    source: str,
    bbox: tuple[float, float, float, float],
    days: int,
    end_date: date,
) -> tuple[Path, Path]:
    """Write raw content and a reproducibility manifest to the chosen directory."""
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = f"firms_{source.lower()}_{end_date.isoformat()}_{days}d"
    csv_path = output_dir / f"{stem}.csv"
    manifest_path = output_dir / f"{stem}.manifest.json"
    csv_path.write_bytes(content)

    manifest = {
        "source_provider": "NASA FIRMS",
        "product": source,
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "query_url": redacted_url(source, bbox, days, end_date),
        "bbox_west_south_east_north": list(bbox),
        "lookback_days": days,
        "end_date": end_date.isoformat(),
        "output_file": csv_path.name,
        "sha256": hashlib.sha256(content).hexdigest(),
        "data_rows": max(0, len(content.decode("utf-8", errors="replace").splitlines()) - 1),
    }
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return csv_path, manifest_path


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Download a NASA FIRMS area report and write a source manifest."
    )
    parser.add_argument(
        "--bbox",
        required=True,
        type=parse_bbox,
        metavar="WEST,SOUTH,EAST,NORTH",
        help="longitude/latitude bounding box in WGS84",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=10,
        help="number of days ending on --end-date (1-365; default: 10)",
    )
    parser.add_argument(
        "--end-date",
        type=parse_date,
        default=date.today(),
        help="query end date in YYYY-MM-DD (default: today)",
    )
    parser.add_argument(
        "--source",
        default="VIIRS_SNPP_NRT",
        help="FIRMS source identifier (default: VIIRS_SNPP_NRT)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/raw/firms"),
        help="directory for raw CSV and manifest (default: data/raw/firms)",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=int,
        default=30,
        help="HTTP timeout in seconds (default: 30)",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = make_parser().parse_args(argv)
    if args.timeout_seconds < 1:
        raise ValueError("timeout-seconds must be positive")

    url = build_area_url(
        os.environ.get("FIRMS_MAP_KEY", ""),
        args.source,
        args.bbox,
        args.days,
        args.end_date,
    )
    content = download_csv(url, args.timeout_seconds)
    csv_path, manifest_path = write_download(
        content,
        args.output_dir,
        args.source,
        args.bbox,
        args.days,
        args.end_date,
    )
    print(f"Saved {csv_path} and {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

