# FireSight: team responsibilities and handoff

Based on the 8-page final-delivery plan read from the authorized WhatsApp conversation and repository / Jira inspection on 29 October 2026, refreshed against upstream main 41584f9 during PR preparation. **Responsibilities are planned outputs, not proof of completion.** Internal deadlines use Perth time; Tabib must verify official Blackboard requirements.

## Latest follow-up after PR 15

[Current spatial update](Spatial_Update_2026-10-30.md): main a86e39b adds results_real evidence and a static-cell filter. Filtered counts independently match the CSVs (1,573 cells, 2,684 positive cell-days); aggregate means favour spatial LightGBM, with evaluation/provenance review limits retained. Sa-ad's FS-30/32/33 and new FS-52/53/54 are Done; his FS-32 comment confirms evaluation draft/review and pending final integration. His FS-33 comment records 24-hour real clustering. Actual forecast, edge/day policy and matching spatial-run evidence remain open. **S1/S2/S3 now correspond to FS-52/53/54**, respectively; do not infer authentic sprint artefacts solely from Done status.

Sa-ad's [PR #14](https://github.com/asaduzzamanayon01/firesight/pull/14) is open with grid/label verification and protocol drafts; its two expected-failure examples document 24-hour clustering limits. Edge overshoot is intentional in that draft. Review/adoption remains pending; this delivery does not merge another member's PR or alter the clustering window.

## Earlier received-file checkpoint

**30 October update:** Six seasonal event files and five weather JSON batches have arrived from Victor. [Measured audit and owners](Real_Data_Quality_Status.md) supersedes earlier waiting-for-files statements. Responsibilities below are preserved from the plan.

| Member | Verified handoff | Next action |
|---|---|---|
| Ayon | 2,846 supplied event rows and 56 complete raw weather point series now inspected; main label proportion reproduced as 0.08174024% | Supply forecast, actual processed weather/grid, original manifests, exact run revision and result artefacts |
| Sa-ad | Geography PR #3 merged; 10 separate tests passed with pyproj | Agree boundary/edge-cell and UTC/Perth-day contract with Ayon; resolve 35 reconstructed main-grid centres outside bbox |
| Yian | Catalogue/checker plus actual received-file measurements, report and slide updated | Validate remaining artefacts and agreed contract; obtain review/merge, integrate with Tabib and rehearse |
| Tabib | Refreshed editable report/slide and notes available in this folder | Integrate/review whole submission, confirm official requirements and coordinate timing |
| Zarif | Dashboard export contract documented | Obtain forecast.csv, integrate historical backtest and retain offline demo/rehearsal evidence |

The author's reported model PR-AUC remains unverified; no model result was reproduced in this data audit. Missing evidence here does not establish that a teammate has done no work elsewhere.

## Ayon — ML, real data and code

| Plan / Jira | Required output | Internal deadline |
|---|---|---|
| A1 / FS-19 | Supplied scripts / patches, CI, lint, plan target 40 tests, second-person review / merge | 29 Oct 12:00 |
| A2 / FS-20 | Rerun synthetic pipeline and compare_models --sample 200000; retain results | 29 Oct 18:00 |
| A3 / FS-21 | Local FIRMS key, six real label seasons, counts and positive rate | 30 Oct 09:00 |
| A4 / FS-22 | Real Open-Meteo weather file and missingness record | 30 Oct 12:00 |
| A5 / FS-23 | Real baseline, LightGBM, calibration, SHAP and saved results | 30 Oct 18:00 |
| A6 / FS-24 | Dashboard forecast.csv: sample first, real version after real run | Sample 29 Oct 21:00; real Friday evening |
| A7 / FS-25 | Optional additional horizons after A5 | 31 Oct 09:00 |
| A8 / FS-26 | README, merged PRs, green CI and v1.0 freeze | 31 Oct 12:00 |
| A9 / FS-27 | Methodology, Results, Testing, Limitations and Contributions | 31 Oct 18:00 |
| A10 / FS-28 | Model / results slides, demo support and backup computer | 31 Oct 18:00 |
| A11 / FS-29 | Submit code and retain receipt | 1 Nov 10:00 |

Feature lags of 1 / 2 / 3 days do not themselves validate 24 / 48 / 72-hour targets. Define target intervals, prediction origin and feature availability.

## Sa-ad — Scrum Master, geography and evaluation

FS-30–FS-34 cover daily checks, evidence, evaluation, grid/literature and sprint review. The new FS-52/53/54 cover S1/S2/S3, so all eight responsibilities are now mapped.

| Plan | Required output | Internal deadline |
|---|---|---|
| S1 / FS-52 | Jira administration and Scrum Master handover | 29 Oct 10:00 |
| S2 / FS-53 | Restore board from real evidence; close Sprint 1 without inventing history | 29 Oct 14:00 |
| S3 / FS-54 | Epics, tickets, owners, dates, points and Sprint 2 start | 29 Oct 18:00 |
| S4 | Friday / Saturday standups and daily updates | Daily |
| S5 | Board, burndown, sprint report, CSV and merged-PR evidence to Zarif | 31 Oct 12:00 |
| S6 | PR-AUC, Brier, reliability and leave-one-season-out evaluation material | 30 Oct 18:00 |
| S7 | Grid, labels / leakage conventions and literature | 30 Oct 18:00 |
| S8 | Sprint 2 closeout and retrospective evidence | 1 Nov 14:00 |

