"""Explicit expected cell/day coverage; never infer or repair a run's population."""

from __future__ import annotations

from datetime import date

import pandas as pd


def check_cell_day_coverage(frame, grid, *, start, end):
    """Compare unique valid daily keys to a caller-supplied grid and inclusive dates.

    This checks key presence, not feature validity, geography policy or provenance.
    The Cartesian product is counted without allocating it. Only counts are returned.
    """
    if start is None or end is None:
        raise ValueError("complete cell/day coverage requires explicit start and end")
    first, last = date.fromisoformat(str(start)), date.fromisoformat(str(end))
    if first > last:
        raise ValueError("start must be on or before end")
    if frame.columns.duplicated().any() or grid.columns.duplicated().any():
        raise ValueError("coverage inputs require unambiguous column names")
    if not {"cell_id", "date"}.issubset(frame.columns) or "cell_id" not in grid:
        raise ValueError("coverage requires table cell_id/date and grid cell_id")
    cells = grid.cell_id.astype(str).str.strip()
    invalid_ids = grid.cell_id.isna() | cells.isin(["", "nan", "NaN", "None", "null", "<NA>"])
    if cells.empty or invalid_ids.any() or cells.duplicated().any():
        raise ValueError("coverage grid must have nonempty, present, unique cell IDs")

    values = frame.date
    if pd.api.types.is_datetime64_any_dtype(values):
        if values.dt.tz is None and values.eq(values.dt.normalize()).all():
            text = values.dt.strftime("%Y-%m-%d")
        else:
            text = values.map(lambda value: value.isoformat() if pd.notna(value) else "")
    else:
        text = values.astype(str)
    valid_format = text.str.fullmatch(r"\d{4}-\d{2}-\d{2}").fillna(False)
    days = pd.to_datetime(text.where(valid_format), format="%Y-%m-%d", errors="coerce")
    ids = frame.cell_id.astype(str).str.strip()
    in_grid = frame.cell_id.notna() & ids.isin(cells)
    in_window = days.between(pd.Timestamp(first), pd.Timestamp(last))
    # Unknown cells, bad dates and out-of-window rows cannot fill a missing pair.
    pairs = pd.DataFrame({"cell_id": ids, "date": days})[in_grid & in_window].drop_duplicates()
    expected_days = (last - first).days + 1
    expected_pairs = len(cells) * expected_days
    counts = {
        "expected_cells": len(cells),
        "expected_days": expected_days,
        "expected_cell_days": expected_pairs,
        "observed_unique_expected_cell_days": len(pairs),
        "missing_cell_days": expected_pairs - len(pairs),
        "cells_absent_entire_window": len(cells) - pairs.cell_id.nunique(),
        "dates_absent_all_expected_cells": expected_days - pairs.date.nunique(),
        "duplicate_valid_pair_rows": int((in_grid & in_window).sum()) - len(pairs),
        "unknown_or_missing_cell_rows": int((~in_grid).sum()),
        "invalid_daily_date_rows": int(days.isna().sum()),
        "out_of_window_rows": int((days.notna() & ~in_window).sum()),
    }
    issues = [
        {"code": f"coverage_{name}", "count": int(counts[name]), "severity": "error"}
        for name in (
            "missing_cell_days",
            "duplicate_valid_pair_rows",
            "unknown_or_missing_cell_rows",
            "invalid_daily_date_rows",
            "out_of_window_rows",
        )
        if counts[name]
    ]
    return {
        "start": first.isoformat(),
        "end": last.isoformat(),
        "basis": "supplied grid IDs x inclusive literal daily date keys; no inferred population",
        **{name: int(value) for name, value in counts.items()},
        "passed": not issues,
        "issues": issues,
    }
