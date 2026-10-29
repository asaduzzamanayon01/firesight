"""Non-mutating quality checks for FireSight tables; no network access required."""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd


@dataclass(frozen=True)
class Contract:
    required: tuple[str, ...]
    unique: tuple[str, ...]
    timestamp: str = "date"
    daily: bool = True
    coordinates: bool = True
    numeric: tuple[str, ...] = ()


CONTRACTS = {
    # Adapt explicitly if Ayon's processed event schema differs.
    "ignitions": Contract(("lat", "lon", "date"), ("lat", "lon", "date"), daily=False),
    "weather": Contract(("cell_id", "date"), ("cell_id", "date")),
    "forecast": Contract(
        ("cell_id", "lat", "lon", "date", "probability", "actual", "season"),
        ("cell_id", "date"),
        numeric=("probability", "actual"),
    ),
}


def validate_bbox(bbox):
    if len(bbox) != 4:
        raise ValueError("bbox requires west,south,east,north")
    west, south, east, north = map(float, bbox)
    if not all(map(math.isfinite, (west, south, east, north))):
        raise ValueError("bbox must be finite")
    if not (-180 <= west < east <= 180 and -90 <= south < north <= 90):
        raise ValueError("bbox is invalid")
    return west, south, east, north


def _missing(series):
    return series.isna() | series.astype(str).str.strip().isin(["", "nan", "NaN", "None", "null"])


def check_frame(
    frame,
    kind,
    bbox,
    *,
    weather_features=(),
    column_map=None,
    start=None,
    end=None,
    date_timezone="UTC",
):
    """Return counts only, never raw rows. Column map maps incoming to canonical names.

    Timestamps without offsets use date_timezone explicitly. Daily table dates must
    be ISO YYYY-MM-DD. Event timestamps also accept offset-bearing ISO datetimes.
    Ignition duplicate keys flag candidate repeated detections, not unique fires.
    """
    bbox = validate_bbox(bbox)
    if kind not in CONTRACTS:
        raise ValueError("unknown table kind")
    contract = CONTRACTS[kind]
    original_columns = list(frame.columns)
    mapped = frame.rename(columns=column_map or {}).copy()
    issues = []

    def issue(code, count, severity="error"):
        if count:
            issues.append({"code": code, "count": int(count), "severity": severity})

    duplicate_columns = int(mapped.columns.duplicated().sum())
    issue("duplicate_column_names", duplicate_columns)
    if duplicate_columns:
        return {
            "kind": kind,
            "rows": len(mapped),
            "columns": original_columns,
            "passed": False,
            "issues": issues,
            "missing": {},
            "coverage": {},
        }
    features = tuple(weather_features)
    if kind == "weather" and not features:
        raise ValueError("weather requires an explicit list of numeric feature columns")
    required = tuple(dict.fromkeys(contract.required + (features if kind == "weather" else ())))
    missing_columns = [name for name in required if name not in mapped.columns]
    issue("missing_required_columns", len(missing_columns))
    issue("empty_table", int(mapped.empty))
    missing = {str(col): int(_missing(mapped[col]).sum()) for col in mapped.columns}
    issue("missing_required_values", sum(missing[c] for c in required if c in mapped))
    issue(
        "missing_optional_values",
        sum(v for c, v in missing.items() if c not in required),
        "warning",
    )
    issue("exact_duplicate_rows", int(mapped.duplicated().sum()))
    coverage = {}
    dates = None
    if contract.timestamp in mapped:
        values = mapped[contract.timestamp]
        if pd.api.types.is_datetime64_any_dtype(values):
            # Preserve event precision and timezone; daily dates must be naive midnight.
            if contract.daily and values.dt.tz is None and values.eq(values.dt.normalize()).all():
                text = values.dt.strftime("%Y-%m-%d")
            else:
                text = values.map(lambda value: value.isoformat() if pd.notna(value) else "")
        else:
            text = values.astype(str)
        iso_pattern = (
            r"\d{4}-\d{2}-\d{2}"
            if contract.daily
            else r"\d{4}-\d{2}-\d{2}(?:[T ][0-2]\d:[0-5]\d(?::[0-5]\d(?:\.\d+)?)?(?:Z|[+-]\d{2}:?\d{2})?)?"
        )
        valid_format = text.str.fullmatch(iso_pattern).fillna(False)

        def parse(value):
            try:
                ts = pd.Timestamp(value)
                if ts.tzinfo is None:
                    ts = ts.tz_localize(date_timezone, ambiguous="raise", nonexistent="raise")
                return ts.tz_convert("UTC")
            except (ValueError, TypeError):
                return pd.NaT

        dates = pd.to_datetime(text.where(valid_format).map(parse), utc=True)
        bad = dates.isna() | ~valid_format
        issue("invalid_timestamps", int(bad.sum()))
        valid = dates.dropna()
        if not valid.empty:
            coverage = {"start_utc": valid.min().isoformat(), "end_utc": valid.max().isoformat()}
        if start:
            issue(
                "timestamps_before_requested_start",
                int((dates < pd.Timestamp(start, tz=date_timezone).tz_convert("UTC")).sum()),
            )
        if end:
            end_exclusive = pd.Timestamp(end, tz=date_timezone).tz_convert("UTC") + pd.Timedelta(
                days=1
            )
            issue("timestamps_after_requested_end", int((dates >= end_exclusive).sum()))
    if all(col in mapped for col in contract.unique):
        keys = mapped[list(contract.unique)].copy()
        if dates is not None:
            keys[contract.timestamp] = dates
        if kind == "ignitions":
            for col in ("lat", "lon"):
                keys[col] = pd.to_numeric(keys[col], errors="coerce")
        if "cell_id" in keys:
            keys["cell_id"] = keys["cell_id"].astype(str).str.strip()
        issue("duplicate_record_keys", int(keys.duplicated().sum()))
    has_coords = "lat" in mapped and "lon" in mapped
    if contract.coordinates or "lat" in mapped or "lon" in mapped:
        if not has_coords:
            issue("missing_coordinate_columns", 1)
        else:
            lat = pd.to_numeric(mapped["lat"], errors="coerce")
            lon = pd.to_numeric(mapped["lon"], errors="coerce")
            west, south, east, north = bbox
            valid = lat.between(south, north) & lon.between(west, east)
            issue("coordinates_outside_study_box_or_invalid", int((~valid).sum()))
    numeric = contract.numeric + (features if kind == "weather" else ())
    for col in numeric:
        if col not in mapped:
            continue
        values = pd.to_numeric(mapped[col], errors="coerce")
        finite = values.map(lambda v: pd.notna(v) and math.isfinite(float(v)))
        issue(f"non_numeric_or_nonfinite_{col}", int((~finite).sum()))
        if col == "probability":
            issue("probability_outside_0_1", int((finite & ~values.between(0, 1)).sum()))
        if col == "actual":
            issue("actual_not_binary", int((finite & ~values.isin([0, 1])).sum()))
    if kind == "forecast" and all(c in mapped for c in ("cell_id", "lat", "lon")):
        coords = mapped[["cell_id", "lat", "lon"]].drop_duplicates()
        issue(
            "cell_ids_with_inconsistent_coordinates",
            int((coords.groupby("cell_id").size() > 1).sum()),
        )
    summary = {}
    if kind == "forecast" and "actual" in mapped:
        actual = pd.to_numeric(mapped["actual"], errors="coerce")
        summary = {
            "positive_rows": int(actual.eq(1).sum()),
            "invalid_label_rows": int((~actual.isin([0, 1])).sum()),
            "positive_rate_valid_labels": float(actual[actual.isin([0, 1])].mean())
            if actual.isin([0, 1]).any()
            else None,
        }
        if "season" in mapped:
            summary["season_counts"] = {
                str(k): int(v) for k, v in mapped.groupby("season", dropna=False).size().items()
            }
    if kind == "ignitions":
        summary["event_table_rows"] = len(mapped)
        summary["interpretation"] = (
            "Rows are detections or supplied events, not independently verified ignitions."
        )
    return {
        "kind": kind,
        "rows": len(mapped),
        "columns": original_columns,
        "missing_required_columns": missing_columns,
        "missing": missing,
        "coverage": coverage,
        "summary": summary,
        "issues": issues,
        "coordinate_check": "performed"
        if has_coords
        else "requires separate grid validation"
        if kind == "weather"
        else "unavailable",
        "passed": not any(i["severity"] == "error" for i in issues),
    }


