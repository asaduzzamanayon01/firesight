# FireSight data quality summary

Data mode: **real** (caller declared).

This report counts supplied records. It does not establish model accuracy, provenance, or causal ignition locations.

| Table | Rows | Result |
|---|---:|---|
| forecast | 22022 | FAIL |

## forecast

Input SHA256: `59ec60508bfaa0d28c5ba884825c7fc5c25b7e67cababcfb1dcca4200969cecb`

Coverage: {"start_utc": "2025-01-10T00:00:00+00:00", "end_utc": "2025-01-23T00:00:00+00:00"}

Summary: {"positive_rows": 3, "invalid_label_rows": 0, "positive_rate_valid_labels": 0.0001362274089546817, "season_counts": {"2024-25": 22022}}

Expected cell/day coverage: **PASS**

Supplied grid: 1,573 cells; inclusive window: 2025-01-10 to 2025-01-23 (14 days).

Unique expected pairs observed: 22,022 / 22,022; missing pairs: 0; cells absent throughout: 0; dates absent across all expected cells: 0.

Grid SHA256: `ec5cf28a917afb4c0ffbab34ee9b89273aaa5bfb33235344d72197b7aeb99084`

Missing values by column:
- `cell_id`: 0
- `lat`: 0
- `lon`: 0
- `date`: 0
- `probability`: 0
- `actual`: 0
- `season`: 0
- `risk_percentile`: 0

Checks:
- error: coordinates_outside_study_box_or_invalid (490)
- error: grid_centres_outside_study_box_or_invalid (35)
