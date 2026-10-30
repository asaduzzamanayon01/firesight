# FireSight data pipeline and security contribution

Yian Wang — Data and Pipeline Lead  
Updated 30 October 2026 for Tabib to integrate into the final report

## Evidence and integration status

This contribution integrates upstream main a86e39b, including the new spatial features and static-source filter. The combined candidate passes 95 root tests with six subtests, ten geography tests separately with pyproj, and lint. The workflow fixes the upstream test-entry-point import failure while retaining its Python 3.11 synthetic-baseline smoke check. PR #7 awaits review and upstream merge; current hosted status is linked from the delivery index. Six received event tables and five raw weather batches have been checked. Event structure passes; reconstructed weather retains a 35-centre boundary failure. Filtered label counts independently match the newly published metric CSVs; their summary arithmetic is checked without retraining or rederiving scores from predictions. Forecast export and original acquisition/run provenance remain incomplete.

## Data and pipeline

FireSight separates acquisition, validation and modelling inputs. The catalogue records source products, requested and observed dates, geographic extent, variables, units, transformations and attribution. This contribution checks NASA FIRMS satellite-derived event tables and Open-Meteo historical weather. Vegetation, roads and powerlines are outside its verified implementation scope.

The FIRMS helper preserves downloaded CSV bytes and writes a manifest with product, dates, bounding box, retrieval time and SHA256. The Area API date denotes the first day of a request. The helper converts its inclusive end-date argument to that start date and limits requests to one to five days (NASA FIRMS n.d.). This helper's offline tests do not establish that Ayon's separate seasonal extraction retrieved every source window.

The weather catalogue retains requested and returned coordinates, timezone, units and selected model. Historical reanalysis supports retrospective analysis; a one-day feature lag does not prove availability at a historical issue time (Open-Meteo n.d.a). Assigning coarse weather values to 3 km cells does not create independent observations at that resolution.

The non-mutating quality module checks required fields, missingness, duplicate keys, timestamps and configured coordinate bounds. The repository adapter preserves acquisition precision and checks each event date against its UTC acquisition day. A supplied grid resolves cell IDs to coordinates. The forecast contract requires cell_id, lat, lon, date, probability, actual and season, with finite probabilities in [0,1] and binary actual labels. The new optional risk_percentile must also be finite and in [0,1]; this daily relative rank is not a calibrated probability. JSON and Markdown outputs retain aggregate counts, failures and input hashes. The ordinary checker exits nonzero on invalid inputs. Coverage and scientific validity require separate review.

## Data management

Raw inputs preserve the received evidence; processed outputs represent documented transformations. A source-record template captures provider/product or model, retrieval time, requested and observed coverage, coordinate system, parent hashes and attribution. Unknown provenance stays explicitly unknown. A caller's real/synthetic/test-fixture label does not authenticate acquisition. Satellite detections, supplied grouped events and positive cell-days are reported separately.

Open-Meteo API data use CC BY 4.0. The catalogue credits the provider, links its licence and identifies aggregation; upstream model attribution must match the actual selected source (Open-Meteo n.d.b). NASA product-specific notices also remain necessary. Raw and processed data are excluded by repository ignore rules, with aggregate evidence selected intentionally for sharing. This contribution does not configure shared-storage access, long-term retention, DVC or MLflow automatically.

## Security and privacy measures

The FIRMS helper reads its key from the environment, redacts the recorded request URL and suppresses credential-bearing network errors. It refuses to overwrite an existing output. Focused offline tests cover these controls; a live call remains unverified. Upstream removed the example environment file, so setup uses an environment variable. The separate seasonal workflow still requires credential-safe logging review.

Quality checks run locally without network access. Summaries share filenames, hashes and aggregate findings rather than raw observations or absolute paths. Ignore rules cannot remove secrets already committed; secret-free history, encrypted storage, production access control and deployment security have not been verified. Only authorised layers at necessary precision should enter the final release. Environmental observations and a passing structural check do not establish reliable public warnings.

## Measured data quality and remaining limits

