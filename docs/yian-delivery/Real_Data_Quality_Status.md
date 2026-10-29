# Y3 real data quality summary

Status on 29 October 2026: **awaiting Ayon's measured run inputs**. Do not submit fixture counts as real observations.

This corresponds to [FS-37](https://asaduzzamanayon001.atlassian.net/browse/FS-37), assigned to Yian and due 30 October. A read-only connector query of all 41 accessible FS issues at the initial check returned empty attachment lists, so Jira did not provide the required run files at the time checked.

| Required evidence | Current state |
|---|---|
| Actual processed ignition file and definition | Not available |
| Actual weather file and numeric predictor schema | File absent from inspected main; five configured field names are known, units and actual extraction remain unverified |
| Actual forecast.csv | Not available |
| Approved study bounding box, grid and source timezone | Main config and open PR #3 have conflicting bbox, event grouping and timezone conventions; final agreement and actual grid pending |
| Source manifests and actual extraction intervals | Not available |
| Real event counts, missingness and seasonal coverage | Not measured |

The runnable validator and Markdown summary writer are complete. Follow code/README.md when the inputs arrive. Its summary provides row counts, missing values, timestamp coverage, forecast positives and season counts. Supplement it with the expected cell/day count and source-specific event grouping definition. A valid quality pass does not detect missing entire days unless expected coverage is checked separately.

The demonstration under evidence/ uses three tiny, hand-authored test fixtures. It verifies execution only. It provides no empirical support for a real-data result.

Repository follow-up: authenticated Safari provided main snapshot ad480505e229fc118b6e8b1a1a9796c2d48bb550. Both data/raw and data/processed contain only .gitkeep. No production file was obtained. The adapted candidate passes 75 tests, including controlled Parquet fixtures. These results verify implementation, not real-data quality. See evidence/Repository_Integration_Status.md.
