# Data Sources and Reproducibility Record

Maintainer: Yian Wang - Data & Pipeline

This document records the minimum provenance information required before a FireSight data source is used in a model run. It complements, rather than replaces, the proposal Data Management Plan.

| Source | Intended contribution | Record before use |
|---|---|---|
| NASA FIRMS | Satellite active-fire observations for constructing ignition labels | Product identifier, query URL with key redacted, access date, bounding box, time window, licence/terms, checksum and label-construction rule |
| ERA5-Land and/or Bureau of Meteorology | Weather and drought-related predictors | Variables, provider, access date, spatial/temporal resolution, resampling method, licence/terms and checksum |
| Sentinel-2 and/or MODIS | Vegetation-condition and fuel proxies | Product/version, acquisition dates, cloud handling, spatial resolution, aggregation method, licence/terms and checksum |
| Geoscience Australia and WA public spatial layers | Roads, powerlines, settlement edges and terrain predictors | Layer version, access date, coordinate reference system, licence/terms and transformation record |
| DBCA burn schedule | Filter for planned ignitions and label-noise documentation | Coverage period, access date, matching rule, unresolved records and licence/terms |

Every raw download must remain unchanged in `data/raw/`. A processing run must record its input manifest(s), source version, script revision, time-zone convention, coordinate reference system and output checksum. The team must not commit API credentials, `.env` files, raw data, restricted layers or unapproved derived outputs to Git.

