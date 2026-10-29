# Progress check after the real-run updates

**Historical checkpoint; superseded for input receipt by the [30 October measured audit](Real_Data_Quality_Status.md).**

Checked 29 October 2026 (Perth), after upstream main reached **cc00735a5d3ed51d24f0538905afc8561022a9d4**.

## What changed

| Item | Evidence found | What it establishes |
|---|---|---|
| FS-21 real labels | Jira Done; [commit f1a37ea](https://github.com/asaduzzamanayon01/firesight/commit/f1a37ea28fda968eb546c564e9c864714fe11c92) reports 2019–2025 and 0.0817% positive rate | Ayon reports completion; actual files and counts still need independent checking. |
| FS-22 real weather | Jira Done; merged PRs #10 / #12 | Ayon reports weather join and missing-value checks; no weather file / manifest was attached to the issue. |
| FS-23 real model run | Jira Done; [PR #11](https://github.com/asaduzzamanayon01/firesight/pull/11) and [commit 6d4c68c](https://github.com/asaduzzamanayon01/firesight/commit/6d4c68c44a537cb014ec11883dc008f7dc1b81f6) | Reports LightGBM PR-AUC 0.0021 vs climatology 0.0064: baseline wins. PR #11 changes zero files and refers to a local results_real directory. These are author-reported values, not reproduced results. |
| FS-24 forecast | Jira Done; [PR #13](https://github.com/asaduzzamanayon01/firesight/pull/13) fixes calibrator loading | Export-related code is updated; forecast.csv itself was not obtained. |
| Sa-ad geography | [PR #3](https://github.com/asaduzzamanayon01/firesight/pull/3) is merged; firesight-geo is now in main | Earlier statements that it was open are superseded. Presence in main does not establish which grid the real run used. |
| Season configuration | Main now uses start_year=2019 and end_year=2025 | Configured period matches the intended six July–June seasons; actual coverage still requires source / output evidence. |
| FIRMS seasonal workflow | Main now uses 5-day requests and raises if any window fails | Earlier warnings about 10-day chunks and silently accepting failed windows are superseded. Credential-safe error handling / manifests still need review. |

## Why FS-37 is still waiting

FS-21–FS-24 each have no Jira attachment, description or comment at this check. Latest tracked data/raw and data/processed still contain only .gitkeep. No input / result download link was found in the real-run PR #11 description. A local results_real directory named in a commit message does not make its files available to reviewers.

Please provide accessible links or Jira attachments for:

- Actual ignition events and their source / acquisition manifests.
- weather.parquet, its manifest, units, timezone and KBDI derivation.
- forecast.csv, actual grid / cell IDs and export provenance.
- Exact run revision, date coverage, per-season counts and missingness / failure logs.
- results_real metrics / plots and the evaluation / calibration split explanation.

Keep API keys out of shared files. Yian can then run the existing validator and complete measured FS-37 statistics. Do not copy the reported 0.0817% or PR-AUC figures into a verified data-quality summary.

## Branch integration and verification

The delivery branch integrates cc00735, preserving the upstream removal of .env.example. Root setup instructions use an environment variable instead of referencing that removed file.

Five lint findings introduced with firesight-geo were corrected: import ordering, the collections.abc Iterator import and warning stacklevel. No grid / event definition was changed.

- Root suite: **83 tests passed in 4.42 s**.
- Geography suite: **10 tests passed in 5.73 s**, using real pyproj 3.8.0 rather than its approximate fallback.
- **ruff check . passed**.
- These are separate test commands. Hosted CI currently runs the root suite; do not claim its run also executed the ten geography tests.
- No live API download, real-data validation or model training was performed in this check.

[Root test log](progress-root-tests.txt), [geography test log](progress-geo-tests.txt), [lint log](progress-lint.txt). Check [branch Actions](https://github.com/YIAN-WANG-W/firesight/actions) and [PR #7](https://github.com/asaduzzamanayon01/firesight/pull/7) for the latest hosted result and review / merge state.
