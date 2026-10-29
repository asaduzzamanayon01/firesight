"""Adapt the FS-36 contract to main's ignition and weather schemas.

This module validates supplied data without changing source files or repairing rows.
UTC event days follow the current main branch. PR #3's Perth-day rule needs a team decision.
"""

from __future__ import annotations

import pandas as pd

from src.config import CFG
from src.quality.checks import check_frame


def check_repository_frame(
    frame,
    kind,
    bbox=None,
    *,
    grid=None,
    weather_features=None,
    start=None,
    end=None,
    date_timezone="UTC",
):
    bbox = tuple(CFG.region.bbox) if bbox is None else bbox
    features = tuple(CFG.weather.variables) if weather_features is None else weather_features
    adapted = frame.copy()
    extra = []

    def issue(code, count):
        if count:
            extra.append({"code": code, "count": int(count), "severity": "error"})

    if kind == "ignitions":
        required = {
            "event_id",
            "latitude",
            "longitude",
            "acq_datetime",
            "detections_in_event",
            "date",
        }
        issue("missing_repository_ignition_columns", len(required - set(frame.columns)))
        # Keep the acquisition instant in the duplicate key, not just its calendar day.
        adapted = adapted.rename(
            columns={
                "date": "event_day",
                "acq_datetime": "date",
                "latitude": "lat",
                "longitude": "lon",
            }
        )
        if "event_id" in frame:
            issue("duplicate_event_ids", frame.event_id.astype(str).str.strip().duplicated().sum())
            issue(
                "missing_event_ids",
                (frame.event_id.isna() | frame.event_id.astype(str).str.strip().eq("")).sum(),
            )
        if "detections_in_event" in frame:
            counts = pd.to_numeric(frame.detections_in_event, errors="coerce")
            issue("invalid_detection_counts", (~(counts.ge(1) & counts.mod(1).eq(0))).sum())
        if {"date", "acq_datetime"}.issubset(frame.columns):
            days = pd.to_datetime(frame.date, errors="coerce", utc=True, format="mixed")
            instants = pd.to_datetime(frame.acq_datetime, errors="coerce", utc=True, format="mixed")
            issue(
                "event_day_not_utc_acquisition_day",
                (days.isna() | instants.isna() | days.ne(instants.dt.normalize())).sum(),
            )
    elif kind in {"weather", "forecast"} and grid is not None:
        grid = grid.rename(columns={"centroid_lat": "lat", "centroid_lon": "lon"}).copy()
        if not {"cell_id", "lat", "lon"}.issubset(grid.columns) or grid.columns.duplicated().any():
            raise ValueError("grid requires cell_id and unambiguous WGS84 centre coordinates")
        grid["cell_id"] = grid.cell_id.astype(str).str.strip()
        if (
            grid.cell_id.duplicated().any()
            or grid.cell_id.eq("").any()
            or grid.cell_id.eq("nan").any()
        ):
            raise ValueError("grid cell IDs must be present and unique")
        west, south, east, north = bbox
        lat = pd.to_numeric(grid.lat, errors="coerce")
        lon = pd.to_numeric(grid.lon, errors="coerce")
        issue(
            "grid_centres_outside_study_box_or_invalid",
            (~(lat.between(south, north) & lon.between(west, east))).sum(),
        )
        if "cell_id" in adapted:
            adapted["cell_id"] = adapted.cell_id.astype(str).str.strip()
            issue("unknown_cell_ids", (~adapted.cell_id.isin(grid.cell_id)).sum())
            if kind == "weather" and not {"lat", "lon"}.issubset(adapted.columns):
                adapted = adapted.drop(columns=[c for c in ("lat", "lon") if c in adapted])
                adapted = adapted.merge(
                    grid[["cell_id", "lat", "lon"]],
                    on="cell_id",
                    how="left",
                    validate="many_to_one",
                )
    result = check_frame(
        adapted,
        kind,
        bbox,
        weather_features=features,
        start=start,
        end=end,
        date_timezone=date_timezone,
    )
    result["source_columns"] = list(frame.columns)
    result["schema_adapter"] = "repository-main-utc"
    result["issues"].extend(extra)
    result["passed"] = result["passed"] and not extra
    return result
