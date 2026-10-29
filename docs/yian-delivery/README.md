# Yian’s delivery: files, evidence and remaining work

**Owner:** Yian Wang · **Updated:** 29 October 2026 (Perth) · **Scope:** FS-35–FS-39 · **PR:** [#7](https://github.com/asaduzzamanayon01/firesight/pull/7)

Catalogue, checker, tests, report and presentation materials are available for team review. **Real-data statistics remain pending.** Publication on the delivery branch does not mean review or merge into upstream main is complete.

## Latest progress check

Ayon’s FS-21–FS-24 are now Done, and Sa-ad’s PR #3 is merged. The delivery branch integrates main cc00735. **Actual real-run files are still not accessible in the inspected sources**, so FS-37 remains waiting for the handoff. See the [new checkpoint](Progress_Check_2026-10-29.md), including author-reported model results and the 83 + 10 separately executed tests.

## Start here

- **Ayon / Sa-ad:** review the [integration instructions](../data-quality.md), code and tests.
- **Tabib:** use the editable [Word report](Yian_Report_Sections.docx), [Markdown report](Yian_Report_Sections.md), [PowerPoint slide](Yian_Data_Slide.pptx) and [speaker notes](Speaker_Notes.txt).
- **Whole team:** see [everyone’s responsibilities and handoff order](TEAM_HANDOFF.md).
- **Offline copy:** [complete archive](FireSight_Yian_Final_Delivery_2026-10-29.zip). It preserves the original local evidence snapshot; this index and Jira record current publication status.

**Hosted CI:** [passed on code revision 61851c4](https://github.com/YIAN-WANG-W/firesight/actions/runs/40873721046), Python 3.10. PR #7 has no merge conflicts; review and upstream merge remain pending.

## Five deliverables

| Task | Delivered files | Present state | Remaining work |
|---|---|---|---|
| [FS-35 · Catalogue](https://asaduzzamanayon001.atlassian.net/browse/FS-35) | [Catalogue](../data-sources.md), [source-record template](../source-record.template.json) | Prepared; catalogue attached in Jira. | Ayon supplies acquisition manifests, products, dates and units; Yian completes run provenance. |
| [FS-36 · Quality checks](https://asaduzzamanayon001.atlassian.net/browse/FS-36) | [Instructions](../data-quality.md), [CLI](../../scripts/check_data_quality.py), [module](../../src/quality) and tests | Implemented for repository schemas, CSV and Parquet; **83 local tests passed after upstream refresh**. Archive attached in Jira. | Second-person review and upstream merge; agree conventions with PR #3 before the real run. |
| [FS-37 · Real-data summary](https://asaduzzamanayon001.atlassian.net/browse/FS-37) | [Required inputs / status](Real_Data_Quality_Status.md) | **Waiting for accessible real-run inputs; Ayon’s related tasks are now Done.** No real counts, missingness or seasonal coverage measured. | Ayon supplies ignition, weather, forecast, grid and manifests; Yian publishes measured results with hashes and revision. |
| [FS-38 · Report](https://asaduzzamanayon001.atlassian.net/browse/FS-38) | [Word](Yian_Report_Sections.docx), [Markdown](Yian_Report_Sections.md) | Editable contribution attached in Jira; Word layout inspected. | Tabib integrates / reviews; Yian adds FS-37 measurements. |
| [FS-39 · Presentation](https://asaduzzamanayon001.atlassian.net/browse/FS-39) | [PowerPoint](Yian_Data_Slide.pptx), [notes](Speaker_Notes.txt) | Editable slide / script attached in Jira; slide rendered and inspected. | Tabib integrates; Yian rehearses and joins team rehearsal. |

All five tasks remain **In Progress**. The repository’s Definition of Done requires review, CI and merge for code work. Fork CI has passed; second-person review and upstream merge remain. Commits include relevant FS keys; no automatic Done transition is requested while acceptance work remains.

## Verification

The table below records the earlier 41584f9 integration. For the cc00735 refresh, read the [current checkpoint and logs](Progress_Check_2026-10-29.md).

**Latest refresh:** upstream main 41584f9 now includes CI, weather / forecast scripts and a corrected inner validation split. These changes are retained in this branch; see [latest integration evidence](Latest_Integration_Status.md). Earlier archive statements about absent code describe the original ad480505 snapshot.

From the repository root after installing requirements.txt, run:

    python -m pytest
    ruff check src scripts tests

| Check | Observed result | Limit |
|---|---|---|
| Unmodified baseline ad480505 | 32 tests passed locally | Baseline result; do not add this to 75. |
| Earlier candidate on ad480505 | 75 tests passed locally | Historical result before upstream refresh. |
| Current combined candidate on 41584f9 | **83 tests passed locally** | Includes upstream and delivery tests; fixtures only. |
| Ruff: whole repository | Passed locally | Uses latest upstream configuration, excluding notebooks. Earlier snapshot had 8 notebook findings. |
| Real API / real-data validation / model training | Not performed | Production files and measured results were not obtained. |
| Hosted fork CI on 61851c4 | **Passed on Python 3.10** | Upstream PR Checks tab has no checks; review / merge remain pending. |

See [latest evidence](Latest_Integration_Status.md), [earlier test log](repository-tests.txt), [integration snapshot](Repository_Integration_Status.json) and [real-input commands / interpretation limits](../data-quality.md). Fixture counts are not real fire or weather statistics. The archive and snapshot were written before remote publication; their local-only status is historical.

## Handoff order

1. **Ayon + Sa-ad:** agree bbox, grid IDs / boundaries, UTC versus Perth event day and clustering. Main’s original pipeline and the now-merged [PR #3](https://github.com/asaduzzamanayon01/firesight/pull/3) differ. This delivery follows main’s UTC event-day contract.
2. **Ayon:** supply actual ignition, weather, forecast.csv, grid, manifests, extraction intervals / units and exact run revision. Keep credentials out of GitHub and Jira.
3. **Yian:** run non-mutating checks; separately confirm expected seasonal / cell-day coverage; publish FS-37 measurements and update report / slide.
4. **Tabib:** integrate contributions and verify official submission rules. **Zarif:** integrate the forecast and prepare the offline demo. **Sa-ad:** retain authentic sprint / review evidence.

The referenced Section 5 decision gate and supplied scripts / patches were not obtained. Confirm them before deciding final real-data versus synthetic-demo scope. WhatsApp’s Jira.csv is management evidence for Zarif, not a replacement for model inputs.
