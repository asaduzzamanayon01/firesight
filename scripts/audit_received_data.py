"""Offline audit of the 30 October handoff; never downloads or modifies inputs.

Run with PYTHONPATH=. from the repository root. Input directory must contain
extracted/ignitions and extracted/weather, as described in the accompanying report.
Derived weather follows this revision's main pipeline; it is not an original
processed file supplied by the model author. No model is trained here.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from scripts.fetch_weather_openmeteo import build_point_table, lattice, nearest_point
from src.config import CFG
from src.features.grid import assign_cells, cell_centroids
from src.quality.checks import file_sha256
from src.quality.repository import check_repository_frame


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--inputs", type=Path, required=True)
    ap.add_argument("--output-dir", type=Path, required=True)
    ap.add_argument("--source-revision", required=True)
    args = ap.parse_args()
    out = args.output_dir
    out.mkdir(parents=True, exist_ok=True)
    start, end = "2019-07-01", "2025-06-30"
    report = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),  # noqa: UP017
        "audit_version": 1,
        "source_revision": args.source_revision,
        "data_mode": "forwarder-described real data; acquisition provenance incomplete",
        "input_files": [], "ignitions": [], "raw_weather_points": [],
        "complete_three_table_handoff": False,
        "forecast_validation": "NOT RUN: forecast.csv not supplied",
    }
    frames = []
    for f in sorted((args.inputs / "extracted/ignitions").glob("*.parquet")):
        df = pd.read_parquet(f)
        season_start = f.stem.removeprefix("ignitions_")
        season_end = str((pd.Timestamp(season_start) + pd.DateOffset(years=1)
                          - pd.Timedelta(days=1)).date())
        r = check_repository_frame(df, "ignitions", start=season_start, end=season_end)
        r.update(file=f.name, sha256=file_sha256(f),
                 grouped_detection_count=int(df.detections_in_event.sum()))
        report["ignitions"].append(r)
        report["input_files"].append({"file": f.name, "sha256": r["sha256"],
                                     "bytes": f.stat().st_size})
        frames.append(df.assign(source_season=season_start))
        print(f"checked {f.name}: {len(df)} rows; passed={r['passed']}", flush=True)
    if len(frames) != 6:
        raise ValueError("Expected exactly six seasonal ignition tables")
    events = pd.concat(frames, ignore_index=True)
    assigned = assign_cells(events)
    valid = assigned.loc[assigned.cell_id.ge(0)]
    positive = valid.groupby(["cell_id", "date"]).size()
    grid = cell_centroids()
    days = len(pd.date_range(start, end))
    report["event_summary"] = {
        "event_rows": len(events),
        "grouped_detection_count": int(events.detections_in_event.sum()),
        "duplicate_season_event_ids": int(events.duplicated(["source_season", "event_id"]).sum()),
        "repeated_bare_event_ids_across_seasons": int(events.event_id.duplicated().sum()),
        "event_id_scope": "local to each seasonal file; use (source_season,event_id)",
        "unassigned_events": int(assigned.cell_id.lt(0).sum()),
        "positive_cell_days": len(positive),
        "cell_days_with_multiple_event_rows": int(positive.gt(1).sum()),
        "total_model_cell_days": len(grid) * days,
        "positive_cell_day_rate_percent": len(positive) / (len(grid) * days) * 100,
        "ignition_contract_all_passed": all(x["passed"] for x in report["ignitions"]),
    }
    points = lattice(0.2)
    raw = {}
    expect_d = pd.date_range("2018-07-01", end).strftime("%Y-%m-%d").tolist()
    expect_h = pd.date_range("2018-07-01", "2025-06-30 23:00", freq="h").strftime(
        "%Y-%m-%dT%H:%M").tolist()
    for f in sorted((args.inputs / "extracted/weather").glob("*.json")):
        batch = int(f.stem.rsplit("_", 1)[1])
        responses = json.loads(f.read_text())
        ids = points.iloc[batch:batch + 12].point_id
        report["input_files"].append({"file": f.name, "sha256": file_sha256(f),
                                     "bytes": f.stat().st_size})
        for pid, js in zip(ids, responses, strict=True):
            pid = int(pid)
            if pid in raw:
                raise ValueError("Duplicate request point ID")
            raw[pid] = js
            daily, hourly = js["daily"], js["hourly"]
            variables = {}
            for group_name, group in (("daily", daily), ("hourly", hourly)):
                for name, values in group.items():
                    if name == "time":
                        continue
                    a = pd.to_numeric(pd.Series(values), errors="coerce")
                    variables[f"{group_name}.{name}"] = {
                        "values": len(a), "expected_values": len(group["time"]),
                        "missing_or_nonfinite": int((~np.isfinite(a)).sum()),
                        "min": float(a.min()), "max": float(a.max()),
                    }
            report["raw_weather_points"].append({
                "point_id": pid, "file": f.name,
                "requested_lat": float(points.iloc[pid].lat),
                "requested_lon": float(points.iloc[pid].lon),
                "returned_lat": js["latitude"], "returned_lon": js["longitude"],
                "timezone": js["timezone"], "utc_offset_seconds": js["utc_offset_seconds"],
                "daily_expected_axis_match": daily["time"] == expect_d,
                "hourly_expected_axis_match": hourly["time"] == expect_h,
                "daily_duplicate_times": len(daily["time"]) - len(set(daily["time"])),
                "hourly_duplicate_times": len(hourly["time"]) - len(set(hourly["time"])),
                "daily_units": js["daily_units"], "hourly_units": js["hourly_units"],
                "variables": variables,
            })
        print(f"checked weather batch {batch}: {len(responses)} points", flush=True)
    if set(raw) != set(points.point_id):
        raise ValueError("Raw responses do not cover the current request lattice")
    raw_points = report["raw_weather_points"]
    coords = {(x["returned_lat"], x["returned_lon"]) for x in raw_points}
    report["raw_weather_summary"] = {
        "request_points": len(raw), "unique_returned_coordinates": len(coords),
        "days_per_point_including_spinup": len(expect_d),
        "hours_per_point": len(expect_h), "model_days_per_point": days,
        "all_daily_axes_complete": all(x["daily_expected_axis_match"] for x in raw_points),
        "all_hourly_axes_complete": all(x["hourly_expected_axis_match"] for x in raw_points),
        "all_variable_lengths_match": all(v["values"] == v["expected_values"]
                                          for x in raw_points for v in x["variables"].values()),
        "missing_or_nonfinite_values": sum(v["missing_or_nonfinite"]
                                            for x in raw_points for v in x["variables"].values()),
        "timezones": sorted({x["timezone"] for x in raw_points}),
        "units_consistent": all(x["daily_units"] == raw_points[0]["daily_units"]
                                and x["hourly_units"] == raw_points[0]["hourly_units"]
                                for x in raw_points),
        "ranges": {key: {"min": min(x["variables"][key]["min"] for x in raw_points),
                         "max": max(x["variables"][key]["max"] for x in raw_points)}
                   for key in raw_points[0]["variables"]},
    }
    table = build_point_table(raw, pd.Timestamp(start))
    mapping = nearest_point(grid, points)
    weather = mapping.merge(table, on="point_id", how="left").drop(columns="point_id")
    weather = weather[["cell_id", "date", *CFG.weather.variables]].sort_values(
        ["cell_id", "date"]).reset_index(drop=True)
    weather_file = out / "weather_reconstructed.parquet"
    weather.to_parquet(weather_file, index=False)
    grid.to_csv(out / "grid_reconstructed.csv", index=False)
    mapping.to_csv(out / "cell_to_weather_point.csv", index=False)
    print(f"reconstructed {len(weather):,} cell-days; running unchanged checker", flush=True)
    r = check_repository_frame(weather, "weather", grid=grid, start=start, end=end)
    r.update(sha256=file_sha256(weather_file), origin="locally reconstructed from supplied JSON",
             original_author_processed_weather_supplied=False)
    report["reconstructed_weather"] = r
    west, south, east, north = CFG.region.bbox
    outside = ~(grid.centroid_lat.between(south, north) & grid.centroid_lon.between(west, east))
    report["grid_summary"] = {
        "origin": "locally reconstructed from current main src/features/grid.py",
        "actual_run_grid_supplied": False,
        "cells": len(grid), "centres_outside_configured_bbox": int(outside.sum()),
        "weather_rows_at_those_centres": int(outside.sum()) * days,
        "weather_points_used_by_grid": int(mapping.point_id.nunique()),
        "bbox": list(CFG.region.bbox),
        "sha256": file_sha256(out / "grid_reconstructed.csv"),
    }
    report["limitations"] = [
        "Forwarded files identify real data by sender claim; original FIRMS request manifests absent.",
        "Event-day coverage cannot establish successful retrieval of every source window.",
        "Weather response metadata has units/timezone but no selected model or acquisition timestamp.",
        "Batch-to-request-point mapping is inferred from filenames and current pipeline order, not a request manifest.",
        "Derived weather and grid reproduce current main assumptions; actual model-run artefacts/revision absent.",
        "Main event dates are UTC; weather days are Australia/Perth. Team must approve their interpretation together.",
        "Main and firesight-geo use different bbox/grid/clustering/day conventions; no silent substitution performed.",
        "No forecast.csv, model metrics or calibrated predictions were provided; model quality is not reproduced.",
        "Historical reanalysis and simplified KBDI do not establish live forecast availability.",
    ]
    report["overall_acceptance"] = "PENDING: missing forecast/run provenance and grid/day policy"
    (out / "real-data-audit.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(json.dumps({k: report[k] for k in ("event_summary", "raw_weather_summary",
                                           "grid_summary", "overall_acceptance")}, indent=2))


if __name__ == "__main__":
    main()