## Yian — data and pipeline

| Plan / Jira | Required output | Internal deadline |
|---|---|---|
| Y1 / FS-35 | FIRMS / Open-Meteo catalogue, licence / attribution and run provenance | 29 Oct 21:00 |
| Y2 / FS-36 | Ignition / weather / forecast schema, duplicate, time, bounds and missingness checks plus tests | 30 Oct 18:00 |
| Y3 / FS-37 | Measured real event counts, missingness, coverage and known issues | 30 Oct 21:00 |
| Y4 / FS-38 | Data pipeline, management and implemented security / privacy report sections | 31 Oct 12:00 |
| Y5 / FS-39 | Data slide, script and rehearsal | 31 Oct; no hour specified |

Yian owns traceability and checks. Ayon / Sa-ad supply model results; Tabib coordinates report and submission. [Delivery index](README.md).

## Tabib — report, presentation and submission

| Plan / Jira | Required output | Internal deadline |
|---|---|---|
| T1 / FS-40 | Confirm Blackboard deadline, word / format limits, Turnitin / GenAI rules, presentation slot and earlier claims | 29 Oct 10:00 |
| T2 / FS-41 | Shared report outline, owners and word allocation | 29 Oct 18:00 |
| T3 / FS-42 | Factual ethics, SDGs, Indigenous / stakeholder considerations | 30 Oct 18:00 |
| T4 / FS-43 | Introduction, Conclusion and Chicago 17 references | 31 Oct 12:00 |
| T5 / FS-44 | Integrate, proofread and reconcile full report | 31 Oct 20:00 |
| T6 / FS-45 | Integrate slides; agree structure and timing | 31 Oct 18:00 |
| T7 / FS-46 | Submit report / presentation and retain receipts | 1 Nov 10:00 |

## Zarif — dashboard, demo, risk and management

| Plan / Jira | Required output | Internal deadline |
|---|---|---|
| Z1 / FS-47 | Integrate forecast.csv: map, date, probability and actual; label historical backtest / decision support | 30 Oct 21:00 |
| Z2 / FS-48 | Offline three-minute demo, runbook and backup recording | 31 Oct 12:00 |
| Z3 / FS-49 | Risk register and responses | 30 Oct 18:00 |
| Z4 / FS-50 | Dashboard, Innovation / Significance, Sustainability and Project Management sections | 31 Oct 18:00 |
| Z5 / FS-51 | Demo slides, script and at least two rehearsals | 31 Oct |

## Shared milestones

29 Oct 20:00 standup → 30 Oct 12:00 real-data decision gate → 31 Oct 12:00 freeze → 18:00 slides → 19:00 rehearsal → 20:00 report → 1 Nov 08:00 final read → 10:00 target uploads / receipts. Presentation from the week of 2 November follows the official allocation.

## Resolve these dependencies first

1. **Ayon + Sa-ad: one data contract.** Main bbox: 115.45,-32.60,116.55,-31.40; PR #3: 115.65,-32.60,116.30,-31.60. Main uses UTC days and 1.5 km / 24-hour clustering; PR #3 uses Perth days and 2 km / 2 days. Inspected main grid: 1,575 centres, 35 outside configured bbox. Agree boundaries, CRS, dates and grid IDs.
2. **Ayon: real evidence and valid evaluation.** Inspected raw / processed directories contained only .gitkeep. Supply ignition, weather, forecast, grid, manifests, intervals, units and revision. Confirm six-season coverage against configured dates. Latest main separates early-stopping validation from the held-out season; preserve and review this fix, and document independent calibration evaluation before reporting real results.
3. **Ayon: remaining ingestion / CI.** This PR corrects src/ingest/download_firms.py. Separate firms_client.py now uses five-day requests and rejects failed windows; source manifests and credential-safe errors still need review. Missing downloads are not zero-fire periods. Latest main now includes CI and weather / forecast scripts. Their presence does not establish successful hosted CI or a real run; obtain logs and actual output files.
4. **Yian: review now, measurements next.** Deliver FS-35 / 36 / 38 / 39 now. After real inputs arrive, run checks, separately verify expected cell-day / seasonal coverage, publish FS-37 measurements and update report / slide.
5. **Plan author / Ayon + Tabib: complete requirements.** PDF was read page by page but could not be saved. It jumps from Section 4 to Section 6 while referring to Section 5, a real-data gate and supplied scripts / patches. Those materials were not obtained. Confirm gate and official rules before final scope / submission decisions.

Old FS-5 / FS-6 screenshots concern earlier completed tickets; they do not complete FS-35 / FS-36. Latest WhatsApp Jira.csv is management evidence for Zarif. Use FS keys in commits; mark Done only when acceptance evidence exists.

Latest refresh: the earlier absence of CI / weather / forecast code applied to ad480505 only. Main 41584f9 adds those implementations and fixes the held-out early-stopping split. The delivery branch preserves these updates. See [latest integration evidence](Latest_Integration_Status.md); earlier archived snapshots are historical.
