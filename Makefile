.PHONY: help setup test lint reset synth baseline train calibrate explain pipeline compare \
        labels weather features real demo-stats forecast dashboard-data serve-dashboard

PY := PYTHONPATH=. python

# Fire seasons to download: season Y runs 1 Jul Y to 30 Jun Y+1 (see config/config.yaml)
SEASONS ?= 2019 2020 2021 2022 2023 2024

help:  ## List the available targets
	@grep -E '^[a-z-]+:.*##' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  %-16s %s\n", $$1, $$2}'

# --- Environment -------------------------------------------------------------

setup:  ## Install dependencies
	pip install -r requirements.txt

test:  ## Run the unit and leakage tests
	PYTHONPATH=. pytest

lint:  ## Lint with ruff
	ruff check .

reset:  ## Delete generated data so synthetic and real data are never mixed
	rm -f data/raw/ignitions_*.parquet data/processed/*.parquet data/processed/*.csv \
	      data/processed/*.json models/*.pkl
	@echo "data/raw ignitions, data/processed and models/ cleared"

# --- Synthetic data (no API key, about 2 minutes) ------------------------------

synth:  ## Generate synthetic cell-day data
	$(PY) scripts/make_synthetic.py

# --- Real data ----------------------------------------------------------------

labels:  ## FIRMS ignition labels, one file per season (needs FIRMS_MAP_KEY in .env)
	@mkdir -p logs
	@for y in $(SEASONS); do \
	  echo "FIRMS season $$y"; \
	  $(PY) -m src.ingest.firms_client --start $$y-07-01 --days 365 2>&1 | tee logs/firms_$$y.log; \
	done

weather:  ## Open-Meteo weather and KBDI (no key; resumes from cache after a 429)
	$(PY) -m scripts.fetch_weather_openmeteo

features:  ## Cell-day table (labels) then lagged weather join
	$(PY) -m src.features.build_cell_days
	$(PY) -m src.features.join_weather

real: labels weather features pipeline demo-stats forecast  ## Whole real-data run

# --- Models (work on synthetic or real data) -----------------------------------

baseline:  ## Climatology baseline, the number to beat
	$(PY) -m src.models.baseline_climatology

train:  ## LightGBM, leave-one-season-out, logged to MLflow
	$(PY) -m src.models.train_lgbm

calibrate:  ## Isotonic calibration on out-of-fold predictions
	$(PY) -m src.models.calibrate

explain:  ## SHAP feature importance
	$(PY) -m src.explain.shap_explain

pipeline: baseline train calibrate explain  ## baseline -> train -> calibrate -> explain

compare:  ## Compare logistic, random forest, gradient boosting, LightGBM
	$(PY) -m src.models.compare_models --sample 200000

# --- Outputs ------------------------------------------------------------------

demo-stats:  ## Share of ignitions captured by the top 5% / 10% of cells
	$(PY) -m scripts.demo_stats --top 0.05 0.10

forecast:  ## Write data/processed/forecast.csv (dashboard window: 1 Dec 2024 to 28 Feb 2025)
	$(PY) -m scripts.export_forecast --start 2024-12-01 --days 90

dashboard-data: forecast  ## Copy the forecast into the dashboard
	cp data/processed/forecast.csv dashboard/data/forecast.csv

serve-dashboard:  ## Serve the dashboard at http://localhost:8000
	cd dashboard && python3 -m http.server 8000
