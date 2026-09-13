.PHONY: setup synth test pipeline baseline train calibrate explain lint

setup:
	pip install -r requirements.txt

synth:
	PYTHONPATH=. python scripts/make_synthetic.py

baseline:
	PYTHONPATH=. python -m src.models.baseline_climatology

train:
	PYTHONPATH=. python -m src.models.train_lgbm

calibrate:
	PYTHONPATH=. python -m src.models.calibrate

explain:
	PYTHONPATH=. python -m src.explain.shap_explain

pipeline: baseline train calibrate explain

test:
	PYTHONPATH=. pytest

lint:
	ruff check .
