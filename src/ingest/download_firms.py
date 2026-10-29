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
from collections.abc import Sequence
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from urllib.error import URLError
from urllib.parse import quote
from urllib.request import urlopen

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
    """Keep legacy inclusive end_date input; send NASA's required start date."""
    if not map_key:
        raise ValueError("FIRMS_MAP_KEY is required in the environment")
    if days < 1 or days > 5:
        raise ValueError(
            "days must be between 1 and 5; split seasonal pulls into documented chunks"
        )

    bounds = ",".join(f"{coordinate:.6f}" for coordinate in bbox)
    return "/".join(
        (
            FIRMS_AREA_API,
            quote(map_key, safe=""),
            quote(source, safe=""),
            quote(bounds, safe=","),
            str(days),
            (end_date - timedelta(days=days - 1)).isoformat(),
        )
    )


def redacted_url(
    source: str, bbox: tuple[float, float, float, float], days: int, end_date: date
) -> str:
    """Return a manifest-safe FIRMS URL with no API key."""
    bounds = ",".join(f"{coordinate:.6f}" for coordinate in bbox)
    return "/".join(
        (
            FIRMS_AREA_API,
            "<redacted>",
            source,
            bounds,
            str(days),
            (end_date - timedelta(days=days - 1)).isoformat(),
        )
    )


def download_csv(url: str, timeout_seconds: int) -> bytes:
    """Fetch a FIRMS CSV and reject empty responses."""
    try:
        with urlopen(url, timeout=timeout_seconds) as response:
            content = response.read()
    except (URLError, TimeoutError, OSError):
        raise RuntimeError("FIRMS request failed; credential-bearing URL suppressed") from None
    if not content.strip():
        raise RuntimeError("FIRMS returned an empty response")
    import csv
    import io

    try:
        header = next(csv.reader(io.StringIO(content.decode("utf-8-sig"))))
    except (ValueError, StopIteration, UnicodeError):
        raise RuntimeError("FIRMS response is not a valid CSV") from None
    if not {"latitude", "longitude", "acq_date", "acq_time"}.issubset(header):
        raise RuntimeError("FIRMS response lacks required detection columns")
    return content


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
    if csv_path.exists() or manifest_path.exists():
        raise FileExistsError("output already exists; choose a new run directory")
    csv_path.write_bytes(content)

    manifest = {
        "source_provider": "NASA FIRMS",
        "product": source,
        "retrieved_at_utc": datetime.now(UTC).isoformat(),
        "query_url": redacted_url(source, bbox, days, end_date),
        "bbox_west_south_east_north": list(bbox),
        "day_range": days,
        "start_date": (end_date - timedelta(days=days - 1)).isoformat(),
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
        default=5,
        help="days ending on --end-date (1-5; default: 5)",
    )
    parser.add_argument(
        "--end-date",
        type=parse_date,
        default=date.today(),
        help="inclusive end date; converted to NASA start date (default: today)",
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
