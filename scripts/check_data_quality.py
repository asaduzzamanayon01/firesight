"""Run from the project root. Exits 0 on pass, 1 on invalid data, 2 on usage errors."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.config import CFG  # noqa: E402
from src.quality.checks import check_frame, file_sha256, read_table, validate_bbox, write_report  # noqa: E402
from src.quality.repository import check_repository_frame  # noqa: E402


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for kind in ("ignitions", "weather", "forecast"):
        parser.add_argument(f"--{kind}", type=Path)
    parser.add_argument("--schema", choices=["repository", "canonical"], default="repository")
    parser.add_argument(
        "--bbox",
        default=",".join(map(str, CFG.region.bbox)),
        help="west,south,east,north; use --bbox=... for negative west",
    )
    parser.add_argument(
        "--weather-features",
        default=",".join(CFG.weather.variables),
        help="comma-separated numeric columns in canonical schema",
    )
    parser.add_argument(
        "--grid",
        type=Path,
        help="CSV/Parquet with unique cell_id, lat, lon for weather without coordinates",
    )
    parser.add_argument(
        "--column-map",
        type=Path,
        help="JSON mapping by kind: original column name to canonical name",
    )
    parser.add_argument(
        "--date-timezone", default="UTC", help="timezone for offset-free source dates"
    )
    parser.add_argument("--start", type=date.fromisoformat)
    parser.add_argument("--end", type=date.fromisoformat)
    parser.add_argument("--data-mode", choices=["real", "synthetic", "test-fixture"], required=True)
    parser.add_argument("--revision", help="actual source commit SHA if known")
    parser.add_argument("--output-dir", type=Path, default=Path("reports/data-quality"))
    args = parser.parse_args(argv)
    paths = {k: getattr(args, k) for k in ("ignitions", "weather", "forecast") if getattr(args, k)}
    if not paths:
        parser.error("provide at least one input table")
    if args.start and args.end and args.start > args.end:
        parser.error("start must be on or before end")
    try:
        bbox = validate_bbox([float(p) for p in args.bbox.split(",")])
        # Validate the timezone even for empty inputs.
        from zoneinfo import ZoneInfo

        ZoneInfo(args.date_timezone)
        mappings = json.loads(args.column_map.read_text()) if args.column_map else {}
        features = tuple(c.strip() for c in args.weather_features.split(",") if c.strip())
        if args.weather and not features:
            parser.error("--weather requires --weather-features")
    except (ValueError, KeyError, OSError) as exc:
        parser.error(str(exc))
    results = []
    for kind, path in paths.items():
        try:
            frame = read_table(path)
            mapping = mappings.get(kind, {})
            frame = frame.rename(columns=mapping)
            if (
                args.schema == "canonical"
                and kind == "weather"
                and args.grid
                and not {"lat", "lon"}.issubset(frame.columns)
            ):
                grid = read_table(args.grid)
                if (
                    not {"cell_id", "lat", "lon"}.issubset(grid.columns)
                    or grid.cell_id.duplicated().any()
                ):
                    raise ValueError("grid requires unique cell_id and lat/lon")
                frame = frame.drop(columns=[c for c in ("lat", "lon") if c in frame])
                frame = frame.merge(
                    grid[["cell_id", "lat", "lon"]],
                    how="left",
                    on="cell_id",
                    validate="many_to_one",
                )
            checker = check_repository_frame if args.schema == "repository" else check_frame
            options = (
                {"grid": read_table(args.grid)} if args.schema == "repository" and args.grid else {}
            )
            result = checker(
                frame,
                kind,
                bbox,
                weather_features=features,
                start=args.start,
                end=args.end,
                date_timezone=args.date_timezone,
                **options,
            )
            result["sha256"] = file_sha256(path)
            result["input_name"] = path.name
            if kind == "weather" and args.grid:
                result["grid_sha256"] = file_sha256(args.grid)
        except (ValueError, OSError, ImportError, TypeError):
            # No exception repr: source data and credential-bearing paths stay out of logs.
            result = {
                "kind": kind,
                "rows": None,
                "passed": False,
                "issues": [
                    {
                        "code": "input_unreadable_or_contract_invalid",
                        "count": 1,
                        "severity": "error",
                    }
                ],
            }
        results.append(result)
    payload = write_report(
        results,
        args.output_dir,
        data_mode=args.data_mode,
        bbox=bbox,
        revision=args.revision,
        settings={
            "weather_features": features,
            "column_map": mappings,
            "date_timezone": args.date_timezone,
            "schema": args.schema,
            "complete_input_set": set(paths) == {"ignitions", "weather", "forecast"},
            "start": str(args.start) if args.start else None,
            "end": str(args.end) if args.end else None,
        },
    )
    print(
        f"{'PASS' if payload['passed'] else 'FAIL'}: {len(results)} table(s). See quality-report.json and quality-summary.md."
    )
    return 0 if payload["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
