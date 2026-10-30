# FS-36 / FS-37: explicit expected cell/day coverage

Yian Wang · 30 October 2026 (Perth) · follow-up after 7b66a46 · [PR #7](https://github.com/asaduzzamanayon01/firesight/pull/7)

## What this adds

Ordinary date-range checks only reject supplied rows outside the requested period. They can pass a file missing an entire date or grid cell. The new **--require-complete-cell-days** option compares unique valid `(cell_id, date)` pairs against the **explicit supplied grid × inclusive start/end dates**. It reports missing pairs, whole missing cells and whole missing dates. Duplicates and unrelated/invalid rows cannot hide gaps. Inputs are never repaired or overwritten.

The option requires **--grid, --start, --end** and at least one weather/forecast input. It supports repository and canonical schemas after the existing column mapping. It does not apply a dense daily requirement to sparse ignition events. Coverage failure returns exit 1; missing coverage prerequisites return 2. Default validation remains unchanged. JSON and Markdown both record the counts and supplied grid hash; forecast grid hashes are now recorded too.

Use the [full instructions and example command](../data-quality.md#require-an-explicit-complete-daily-population). Select the actual approved run population and exact date window. A filtered 1,573-cell output must not be tested against an unfiltered 1,575-cell grid. Different weather/forecast windows need separate invocations. Neither exclusions nor calendar/edge policies are inferred by this option.

## Measured check of locally reconstructed weather

[Machine-readable evidence and input hashes](Cell_Day_Coverage_Audit_2026-10-30.json).

| Check | Measured result |
|---|---:|
| Supplied reconstructed grid | 1,575 unique cells |
| Inclusive daily window | 2019-07-01 to 2025-06-30; 2,192 days |
| Expected cell/day pairs | 3,452,400 |
| Observed unique expected pairs | 3,452,400 |
| Missing pairs / whole missing cells / whole missing dates | 0 / 0 / 0 |
| Duplicate valid pairs / unknown cells / invalid dates / outside-window rows | 0 / 0 / 0 / 0 |
| Key-coverage result | PASS |
| Overall weather acceptance | **Pending/failed strict bounds: 35 edge centres / 76,720 rows** |

This is the **unfiltered locally reconstructed weather**, derived in the original received-data audit. It is not Ayon's actual processed model-run export. Raw files and their reconstruction remain local; only aggregate evidence and hashes are published. Feature and grid bounds are separate checks: this key-coverage pass does not relax the preserved boundary failure or establish original acquisition completeness.

To reproduce the key-only measurement after reconstructing the original weather/grid using the [received-data audit](Real_Data_Quality_Status.md):

```python
import json
import pandas as pd
from src.quality.coverage import check_cell_day_coverage

weather = pd.read_parquet("audit/weather_reconstructed.parquet", columns=["cell_id", "date"])
grid = pd.read_csv("audit/grid_reconstructed.csv", dtype={"cell_id": str})
result = check_cell_day_coverage(weather, grid, start="2019-07-01", end="2025-06-30")
print(json.dumps(result, indent=2))
```

Replace the two local paths. Match input SHA256 values to the linked JSON before comparing counts. The helper checks daily keys only; the normal CLI adds the existing feature/coordinate checks.

## Verification and what remains

**120 local root tests + 6 subtests passed; Ruff passed.** The 25 new regression cases include a whole missing day, whole missing cell, duplicate rows replacing a missing pair, unknown/missing IDs, out-of-window or malformed dates, empty/invalid grids, explicit filtered populations, unchanged source frames and opt-in CLI/report behavior. See [branch Actions](https://github.com/YIAN-WANG-W/firesight/actions) and PR #7 for hosted CI on the exact published revision. Earlier c72d464's 95-test hosted run is historical evidence for that revision, not this count.

No new teammate artefacts were found in the Jira/upstream-main check immediately before this follow-up; main remains a86e39b. The **2026-10-30_Spatial Word/PPT/notes and model summary statistics remain current**. This checker addendum does not claim a new model run or prediction-level metric reproduction.

Next owners remain: **Ayon** supplies forecast.csv, held-out predictions, actual processed run weather/grid, manifests and matching spatial-run record/hashes; **Ayon/Sa-ad** agree edge/day/event rules and review label-derived selection/inner-validation separation; **Yian** applies final checks to that approved actual export; **Tabib** integrates/reviews report and deck; **Yian/team** rehearse. FS-35–FS-39 stay In Progress while acceptance/review/integration/rehearsal is open. PR #7 is ready for review, not merged.
