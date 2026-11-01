"""Yian's independent replay of the current spatial model on received inputs.

Writes a new isolated directory. Preserves the current model/label policy and its
documented limitations; this is a retrospective reproduction, not live forecasting.
"""
from __future__ import annotations

import argparse
import gc
import importlib.metadata
import json
import logging
import os
import platform
import sys
from datetime import UTC, date, datetime
from pathlib import Path

import numpy as np
import pandas as pd

from scripts.demo_stats import capture_rates
from scripts.export_forecast import export
from src.config import CFG, ROOT
from src.evaluation.metrics import evaluate
from src.evaluation.splits import leave_one_season_out
from src.features.build_cell_days import add_temporal_features, build, drop_static_sources
from src.features.grid import cell_centroids
from src.features.join_weather import join
from src.models.baseline_climatology import ClimatologyBaseline
from src.quality.checks import file_sha256, write_report
from src.quality.coverage import check_cell_day_coverage
from src.quality.repository import check_repository_frame

LIMITS = [
    "Current main's all-season label-derived static mask is retained; selection needs review.",
    "Current main builds spatial priors before its inner validation split; this is not an unbiased-evaluation claim.",
    "LOSO may train on future seasons; export is a retrospective backtest, not a prospective live forecast.",
    "UTC event days, Perth weather days, and edge-centre acceptance remain unapproved team decisions.",
    "Inputs are received events and locally reconstructed weather, not authenticated acquisition manifests.",
    "Export uses uncalibrated scores and the existing probability floor; no calibrated-probability claim.",
]


