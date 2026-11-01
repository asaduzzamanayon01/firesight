"""Reconcile received event labels with PR #15's published aggregate CSVs offline.

Does not train a model, verify predictions or modify original source data.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from src.features.build_cell_days import build, drop_static_sources
from src.quality.checks import file_sha256


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--events-dir", required=True, type=Path)
    ap.add_argument("--results-dir", required=True, type=Path)
    ap.add_argument("--output", required=True, type=Path)
    args = ap.parse_args()
    files = sorted(args.events_dir.glob("ignitions_*.parquet"))
    if len(files) != 6:
        raise ValueError("Expected the six received event tables")
    events = pd.concat([pd.read_parquet(f) for f in files], ignore_index=True)
    base = build(events)
    filtered, removed = drop_static_sources(base)
    counts = filtered.groupby("season").agg(n=("ignition", "size"), n_positive=("ignition", "sum"))
    baseline = pd.read_csv(args.results_dir / "baseline_cv.csv")
    spatial = pd.read_csv(args.results_dir / "lgbm_cv_spatial.csv")
    weather = pd.read_csv(args.results_dir / "lgbm_cv_weather_only.csv")
    demo = pd.read_csv(args.results_dir / "demo_stats.csv")
    static_published = pd.read_csv(args.results_dir / "static_cells.csv")
    log = pd.read_csv(args.results_dir / "mlflow_runs_REAL_only.csv")
    paired = baseline.merge(spatial, on="season", suffixes=("_baseline", "_spatial"),
                            validate="one_to_one")
    output = {
        "upstream_revision": "a86e39b62df5a7237e47e2ef9724ef8c10fef06e",
        "evidence_scope": "received-label reconstruction and arithmetic over supplied metrics; no model retraining",
        "events": [{"file": f.name, "sha256": file_sha256(f)} for f in files],
        "result_csv_hashes": {f.name: file_sha256(f) for f in args.results_dir.glob("*.csv")},
        "unfiltered": {"cells": int(base.cell_id.nunique()), "rows": len(base),
                       "positive_cell_days": int(base.ignition.sum())},
        "filtered": {"cells": int(filtered.cell_id.nunique()), "rows": len(filtered),
                     "positive_cell_days": int(filtered.ignition.sum()),
                     "positive_rate_percent": float(filtered.ignition.mean() * 100)},
        "removed_cells": removed.to_dict("records"),
        "removed_matches_published": removed.equals(static_published),
        "filtered_season_counts": counts.reset_index().to_dict("records"),
        "published_counts_match": {},
        "published_pr_auc": {
            "spatial_mean": float(spatial.pr_auc.mean()),
            "baseline_filtered_mean": float(baseline.pr_auc.mean()),
            "weather_only_unfiltered_mean": float(weather.pr_auc.mean()),
            "spatial_beats_paired_baseline_seasons": int(
                (paired.pr_auc_spatial > paired.pr_auc_baseline).sum()),
            "paired_seasons": len(paired),
            "baseline_spatial_counts_identical": bool(
                paired.n_baseline.eq(paired.n_spatial).all()
                and paired.n_positive_baseline.eq(paired.n_positive_spatial).all()),
        },
        "demo_capture": [],
        "mlflow_export": {
            "runs": len(log),
            "mean_pr_auc_values": log["metrics.mean_pr_auc"].tolist(),
            "logged_source_revisions": log["tags.mlflow.source.git.commit"].tolist(),
            "matches_spatial_mean": bool(
                (log["metrics.mean_pr_auc"] - spatial.pr_auc.mean()).abs().lt(1e-10).any()),
        },
        "limits": [
            "Aggregate metrics are checked arithmetically, not recomputed from held-out predictions.",
            "Static-source mask uses ignition labels across all six seasons before LOSO; an independent source mask or fold-specific sensitivity check is needed before unbiased evaluation claims.",
            "The original weather-only metrics and new spatial/baseline metrics use different populations.",
            "The provided MLflow export describes the earlier weather-only result, not the new spatial model run.",
            "Original acquisition manifests, processed model inputs and forecast.csv remain absent.",
            "The 35 outside-bbox main grid centres are not repaired by excluding cells 570/571.",
        ],
    }
    for name, frame in (("baseline", baseline), ("spatial", spatial)):
        merged = counts.reset_index().merge(frame[["season", "n", "n_positive"]],
                                            on="season", suffixes=("_local", "_csv"),
                                            validate="one_to_one")
        output["published_counts_match"][name] = bool(
            len(merged) == 6 and merged.n_local.eq(merged.n_csv).all()
            and merged.n_positive_local.eq(merged.n_positive_csv).all())
    for q, group in demo.groupby("top_share"):
        output["demo_capture"].append({
            "top_share": float(q), "captured_sum": int(group.captured.sum()),
            "positive_sum": int(group.ignitions.sum()),
            "weighted_capture_rate": float(group.captured.sum() / group.ignitions.sum()),
        })
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2, allow_nan=False) + "\n")
    print(json.dumps({k: v for k, v in output.items()
                      if k not in {"events", "result_csv_hashes", "limits"}}, indent=2))


if __name__ == "__main__":
    main()
