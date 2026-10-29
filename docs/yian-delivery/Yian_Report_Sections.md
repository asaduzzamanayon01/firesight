# FireSight data pipeline and security contribution

Yian Wang — Data and Pipeline Lead  
Prepared 29 October 2026 for Tabib to integrate into the final report

## Evidence and integration status

This contribution now integrates with private repository main snapshot 41584f9, including Ayon's CI, weather acquisition, forecast export and inner training-season validation updates. Yian's earlier FIRMS helper is already in main. The refreshed delivery candidate passes 83 local tests, including controlled CSV and Parquet fixtures, and repository lint passes. PR #7 is submitted for review; upstream merge and hosted CI results remain pending. No real input files or measured real-data event counts, missingness rates or model results were obtained. Update the quality summary after the actual files and source manifests arrive.

## Data and pipeline

FireSight separates data acquisition, validation and modelling inputs. The data catalogue identifies the provider and product, the requested period and geographical extent, the variables and units, and the provenance information needed to repeat a run. The updated catalogue includes NASA FIRMS seasonal observations and Open-Meteo historical weather. Vegetation, roads, powerlines and other layers from the earlier proposal are outside this contribution's verified implementation scope.

The FIRMS helper preserves downloaded CSV bytes and creates a manifest containing the product, requested dates, bounding box, retrieval time and SHA256 checksum. During review, the earlier helper's date semantics required correction: the Area API's date is the first day of the interval. The revised helper retains an inclusive end-date command-line argument and converts it to the start date expected by the provider. It also restricts individual requests to the documented range of one to five days. Seasonal extraction requires Ayon's acquisition workflow to combine documented chunks and check product availability (NASA FIRMS n.d.).

The weather catalogue specifies the provenance required from Open-Meteo, including the selected model, returned coordinates, variables, units and timezone. Open-Meteo describes its historical API as a reanalysis service. The catalogue therefore distinguishes retrospective weather inputs from forecasts available at a historical issue time (Open-Meteo n.d.a). Assigning weather to the proposed 3 km cells does not establish independent observations at that resolution. A one-day lag also does not demonstrate that reanalysis values were available at forecast time.

Before modelling, the new quality module validates the supplied ignition and weather tables. At the dashboard boundary it checks the specified forecast.csv fields: cell_id, lat, lon, date, probability, actual and season. It checks required columns and values, parseable ISO timestamps, duplicates and coordinates within the configured study box. The repository adapter reads the five configured weather fields, including kbdi, and preserves acquisition times when checking ignition-event duplicates. It also checks that each event date matches its UTC acquisition day. When weather rows contain only a cell identifier, the command can attach coordinates from a grid table with unique identifiers. An unmatched cell fails coordinate validation. The checker also rejects invalid forecast probabilities and non-binary actual labels.

The checks leave input tables unchanged. They produce a JSON record and a Markdown summary containing table sizes, missing-value counts, time coverage, validation issues and available label summaries. Input checksums bind the summary to the supplied files. A failing table or unreadable input yields a non-zero exit status so the team can stop a run before using unsuitable data. These checks identify structural problems. They do not prove that every expected cell and day is present, that event grouping is scientifically correct, or that features satisfy availability-time constraints.

## Data management

Raw inputs and processed tables have different roles. Raw files preserve what the provider supplied, while processing outputs represent documented transformations. The delivered source-record template captures the product or model, retrieval time, observed and requested coverage, coordinate system, attribution and parent manifests. Null fields explicitly identify provenance that has not yet been supplied. They must be populated from the actual acquisition run rather than inferred from the proposal.

The quality report stores the caller's declared data mode as real, synthetic or test-fixture. That label alone does not authenticate provenance. Ayon and Yian must review the associated source manifests before presenting a run as real. For the final quality summary, event-table rows must also be distinguished from confirmed ignition events. Satellite detections, grouped events and positive cell-days are different quantities and should not share an unexplained count.

Open-Meteo offers API data under CC BY 4.0. The catalogue supplies attribution wording, links the licence and identifies the aggregation performed by FireSight (Open-Meteo n.d.b). Product-specific upstream attribution and NASA FIRMS terms still need to be retained for the exact sources used. The inspected repository excludes local environment files and raw and processed data. The candidate additionally excludes the quality tool's generated reports; evidence files must be selected intentionally for assessment submission. The module does not configure DVC, MLflow, shared storage permissions or long-term retention automatically.

## Security and privacy measures in the delivered module

The FIRMS helper reads its map key from the process environment. It stores a redacted request URL in the manifest and suppresses credential-bearing URLs in network error messages. The supplied environment example contains an empty variable, not a credential. The downloader rejects an existing output destination to reduce accidental replacement of the source record. These controls have focused offline tests. A live service call remains unverified.

The quality tool runs locally without network access. Its generated summaries report aggregate counts and input filenames rather than raw row samples, complete API responses or absolute file paths. The inspected repository's ignore rules exclude local environment files and raw and processed data directories. An ignore file cannot remove material already committed, so it does not by itself establish that the team's history is free of secrets. Access control, encrypted storage, secret scanning and production deployment controls have not been verified and are not claimed here.

Environmental observations do not require collecting participant identities for these checks. Nevertheless, a fine-grained location can still reveal sensitive assets. The final team release should include only authorised layers at the precision needed for the assessment. FireSight's historical backtest must be described with its actual data mode and limitations. A quality pass is not evidence that the system provides reliable public warnings.

## Real data quality summary pending measured inputs

No real-data quality statistics are reported in this version. To complete Y3, run the checker on Ayon's actual ignition table, weather table and forecast.csv using the agreed study box, source timezone, feature names and grid. Main and the open geospatial PR currently differ in their bounding box, event clustering and UTC versus Perth-day rules; these differences must be resolved before integration. Preserve the manifests, file checksums and code revision alongside quality-report.json. Review the event definition and expected seasonal and grid coverage manually. Then insert the measured counts, missing values, failed checks and unresolved limitations into this subsection. A failed or missing acquisition must remain distinguishable from a valid season with no detections.

## References

NASA FIRMS. n.d. “API Area.” Accessed October 29, 2026. https://firms.modaps.eosdis.nasa.gov/api/area/.

Open-Meteo. n.d.a. “Historical Weather API.” Accessed October 29, 2026. https://open-meteo.com/en/docs/historical-weather-api.

Open-Meteo. n.d.b. “Licence.” Accessed October 29, 2026. https://open-meteo.com/en/licence.
