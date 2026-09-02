# FireSight
Predicting where bushfires are likely to start across the Perth peri-urban interface. Grid-level ignition probability on a 3 km grid, 24 to 72 hours ahead.
COMP6002 Computer Science Project, Semester 2 2026. Group 14, Master of AI.
## Team
| Name | Role |
|---|---|
| A K M Asaduzzaman Ayon | Scrum Master and Machine Learning | | Yian Wang | Data and Pipeline |
| Md Tabib Khan | Product, Ethics and Documentation |
| S M Nuayman Sa-ad | Geospatial and Evaluation |
| Zarif | Dashboard and Delivery |
## Structure
- `src/ingest` data download and ETL
- `src/features` feature engineering
- `src/models` training and calibration
- `src/evaluation` metrics and validation - `notebooks` exploratory analysis
- `docs` decisions log and sprint reports
## Setup
```bash
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env           #  FIRMS API key
