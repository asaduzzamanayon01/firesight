# FireSight data catalogue

Maintainer: Yian Wang. Updated 30 October 2026. The [measured receipt and quality report](yian-delivery/Real_Data_Quality_Status.md) records six seasonal event tables and five raw weather JSON batches received from Victor. The original acquisition manifests, actual model-run grid/revision and forecast export remain unavailable. The table below records source requirements; this dated receipt supersedes earlier unavailable-file evidence notes.

| Source or artefact | Use | Provenance to retain | Licence and attribution | Evidence status |
|---|---|---|---|---|
| NASA FIRMS seasonal detections | Input observations for Ayon and Sa-ad's event/label construction | Exact product such as VIIRS_SNPP_SP, available dates, each request's start and end, study box, retrieval UTC, original filename, SHA256, parser revision, seasonal coverage | Retain NASA FIRMS provider/product acknowledgement and check the selected product's terms before redistribution. Do not assign an invented blanket CC licence to NASA products | Downloader corrected and tested offline. Six seasonal event tables received; original source detections/manifests and per-window completeness unverified |
| Open-Meteo Historical Weather API | Historical weather input to Ayon's processing | Endpoint, model selection, requested and returned coordinates, dates, timezone, daily/hourly variables, units, response metadata, retrieval UTC, SHA256, transformation revision | API data: CC BY 4.0. Credit Open-Meteo, link the licence, identify transformations, and retain relevant underlying dataset attribution. Data licence differs from API service terms | Source documentation verified. 56 raw response points supplied, with complete expected date axes and 0 missing/nonfinite variables; no original processed weather.parquet supplied |
| Processed ignition table | Quality input, before modelling | Parent FIRMS manifests, detection filters, event grouping, dates/timezone, grid assignment and label rule | Inherits source conditions. The supplied events are not independently verified ignition causes | Repository adapter checks event_id, latitude, longitude, acq_datetime, detections_in_event and date. Acquisition instants are treated as UTC; the daily date must match the UTC day |
| Processed weather table | Quality input, before feature joining | Parent response manifests, cell/date keys, aggregation rule and native units, output SHA256 | Retain Open-Meteo and upstream attribution after aggregation | Defaults read config/config.yaml: t2m_max, rh_min, wind_speed_max, precip_24h, kbdi. Response units inspected: °C, m/s, mm and %. Existing simplified KBDI code reused offline; reconstruction is not the original model-run table |
| Analysis grid | Coordinates for weather rows lacking lat/lon | Approved boundary, metric CRS used to construct 3 km cells, grid revision, unique cell IDs and WGS84 centres | Record the boundary dataset's actual licence | Main bbox: 115.45,-32.60,116.55,-31.40; nominal 3 km and EPSG:7850. Main uses approximate lon/lat bins; PR #3 proposes a metric grid with different bbox and local dates. Final grid not agreed |
| forecast.csv | Historical dashboard backtest | Source run ID, model revision, data mode, period, input hashes and export revision | Retain source notices and describe model-derived probabilities | Team plan fixes cell_id, lat, lon, date, probability, actual, season |

## FIRMS date handling

The NASA Area API interprets DATE as the **first** day. The corrected helper retains the legacy `--end-date` interface, calculates `start_date = end_date - (days - 1)`, and records both dates. Official documentation currently lists 1 to 5 days per request. For seasonal extraction, use consecutive non-overlapping chunks, check product availability, and retain a manifest for each chunk. A missing file, service error or unavailable date is not evidence of zero detections.

The helper requires `FIRMS_MAP_KEY` in the process environment. It does not load `.env` automatically. Credentials are redacted from the manifest and suppressed in request-error messages. This is an offline-tested helper, not a validated seasonal extraction service.

## Weather provenance and attribution

Record the explicitly selected model rather than silently relying on Best Match. The source's spatial resolution remains coarser than the proposed 3 km analysis grid. Assigning one weather value to several cells does not create additional independent weather observations. Historical reanalysis also has an availability delay. A one-day feature lag alone does not establish that the data could have been obtained at the prediction time. Treat this use as retrospective backtesting until availability-time checks are implemented.

Suggested attribution for transformed output: Weather data by Open-Meteo.com, https://open-meteo.com/, under CC BY 4.0, https://creativecommons.org/licenses/by/4.0/. FireSight aggregated and joined the data to analysis cells. Add the provider-specific attribution required by the model actually selected. Apply this wording to the received weather data and reconstruction; the selected upstream model remains unconfirmed.

## Per-run source record

Use `source-record.template.json` once for each acquired file. Replace nulls with measured values. Do not create fictitious access dates, coverage, counts or checksums. Ayon's seasonal downloader and weather pull should supply these records alongside the files. Keep unknown values explicitly unknown.

## Sources checked on 29 October 2026

- NASA FIRMS. n.d. “API Area.” https://firms.modaps.eosdis.nasa.gov/api/area/.
- Open-Meteo. n.d. “Historical Weather API.” https://open-meteo.com/en/docs/historical-weather-api.
- Open-Meteo. n.d. “Licence.” https://open-meteo.com/en/licence.
- Open-Meteo. n.d. “Terms and Privacy.” https://open-meteo.com/en/terms. Review service limits for the actual run rather than assuming that the data licence removes usage limits.

## Repository integration decisions still required

Latest main cc00735 configures 2019–2025, matching six July–June seasons. Confirm actual coverage from acquisition manifests; configuration alone does not prove it.

The now-merged PR #3 validation protocol uses bbox 115.65,-32.60,116.30,-31.60, Perth calendar days and 2 km / 2 day event grouping; main uses bbox 115.45,-32.60,116.55,-31.40, UTC days and 1.5 km / 24 hour grouping. Ayon and Sa-ad must agree one version before labels, weather and forecasts are joined. The FS-36 adapter deliberately follows the inspected main schema until that decision is made.

Main's current grid creates 1,575 centres, with 35 outside its configured bbox. The checker reports these as failures when that grid is supplied; it does not silently drop or move them. A boundary-intersection policy may be legitimate, but it must be explicit before changing the validation rule.

The correction to src/ingest/download_firms.py does not update Ayon's separate src/ingest/firms_client.py seasonal workflow. Latest main now uses five-day chunks and raises if a download window fails. Credential-safe error reporting and actual source manifests / seasonal coverage still require review.

Current receipt: 2019–2025 event tables contain 2,846 rows, with a supplied grouped-detection-count sum of 24,968. Weather has 56 points over 2018-07-01–2025-06-30, including spin-up. Archive and member SHA256 values, units, returned coordinates and known provenance gaps are retained in the [30 October audit](yian-delivery/Real_Data_Quality_Status.md). Current main labels reproduce 0.08174024% positives; model PR-AUC remains author-reported.
