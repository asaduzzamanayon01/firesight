# Spatial model update and label reconciliation

Checked 30 October 2026 (Perth). This follow-up supersedes earlier statements that results_real files are unavailable or that the earlier weather-only model comparison is the latest result. The original received-file audit remains valid for the unfiltered inputs.

## New upstream evidence

[PR #15](https://github.com/asaduzzamanayon01/firesight/pull/15) is merged at **a86e39b62df5a7237e47e2ef9724ef8c10fef06e**, after cc00735. It adds spatial/recent-activity features, a static-source filter, a risk_percentile export field and tracked results_real CSV/plot files. The delivery branch retains these upstream changes. No forecast.csv or original acquisition manifests are tracked in that snapshot.

The new upstream [CI run](https://github.com/asaduzzamanayon01/firesight/actions/runs/40915755039/job/123595400476) failed collecting tests because the bare pytest entry point did not find src/scripts. The delivery workflow changes that command to python -m pytest, retains the upstream Python 3.11 lint/test/synthetic-baseline smoke steps, and checks fork branch pushes too. Local root suite: **95 passed with 6 subtests**; geography suite: **10 passed separately**; Ruff passed. Hosted status must be checked in [branch Actions](https://github.com/YIAN-WANG-W/firesight/actions); a local pass is not a hosted smoke-test result.

## Received labels independently reconciled with published counts

| Population | Cells | Cell-days | Positive cell-days | Positive rate |
|---|---:|---:|---:|---:|
| Original received labels / old audit | 1,575 | 3,452,400 | 2,822 | 0.08174024% |
| Current main after static-source filter | 1,573 | 3,448,016 | 2,684 | 0.07784187% |

Invoking the new build/drop_static_sources functions on the six received event files independently reproduces exclusion of cells **570 (99 positive days)** and **571 (39)**. The 138 excluded positive days and each season's remaining row/positive counts exactly match the supplied static_cells.csv, baseline_cv.csv and lgbm_cv_spatial.csv. The original 2,846 event-file rows and their structural checks are unchanged. Do not mix event counts, unfiltered cell-days and filtered model counts.

| Published CSV evidence, arithmetic checked | Result |
|---|---:|
| Six-season mean PR-AUC, spatial LightGBM | 0.01022567 |
| Six-season mean PR-AUC, paired filtered climatology | 0.00426083 |
| Seasons spatial model exceeds its paired baseline | 6 of 6 |
| Top 5% daily cells, weighted positive-day capture | 861 / 2,684 = 32.07899% |
| Top 10% daily cells, weighted positive-day capture | 1,223 / 2,684 = 45.56632% |
| Earlier weather-only mean PR-AUC | 0.00213001, on the unfiltered population |

These means/capture fractions are recalculated from the published aggregate CSVs, **not predictions or a new training run**. The baseline and spatial CSVs use matching season counts; the older weather-only CSV uses a different population. Do not present weather-only versus spatial as a controlled feature-only comparison. See [audit JSON with source hashes](Spatial_Update_Audit_2026-10-30.json) and [offline reconciliation script](../../scripts/audit_spatial_update.py). Relevant upstream inputs: [results_real](../../results_real/).

## Remaining model and provenance limits

- The supplied mlflow_runs_REAL_only.csv contains one earlier weather-only run, mean PR-AUC 0.00213001 and source revision fae5ba35. It does not document the new 0.01022567 spatial run; request its matching run record and input hashes.
- The static mask is selected using all six seasons' ignition labels before LOSO. A fixed numeric threshold does not make its selected cell set independent of held-out labels. This is a review limitation inferred from code. An independently defined mask or fold-specific sensitivity check is needed before claiming an unbiased generalisation score. This delivery documents the issue without changing the author's method or published metrics.
- Spatial priors are built before the inner early-stopping split. Fit-season priors may use the inner validation season's labels. Ayon/Sa-ad should review this separation before accepting the validation-based tree count.
- The original held-out predictions, actual processed weather/grid files, selected weather model, source manifests and forecast.csv remain unavailable. CSV arithmetic checks cannot establish full run reproducibility or calibrated probability quality.
- Current main grid construction is unchanged: excluding cells 570/571 does not resolve the 35 outside-bbox edge centres. UTC event-day versus Perth weather-day interpretation and retrospective feature availability remain open.

## Jira evidence now available

- [FS-32](https://asaduzzamanayon001.atlassian.net/browse/FS-32): Done. Sa-ad states the evaluation draft is written and checked against Ayon's results_real output; final report integration remains pending. This is his recorded review, not a new independent training run by Yian.
- [FS-33](https://asaduzzamanayon001.atlassian.net/browse/FS-33): Done. Sa-ad records 16 references, a 1,575-cell approximately 3 km grid and use of 24-hour clustering in real labels, reported as a limitation. This supports the main-style grid/cluster account but does not settle edge centres or the day convention.
- [FS-30](https://asaduzzamanayon001.atlassian.net/browse/FS-30): Done. Stand-up routine and board update recorded; Saturday check remains future work.
- New [FS-52](https://asaduzzamanayon001.atlassian.net/browse/FS-52), [FS-53](https://asaduzzamanayon001.atlassian.net/browse/FS-53), [FS-54](https://asaduzzamanayon001.atlassian.net/browse/FS-54) are marked Done for Jira takeover, recovery and Sprint 2 setup. No supporting attachment/description was present on those three issues at this check; do not invent board-history evidence from the statuses.

## Sa-ad PR 14 remains a separate review

[PR #14](https://github.com/asaduzzamanayon01/firesight/pull/14), head 0331602, is open with two successful checks. It documents main's intentional boundary overshoot for full bbox coverage; this is useful rationale, while adoption of an edge-cell acceptance rule remains pending. It also documents 24-hour clustering splitting example spreading fires and proposes 48 hours for Ayon's decision. A separate run of its proposed label/grid test file against this candidate gives **7 passed / 2 expected failures**. These tests are not merged into this delivery or counted in the 95 root tests. PR #3 is merged; PR #14 is a different pending follow-up. Its draft protocol contains earlier population and unavailable-results statements, which must be reconciled with the current filtered audit before report integration.

## Next owners

**Ayon / Sa-ad:** review static-mask/inner-validation separation and grid/day policy; share the matching spatial run record, prediction/forecast artefacts and provenance. **Yian:** validate the new risk_percentile values when the actual export arrives and reconcile any regenerated counts. **Tabib:** use the refreshed Word/slide and preserve population/evidence limits. **Zarif:** use probability for probabilities and risk_percentile for relative daily display rank; percentiles are not calibrated ignition probabilities. **Whole team:** review PR #7 before merge and rehearse the integrated presentation.

No task is automatically marked Done and no group messages are sent. New evidence is reflected in the current index and Jira; unavailable inputs remain an explicit handoff dependency.