Victor supplied ignitions.zip and weather.zip, described as real FIRMS and weather data. The exact copied archive bytes passed ZIP CRC checks; hashes and member-level audit evidence are retained in Real_Data_Audit_2026-10-30.json. The six July–June event tables cover 2019–20 through 2024–25 and contain 620, 552, 523, 413, 350 and 388 rows, respectively: 2,846 supplied event rows in total. The sum of detections_in_event is 24,968; raw FIRMS detections were not provided to verify that sum independently. All six tables pass the repository's required-field, missingness, duplicate, timestamp, seasonal-range and coordinate checks. Event identifiers reset per seasonal file, so the valid combined key is source season plus event_id.

Under current main grid assignment, the supplied rows map to 2,822 positive cell-days. The 1,575-cell grid and 2,192 dates yield 3,452,400 cell-days, with a positive proportion of 0.08174024%. This reproduces the author's rounded label proportion of 0.0817% under main's assumptions. It is not an independently confirmed count of ignition causes. Event-free dates cannot establish that every source download succeeded.

The weather archive contains five raw JSON batches with 56 distinct returned point coordinates. Every point has all 2,557 expected daily dates and 61,368 hourly timestamps for 2018-07-01 through 2025-06-30, with no missing or nonfinite values in the inspected variables. Response metadata records Australia/Perth, daily maximum temperature in degrees Celsius, maximum wind in metres per second, rainfall in millimetres and hourly relative humidity in percent. This is not an author-supplied processed weather table.

The offline audit reuses the existing main transformations: daily minimum humidity, simplified KBDI with a discarded spin-up year, and nearest request-point mapping. The locally reconstructed output has 3,452,400 unique cell-days and no missing values in its five weather features. However, 35 main grid centres are outside the configured bbox, affecting 76,720 rows. The unchanged checker reports a failure. No data were dropped or moved to conceal it; the team must approve an edge-cell policy or regenerate a consistent grid and downstream outputs.

The spatial update removes cells with at least 35 positive dates across the six seasons. Applying the existing main filter to the received labels removes cells 570 and 571, with 99 and 39 positive dates. The filtered population has 1,573 cells, 3,448,016 cell-days and 2,684 positives, or 0.07784187%. Its seasonal row and positive counts exactly match the published baseline and spatial-model CSVs. These are a different population from the unfiltered counts above.

The published six-season CSV means are PR-AUC 0.01022567 for spatial LightGBM and 0.00426083 for the paired filtered climatology baseline, with the spatial model higher in all six seasons. Published top-5% capture counts sum to 861 of 2,684 positive cell-days (32.08%). These are arithmetic checks of supplied summaries, not rederived metrics from held-out predictions. The earlier weather-only mean of 0.00213001 uses unfiltered data, so the two runs are not a controlled feature-only comparison. The supplied MLflow export records that earlier run and does not identify the new spatial run.

The static mask uses labels from all seasons before leave-one-season-out evaluation. A threshold fixed in advance does not make the resulting selected cell set independent of held-out labels. An independently defined mask or a fold-specific sensitivity check is needed before claiming unbiased performance. Spatial priors are also generated before the inner early-stopping split, allowing fit-season features to depend on inner-validation-season labels. These are review limitations inferred from the inspected code; the author's model method and published metrics have not been silently changed.

Sa-ad's FS-33 comment records the main-style grid and 24-hour real-data clustering. His open PR #14 documents intentional edge overshoot and two strict expected-failure tests where spreading fires are split into multiple events; a separate run reproduces seven passes and those two expected failures. His proposed 48-hour setting remains a team decision, not an applied change. His FS-32 comment states that the evaluation draft has been checked against Ayon's results_real output, with final integration pending. Original acquisition manifests, the selected weather model, actual processed run inputs, a matching spatial-model run record and forecast.csv remain unavailable. Main uses UTC event dates while weather uses Perth dates; edge-cell and calendar-day interpretation still require agreement. Structural and summary checks do not authenticate acquisition completeness, historical feature availability, calibrated probabilities or model generalisation. See Spatial_Update_2026-10-30.md and its audit JSON/script for the evidence and remaining owners.

## References

NASA FIRMS. n.d. “API Area.” Accessed October 29, 2026. https://firms.modaps.eosdis.nasa.gov/api/area/.

Open-Meteo. n.d.a. “Historical Weather API.” Accessed October 29, 2026. https://open-meteo.com/en/docs/historical-weather-api.

Open-Meteo. n.d.b. “Licence.” Accessed October 29, 2026. https://open-meteo.com/en/licence.