def compact_baseline_fit(frame):
    """Exactly aggregate main's +/-15-day expansion without materialising 31x rows.

    Preserve its modulo-365 handling, including its day-366 prediction fallback.
    """
    model = ClimatologyBaseline()
    model.global_rate_ = float(frame.ignition.mean())
    cells = np.sort(frame.cell_id.unique())
    ci = np.searchsorted(cells, frame.cell_id.to_numpy())
    day = (frame.date.dt.dayofyear.to_numpy() - 1) % 365
    pos, count = np.zeros((len(cells), 365)), np.zeros((len(cells), 365))
    np.add.at(pos, (ci, day), frame.ignition.to_numpy())
    np.add.at(count, (ci, day), 1)
    total_pos, total_count = np.zeros_like(pos), np.zeros_like(count)
    for offset in range(-model.window_days, model.window_days + 1):
        total_pos += np.roll(pos, offset, axis=1)
        total_count += np.roll(count, offset, axis=1)
    rate = (total_pos + model.prior_strength * model.global_rate_) / (total_count + model.prior_strength)
    index = pd.MultiIndex.from_product([cells, np.arange(1, 366)], names=["cell_id", "doy"])
    model.cell_doy_rate_ = pd.Series(rate.ravel(), index=index)
    return model


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--events-dir", type=Path, required=True)
    parser.add_argument("--weather", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--source-revision", required=True, help="core-code revision; runner hash is recorded separately")
    parser.add_argument("--forecast-start", type=date.fromisoformat, required=True)
    parser.add_argument("--forecast-days", type=int, default=14)
    args = parser.parse_args(argv)
    if args.forecast_days < 1:
        parser.error("forecast days must be positive")
    files = sorted(args.events_dir.glob("ignitions_*.parquet"))
    if len(files) != 6:
        parser.error("requires the six received seasonal event tables")
    if not args.weather.is_file():
        parser.error("reconstructed weather file is missing")
    dest = args.output_dir.resolve()
    if dest.exists():
        parser.error("output directory must be new; existing runs are never overwritten")
    dest.mkdir(parents=True)
    for name in ("processed", "reports", "models", "figures", "mlflow"):
        (dest / name).mkdir()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    log = logging.getLogger(__name__)
    receipt = {
        "operator": "Yian Wang", "run_purpose": "independent received-input replay; provisional retrospective backtest",
        "started_utc": datetime.now(UTC).isoformat(),
        "core_source_revision": args.source_revision,
        "runner_sha256": file_sha256(Path(__file__)),
        "runtime": {"python": platform.python_version(), "packages": {
            name: importlib.metadata.version(name) for name in
            ("pandas", "numpy", "pyarrow", "scikit-learn", "lightgbm", "mlflow", "matplotlib")}},
        "inputs": [{"name": p.name, "sha256": file_sha256(p)} for p in [*files, args.weather]],
        "code_sha256": {str(p.relative_to(ROOT)): file_sha256(p) for pattern in
                        ("src/**/*.py", "scripts/*.py", "config/*.yaml") for p in sorted(ROOT.glob(pattern))},
        "configuration": json.loads(json.dumps(CFG.to_dict())),
        "forecast_window": {"start": str(args.forecast_start), "days": args.forecast_days},
        "limitations": LIMITS, "status": "preparing", "overall_acceptance": False,
    }

    def save():
        (dest / "run-manifest.json").write_text(json.dumps(receipt, indent=2, allow_nan=False) + "\n")

    save()
    try:
        # Process-local paths isolate all outputs; the source YAML is never edited.
        CFG.to_dict()["paths"].update({key: str(dest / sub) for key, sub in
                                      (("processed", "processed"), ("reports", "reports"),
                                       ("models", "models"), ("figures", "figures"))})
        os.environ["MLFLOW_TRACKING_URI"] = "sqlite:///" + str(dest / "mlflow" / "mlflow.db")
        os.environ["MPLCONFIGDIR"] = str(dest / "matplotlib-cache")
        events = pd.concat([pd.read_parquet(p) for p in files], ignore_index=True)
        cell_days, removed = drop_static_sources(add_temporal_features(build(events)))
        grid = cell_centroids()
        grid = grid[grid.cell_id.isin(cell_days.cell_id.unique())].copy()
        grid.to_csv(dest / "processed/grid.csv", index=False)
        removed.to_csv(dest / "reports/static_cells.csv", index=False)
        receipt["population"] = {"events": len(events), "cells": int(cell_days.cell_id.nunique()),
                                 "rows": len(cell_days), "positive_cell_days": int(cell_days.ignition.sum())}
        weather = pd.read_parquet(args.weather)
        features = join(cell_days, weather)
        features.to_parquet(dest / "processed/cell_days_features.parquet", index=False)
        receipt["feature_missing_counts"] = {name: int(n) for name, n in features.isna().sum().items() if n}
        del events, cell_days, weather, features
        gc.collect()
        receipt["status"] = "training_six_season_spatial_model"
        save()
        import mlflow

        from src.models.train_lgbm import run

        mlflow.set_tracking_uri(os.environ["MLFLOW_TRACKING_URI"])
        mlflow.create_experiment(CFG.mlflow.experiment_name,
                                 artifact_location=(dest / "mlflow/artifacts").as_uri())

        result = run()
        result.to_csv(dest / "reports/lgbm_cv_yian_replay.csv", index=False)
        log.info("spatial model complete; recomputing baseline and prediction-level summaries")
        oof = pd.read_parquet(dest / "processed/oof_predictions.parquet")
        baseline_rows = []
        baseline_oof = np.full(len(oof), np.nan)
        for season, tr, te in leave_one_season_out(oof):
            model = compact_baseline_fit(oof.iloc[tr])
            p = model.predict_proba(oof.iloc[te])
            baseline_oof[te] = p
            baseline_rows.append({"season": season, **evaluate(oof.iloc[te].ignition.to_numpy(), p).to_dict()})
        pd.DataFrame(baseline_rows).to_csv(dest / "reports/baseline_cv_yian_replay.csv", index=False)
        baseline_frame = oof[["cell_id", "date", "season", "ignition"]].copy()
        baseline_frame["y_prob"] = baseline_oof
        baseline_frame.to_parquet(dest / "processed/baseline_oof_predictions.parquet", index=False)
        del baseline_frame
        capture = pd.concat([capture_rates(oof, q) for q in (0.05, 0.10)], ignore_index=True)
        capture.to_csv(dest / "reports/demo_stats_yian_replay.csv", index=False)
        forecast = export(oof, str(args.forecast_start), args.forecast_days, calibrated=False)
        forecast.to_csv(dest / "processed/forecast.csv", index=False)
        end = args.forecast_start + pd.Timedelta(days=args.forecast_days - 1)
        quality = check_repository_frame(forecast, "forecast", grid=grid,
                                         start=args.forecast_start, end=end)
        coverage = check_cell_day_coverage(forecast, grid, start=args.forecast_start, end=end)
        quality.update(expected_cell_day_coverage=coverage, input_name="forecast.csv",
                       sha256=file_sha256(dest / "processed/forecast.csv"),
                       grid_sha256=file_sha256(dest / "processed/grid.csv"))
        quality["issues"].extend(coverage["issues"])
        quality["passed"] = quality["passed"] and coverage["passed"]
        write_report([quality], dest / "reports/forecast-quality", data_mode="real",
                     bbox=CFG.region.bbox, revision=args.source_revision,
                     settings={"scope": "Yian replay; raw uncalibrated retrospective export",
                               "require_complete_cell_days": True})
        receipt["forecast"] = {"rows": len(forecast), "days": int(forecast.date.nunique()),
                               "positive_rows": int(forecast.actual.sum()), "coverage": coverage,
                               "strict_quality_passed": quality["passed"]}
        experiment = mlflow.get_experiment_by_name(CFG.mlflow.experiment_name)
        runs = mlflow.search_runs(experiment_ids=[experiment.experiment_id])
        if len(runs) != 1:
            raise ValueError("expected one spatial run in the isolated MLflow store")
        run_id = runs.iloc[0].run_id
        receipt["mlflow"] = {"run_id": run_id, "status": runs.iloc[0].status,
                             "experiment_id": experiment.experiment_id}
        receipt["status"] = "completed_provisional_replay"
        receipt["finished_utc"] = datetime.now(UTC).isoformat()
        receipt["outputs"] = {str(p.relative_to(dest)): {"bytes": p.stat().st_size, "sha256": file_sha256(p)}
                              for folder in ("processed", "reports", "models", "figures")
                              for p in sorted((dest / folder).rglob("*")) if p.is_file()}
        save()
        client = mlflow.MlflowClient()
        for key, value in {"operator": "Yian Wang", "purpose": "independent provisional replay",
                           "core_source_revision": args.source_revision,
                           "overall_acceptance": "pending team review", "calibrated": "false"}.items():
            client.set_tag(run_id, key, value)
        client.log_artifact(run_id, str(dest / "run-manifest.json"), "provenance")
        for p in (dest / "reports").glob("*.csv"):
            client.log_artifact(run_id, str(p), "replay_reports")
        runs = mlflow.search_runs(experiment_ids=[experiment.experiment_id])
        runs.to_csv(dest / "mlflow_runs_yian_replay.csv", index=False)
        log.info("replay complete: %s; final acceptance remains pending", dest.name)
    except Exception as exc:
        receipt.update(status="failed", error_type=type(exc).__name__,
                       finished_utc=datetime.now(UTC).isoformat())
        save()
        raise
    return 0


if __name__ == "__main__":
    sys.exit(main())