def read_table(path):
    path = Path(path)
    if path.suffix.lower() == ".csv":
        # Preserve identifiers such as 001; reject duplicate headers before pandas renames them.
        import csv

        with path.open(encoding="utf-8-sig", newline="") as handle:
            header = next(csv.reader(handle), [])
        if len(header) != len(set(header)):
            raise ValueError("CSV has duplicate column names")
        return pd.read_csv(path, dtype=str)
    if path.suffix.lower() == ".parquet":
        return pd.read_parquet(path)
    raise ValueError("supported inputs are CSV and Parquet")


def file_sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_report(results, output_dir, *, data_mode, bbox, revision=None, settings=None):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": 1,
        "generated_utc": datetime.now(UTC).isoformat(),
        "data_mode": data_mode,
        "data_mode_basis": "caller declaration; provenance must be reviewed separately",
        "study_bbox": list(bbox),
        "code_revision": revision,
        "settings": settings or {},
        "tables": results,
        "passed": bool(results) and all(r["passed"] for r in results),
    }
    (output_dir / "quality-report.json").write_text(
        json.dumps(payload, indent=2, allow_nan=False) + "\n"
    )
    lines = [
        "# FireSight data quality summary",
        "",
        f"Data mode: **{data_mode}** (caller declared).",
        "",
        "This report counts supplied records. It does not establish model accuracy, provenance, or causal ignition locations.",
        "",
        "| Table | Rows | Result |",
        "|---|---:|---|",
    ]
    for result in results:
        lines.append(
            f"| {result['kind']} | {result['rows']} | {'PASS' if result['passed'] else 'FAIL'} |"
        )
    for result in results:
        lines += [
            "",
            f"## {result['kind']}",
            "",
            f"Input SHA256: `{result.get('sha256', 'unavailable')}`",
            "",
            "Coverage: " + json.dumps(result.get("coverage", {})),
            "",
            "Summary: " + json.dumps(result.get("summary", {})),
            "",
            "Missing values by column:",
        ]
        lines += [f"- `{col}`: {count}" for col, count in result.get("missing", {}).items()]
        lines += ["", "Checks:"] + [
            f"- {i['severity']}: {i['code']} ({i['count']})" for i in result["issues"]
        ]
        if not result["issues"]:
            lines.append("- No issues found by the configured checks.")
    (output_dir / "quality-summary.md").write_text("\n".join(lines) + "\n")
    return payload
