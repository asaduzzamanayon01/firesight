# Data Ingestion Scripts

Maintainer: Yian Wang - Data & Pipeline

## NASA FIRMS area download

`download_firms.py` downloads an unchanged FIRMS area-report CSV and creates a JSON manifest containing the retrieval time, query parameters, output checksum and row count. The manifest redacts the FIRMS API key.

1. Install dependencies: `python -m pip install -r requirements.txt`.
2. Create a local `.env` from `.env.example`, add `FIRMS_MAP_KEY`, then export it in your shell. Do not commit `.env`.
3. Run a bounded query, for example:

   ```bash
   python src/ingest/download_firms.py \
     --bbox 115.4,-32.3,116.2,-31.5 \
     --days 10 \
     --end-date 2026-09-13
   ```

The default output path is `data/raw/firms/`. Raw files and manifests are excluded from ordinary Git commits. Before modelling, the team must record the selected FIRMS product, query period, study-area definition and prescribed-burn filtering decision in the project data catalogue.

