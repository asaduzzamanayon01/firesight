"""FS-18: Train LightGBM and log everything to MLflow.

Owner: Ayon
Jira: FS-18 (Train LightGBM v1 and log to MLflow)

WHY GRADIENT BOOSTING IS THE STARTING POINT (not the final answer)
------------------------------------------------------------------
1. FAST. ~3-5 min per run on 4.5M rows on a laptop. ConvLSTM is 2-3 hours on
   a GPU. Fast training means we can test 50 feature variants in a day, which
   is where the actual gains live on tabular problems.
2. IMBALANCE. `scale_pos_weight` reweights the loss so the ~300:1 negative
   majority stops dominating the gradient. Computed from the data below, never
   hardcoded.
3. EXPLAINABLE. Tree models give exact SHAP values in near-linear time.
   Every flagged cell can carry a reason, which the dashboard requires.

The model comparison in Sprint 3 (FS-19) runs LightGBM, Random Forest and
Logistic Regression through this same harness. Whichever wins on held-out
PR-AUC is the deliverable. This file is the starting point, not a commitment.

Run:
    python -m src.models.train_lgbm
    mlflow ui          # then open http://localhost:5000
"""
from __future__ import annotations

import logging

import numpy as np
import pandas as pd

from src.config import CFG, mlflow_uri
from src.evaluation.metrics import (
    evaluate,
    plot_pr_curve,
    plot_reliability,
    precision_at_k,
    recall_at_k,
)
from src.evaluation.splits import leave_one_season_out

log = logging.getLogger(__name__)


def feature_columns(df: pd.DataFrame) -> list[str]:
    """Everything numeric that is not an identifier or the label.

    Guarding this in one place is how we stop `n_ignitions` (which is the
    label in disguise) sneaking into the feature matrix.
    """
    excluded = set(CFG.model.exclude_cols) | {"n_ignitions"}
    return [
        c for c in df.columns
        if c not in excluded and pd.api.types.is_numeric_dtype(df[c])
    ]


def compute_scale_pos_weight(y: np.ndarray) -> float:
    """negatives / positives. With a 0.3% positive rate this is ~330."""
    pos = int(np.sum(y))
    neg = int(len(y) - pos)
    if pos == 0:
        raise ValueError("no positives in training fold")
    return neg / pos


def train_fold(X_tr, y_tr, X_te, y_te, params: dict):
    import lightgbm as lgb

    spw = compute_scale_pos_weight(y_tr)
    p = dict(params)
    early = p.pop("early_stopping_rounds", 100)
    p.update(scale_pos_weight=spw, random_state=CFG.project.random_seed,
             n_jobs=-1, verbose=-1)

    model = lgb.LGBMClassifier(**p)
    model.fit(
        X_tr, y_tr,
        eval_set=[(X_te, y_te)],
        eval_metric="average_precision",
        callbacks=[lgb.early_stopping(early, verbose=False),
                   lgb.log_evaluation(0)],
    )
    return model, spw


def run() -> pd.DataFrame:
    import mlflow

    proc = CFG.path("processed")
    df = pd.read_parquet(proc / "cell_days_features.parquet")
    df["date"] = pd.to_datetime(df["date"])

    feats = feature_columns(df)
    log.info("%d features: %s", len(feats), feats[:8])

    mlflow.set_tracking_uri(mlflow_uri())
    mlflow.set_experiment(CFG.mlflow.experiment_name)

    params = CFG.model.lightgbm.to_dict()
    rows = []

    with mlflow.start_run(run_name="lgbm_loso"):
        mlflow.log_params(params)
        mlflow.log_param("n_features", len(feats))
        mlflow.log_param("cv_scheme", CFG.evaluation.cv_scheme)
        mlflow.log_param("n_rows", len(df))
        mlflow.log_param("positive_rate", float(df["ignition"].mean()))

        oof = np.full(len(df), np.nan)

        for season, tr, te in leave_one_season_out(df):
            X_tr, y_tr = df.iloc[tr][feats], df.iloc[tr]["ignition"].to_numpy()
            X_te, y_te = df.iloc[te][feats], df.iloc[te]["ignition"].to_numpy()

            model, spw = train_fold(X_tr, y_tr, X_te, y_te, params)
            p = model.predict_proba(X_te)[:, 1]
            oof[te] = p

            s = evaluate(y_te, p)
            log.info("held-out %s | %s", season, s)
            rows.append({"season": season, "scale_pos_weight": spw,
                         "best_iteration": model.best_iteration_, **s.to_dict()})
            for k, v in s.to_dict().items():
                if isinstance(v, float):
                    mlflow.log_metric(f"{season}_{k}", v)

        results = pd.DataFrame(rows)
        mlflow.log_metric("mean_pr_auc", float(results["pr_auc"].mean()))
        mlflow.log_metric("std_pr_auc", float(results["pr_auc"].std()))
        mlflow.log_metric("mean_brier", float(results["brier"].mean()))

        # Operational metrics: top-k is what a DFES planner actually acts on
        mask = ~np.isnan(oof)
        for k in (50, 100, 500):
            mlflow.log_metric(f"precision_at_{k}",
                              precision_at_k(df["ignition"][mask], oof[mask], k))
            mlflow.log_metric(f"recall_at_{k}",
                              recall_at_k(df["ignition"][mask], oof[mask], k))

        fig = CFG.path("figures")
        plot_reliability(df["ignition"][mask], oof[mask],
                         fig / "lgbm_reliability.png",
                         "LightGBM (uncalibrated): reliability")
        plot_pr_curve(df["ignition"][mask], oof[mask],
                      fig / "lgbm_pr_curve.png",
                      "LightGBM: precision-recall")
        mlflow.log_artifacts(str(fig), "figures")

        # Persist out-of-fold predictions - calibrate.py consumes these
        oof_df = df[["cell_id", "date", "season", "ignition"]].copy()
        oof_df["y_prob"] = oof
        oof_df.to_parquet(proc / "oof_predictions.parquet", index=False)

        # Final model on all data, for the dashboard
        final, _ = train_fold(df[feats], df["ignition"].to_numpy(),
                              df[feats], df["ignition"].to_numpy(), params)
        import joblib
        mp = CFG.path("models") / "lgbm_final.pkl"
        joblib.dump({"model": final, "features": feats}, mp)
        mlflow.log_artifact(str(mp), "model")

    return results


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    results = run()
    out = CFG.path("reports") / "lgbm_cv.csv"
    results.to_csv(out, index=False)

    print("\n=== LIGHTGBM (leave-one-season-out) ===")
    print(results[["season", "pr_auc", "pr_auc_lift", "brier", "brier_skill"]]
          .to_string(index=False))
    print(f"\nmean PR-AUC {results['pr_auc'].mean():.4f} "
          f"+/- {results['pr_auc'].std():.4f}")

    base = CFG.path("reports") / "baseline_cv.csv"
    if base.exists():
        b = pd.read_csv(base)["pr_auc"].mean()
        m = results["pr_auc"].mean()
        verdict = "BEATS" if m > b else "DOES NOT BEAT"
        print(f"\nBaseline PR-AUC {b:.4f} -> LightGBM {verdict} baseline "
              f"({m/b:.2f}x)")
    print("\nRun `mlflow ui` to inspect.\n")


if __name__ == "__main__":
    main()
