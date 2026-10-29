# Yian’s delivery and current handoff

Yian Wang · **Updated 30 October 2026 (Perth)** · FS-35–FS-39 · [Upstream PR #7](https://github.com/asaduzzamanayon01/firesight/pull/7)

**Real inputs have arrived and the measured audit is published.** Six event tables pass structural checks. Raw weather is complete; locally reconstructed weather fails the current strict bbox rule at 35 grid centres. Full acceptance awaits forecast.csv, actual run provenance and an agreed grid/day policy. Review and upstream merge remain pending.

## Current files for the team

- **Start with the [measured quality report and next owners](Real_Data_Quality_Status.md).** [Detailed JSON and input hashes](Real_Data_Audit_2026-10-30.json) · [archive receipt](Received_Archives_2026-10-30.json) · [offline audit script](../../scripts/audit_received_data.py).
- **Tabib:** refreshed editable [Word](Yian_Report_Sections.docx), [Markdown](Yian_Report_Sections.md), [one-slide PowerPoint](Yian_Data_Slide.pptx) and [speaker notes](Speaker_Notes.txt).
- **Ayon / Sa-ad:** [catalogue](../data-sources.md), [quality module and run instructions](../data-quality.md), [whole-team responsibilities](TEAM_HANDOFF.md).
- **Historical evidence:** [29 October checkpoint](Progress_Check_2026-10-29.md), [earlier integration](Latest_Integration_Status.md), [original archive](FireSight_Yian_Final_Delivery_2026-10-29.zip). Their waiting-for-input statements are superseded by the measured report above.

## Measured receipt

| Evidence | Result |
|---|---|
| Six event tables, 2019–20 to 2024–25 | 2,846 rows; 0 required missing values; all six native checks pass |
| Grouped detections | 24,968, summed from supplied event counts; original detection rows absent |
| Current main labels | 2,822 / 3,452,400 positive cell-days = 0.08174024% |
| Five raw weather JSON batches | 56 points; full 2,557-day / 61,368-hour axes; 0 missing/nonfinite variable values |
| Locally reconstructed weather | 3,452,400 cell-days; 0 missing features; **FAIL: 35 outside-bbox centres / 76,720 rows** |
| Forecast / run-specific acceptance | **Pending**: no forecast.csv, original acquisition manifests or actual model-run grid/revision |

## Five deliverables and next owners

| Task | Current delivery | Remaining acceptance |
|---|---|---|
| [FS-35 Catalogue](https://asaduzzamanayon001.atlassian.net/browse/FS-35) | Source catalogue now records received fields, units, dates and archive hashes | Ayon supplies original acquisition manifests and selected weather model; Yian reconciles provenance |
| [FS-36 Checker](https://asaduzzamanayon001.atlassian.net/browse/FS-36) | Validator plus reproducible real-file audit; failing bounds remain visible | Second-person review, CI and upstream merge; approved grid/day policy |
| [FS-37 Real summary](https://asaduzzamanayon001.atlassian.net/browse/FS-37) | Actual received-file measurements complete; detailed failure/limits published | Validate forecast and actual run grid/weather, resolve policy and obtain run provenance |
| [FS-38 Report](https://asaduzzamanayon001.atlassian.net/browse/FS-38) | Word and Markdown updated with measured counts and limitations | Tabib integrates/reviews final report |
| [FS-39 Presentation](https://asaduzzamanayon001.atlassian.net/browse/FS-39) | Editable data slide and script updated with measurements and remaining gate | Tabib integrates; Yian and team rehearse |

Keep all five In Progress while their remaining acceptance work is open. Code publication is not upstream merge, and preparing a script is not a completed rehearsal. Commits use relevant FS keys without automatic Done commands.

## Code verification

The previous e555d2a candidate passed **83 root tests** and **10 geography tests separately with pyproj 3.8.0**; whole-repository Ruff passed. [Hosted fork CI on e555d2a passed](https://github.com/YIAN-WANG-W/firesight/actions/runs/40898477285) on Python 3.10, running the root suite only. These implementation tests are separate from the measured real-file audit. Check [branch Actions](https://github.com/YIAN-WANG-W/firesight/actions) for the newest documentation/audit commit result.

The [quality report](Real_Data_Quality_Status.md) gives an offline reproduction command. Its audit process completing successfully does not override a table's failed validation or missing forecast. No new model run was performed and no original model-score reproduction is claimed.
