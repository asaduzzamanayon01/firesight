# Yian’s delivery and current handoff

Yian Wang · **Updated 30 October 2026 (Perth)** · FS-35–FS-39 · [Upstream PR #7](https://github.com/asaduzzamanayon01/firesight/pull/7)

**Current delivery:** measured source-file checks and filtered-label reconciliation are complete for the supplied material; report/slide/notes use the **2026-10-30_Spatial** version. The latest checker additionally detects missing expected cell/days and passes **120 local tests + 6 subtests** and lint; see [branch Actions](https://github.com/YIAN-WANG-W/firesight/actions) for exact-revision hosted CI. Full acceptance awaits forecast.csv, matching run provenance and agreed spatial/calendar-day/evaluation rules. PR #7 is open and awaits review/merge.

**Latest quality follow-up:** [expected cell/day coverage, measured evidence and usage](Cell_Day_Coverage_Update_2026-10-30.md). The locally reconstructed unfiltered weather has **3,452,400 / 3,452,400 unique expected pairs**, with no missing cell/days. Its strict boundary failure remains. This addendum extends FS-36/FS-37; the Spatial Word/PPT/notes and published model statistics remain current.

## Latest upstream follow-up

**PR #15 / main a86e39b is now integrated.** Read the [spatial update and remaining review gates](Spatial_Update_2026-10-30.md). Received-label reconstruction now also reproduces the filtered model population: **1,573 cells / 3,448,016 cell-days / 2,684 positives (0.07784187%)**, after excluding cells 570/571. The original input audit below remains the unfiltered population.

Published CSV arithmetic now supports spatial-model PR-AUC **0.01022567** versus paired filtered baseline **0.00426083**, with 6/6 seasonal wins and top-5% capture **32.08%**. Scores were not rederived from predictions or retraining. The supplied MLflow record still describes the older weather-only run. Source-selection and inner-validation review limitations remain explicit. Local code verification is now **95 root tests + 6 subtests**, **10 separate geography tests**, and lint passed; see current Actions for hosted status.

Use the **2026-10-30_Spatial** report, slide and notes attachments in Jira. Earlier same-day files precede this follow-up; standard online filenames below now point to the refreshed material.

## Current files for the team

- **Start with the [latest filtered-label checkpoint and next owners](Spatial_Update_2026-10-30.md).** [Filtered-label/CSV audit JSON](Spatial_Update_Audit_2026-10-30.json) · [reconciliation script](../../scripts/audit_spatial_update.py).
- **Original input evidence:** [received-file audit](Real_Data_Quality_Status.md), [detailed JSON and input hashes](Real_Data_Audit_2026-10-30.json), [archive receipt](Received_Archives_2026-10-30.json) and [original offline audit](../../scripts/audit_received_data.py). These retain the unfiltered population.
- **Tabib:** refreshed editable [Word](Yian_Report_Sections.docx), [Markdown](Yian_Report_Sections.md), [one-slide PowerPoint](Yian_Data_Slide.pptx) and [speaker notes](Speaker_Notes.txt).
- **Ayon / Sa-ad:** [catalogue](../data-sources.md), [quality module and run instructions](../data-quality.md), [whole-team responsibilities](TEAM_HANDOFF.md).
- **Actual-export acceptance:** use the [explicit coverage option](../data-quality.md#require-an-explicit-complete-daily-population) with the approved run grid and exact date window; [coverage audit JSON](Cell_Day_Coverage_Audit_2026-10-30.json) records only the locally reconstructed unfiltered population.
- **Historical evidence:** [29 October checkpoint](Progress_Check_2026-10-29.md), [earlier integration](Latest_Integration_Status.md), [original archive](FireSight_Yian_Final_Delivery_2026-10-29.zip). Their waiting-for-input statements are superseded by the measured report above.

## Measured receipt

| Evidence | Result |
|---|---|
| Six event tables, 2019–20 to 2024–25 | 2,846 rows; 0 required missing values; all six native checks pass |
| Grouped detections | 24,968, summed from supplied event counts; original detection rows absent |
| Original labels before filtering | 2,822 / 3,452,400 positive cell-days = 0.08174024%, over 1,575 cells |
| Latest filtered model population | 2,684 / 3,448,016 positive cell-days = 0.07784187%, over 1,573 cells |
| Five raw weather JSON batches | 56 points; full 2,557-day / 61,368-hour axes; 0 missing/nonfinite variable values |
| Locally reconstructed weather | 3,452,400 cell-days; 0 missing features; **FAIL: 35 outside-bbox centres / 76,720 rows** |
| Forecast / run-specific acceptance | **Pending**: no forecast.csv, original acquisition manifests or actual model-run grid/revision |

## Five deliverables and next owners

| Task | Current delivery | Remaining acceptance |
|---|---|---|
| [FS-35 Catalogue](https://asaduzzamanayon001.atlassian.net/browse/FS-35) | Source catalogue now records received fields, units, dates and archive hashes | Ayon supplies original acquisition manifests and selected weather model; Yian reconciles provenance |
| [FS-36 Checker](https://asaduzzamanayon001.atlassian.net/browse/FS-36) | Validator, risk_percentile checks, explicit expected cell/day coverage and reproducible audits; 120 local tests pass | Second-person review and upstream merge; approved grid/day policy |
| [FS-37 Real summary](https://asaduzzamanayon001.atlassian.net/browse/FS-37) | Actual received-file measurements complete; detailed failure/limits published | Validate forecast and actual run grid/weather, resolve policy and obtain run provenance |
| [FS-38 Report](https://asaduzzamanayon001.atlassian.net/browse/FS-38) | Word and Markdown updated with measured counts and limitations | Tabib integrates/reviews final report |
| [FS-39 Presentation](https://asaduzzamanayon001.atlassian.net/browse/FS-39) | Editable data slide and script updated with measurements and remaining gate | Tabib integrates; Yian and team rehearse |

Keep all five In Progress while their remaining acceptance work is open. Code publication is not upstream merge, and preparing a script is not a completed rehearsal. Commits use relevant FS keys without automatic Done commands.

## Code verification

**Latest coverage follow-up:** **120 local root tests + 6 subtests**, lint passed. The 25 added cases exercise missing populations, duplicate masking, invalid dates/IDs, filtered grid selection, no source mutation and the opt-in CLI/report behavior. Hosted results are revision-specific: [branch Actions](https://github.com/YIAN-WANG-W/firesight/actions) and PR #7 link the current run.

**Earlier code revision c72d464:** [hosted Python 3.11 CI passed](https://github.com/YIAN-WANG-W/firesight/actions/runs/40979703928), with **95 tests**, lint, synthetic data generation and baseline smoke. Local root tests also passed with six subtests; **10 geography tests passed separately with pyproj**. Sa-ad's pending PR #14 test file was checked separately: **7 passed / 2 expected failures** documenting clustering limits. Those separate checks are not added to the root-test count. Historical 83-test snapshots remain in the older checkpoint files.

The [quality report](Real_Data_Quality_Status.md) gives an offline reproduction command. Its audit process completing successfully does not override a table's failed validation or missing forecast. No new model run was performed and no original model-score reproduction is claimed.
