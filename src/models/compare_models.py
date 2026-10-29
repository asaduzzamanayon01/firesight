"""FS-20: Systematic model comparison. THIS IS THE FILE THAT ANSWERS YOUR
SUPERVISOR'S "don't get stuck on gradient boosting" INSTRUCTION.

Owner: Ayon
Jira: FS-20 (Compare candidate models on held-out PR-AUC)

Every candidate goes through the SAME harness: same features, same
leave-one-season-out folds, same metrics, same MLflow experiment. Model
selection is then a data-driven decision, not a preference.

Candidates:
    logistic      Regularised logistic regression. Linear reference point.
    random_forest Bagged trees. Different bias-variance trade-off to boosting.
    lightgbm      Gradient boosting. Our starting point.
    hist_gbm      sklearn's boosting, as an implementation cross-check.

ConvLSTM lives in src/models/convlstm.py because it needs gridded rasters
rather than a flat table, so it cannot share this harness directly. Its
results are compared on the same held-out seasons and the same metrics.
"""
from __future__ import annotations

import logging

import pandas as pd

from src.config import CFG, mlflow_uri
from src.evaluation.metrics import evaluate
from src.evaluation.splits import leave_one_season_out
from src.models.train_lgbm import compute_scale_pos_weight, feature_columns

log = logging.getLogger(__name__)


def build_candidates(spw: float) -> dict:
    """Instantiate every candidate with imbalance handling switched on."""
    import lightgbm as lgb
    from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
    from sklearn.impute import SimpleImputer
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import StandardScaler

    seed = CFG.project.random_seed
    p = CFG.model.lightgbm.to_dict()
    p.pop("early_stopping_rounds", None)
    mode = p.pop("class_weight", "none")
    # No early stopping here, so use a tree count close to what early stopping
    # picked in train_lgbm (22 to 111 on the synthetic data).
    p["n_estimators"] = 100

    return {
        # Linear models need imputation and scaling; trees do not.
        "logistic": Pipeline([
            ("impute", SimpleImputer(strategy="median")),
            ("scale", StandardScaler()),
            ("clf", LogisticRegression(
                max_iter=1000, class_weight="balanced", random_state=seed)),
        ]),
        "random_forest": RandomForestClassifier(
            n_estimators=300, min_samples_leaf=50, class_weight="balanced_subsample",
            n_jobs=-1, random_state=seed),
        "lightgbm": lgb.LGBMClassifier(
            **p, scale_pos_weight=spw if mode == "balanced" else 1.0, random_state=seed, n_jobs=-1, verbose=-1),
        "hist_gbm": HistGradientBoostingClassifier(
            max_iter=300, learning_rate=0.05, random_state=seed,
            class_weight="balanced"),
    }


def run(sample: int | None = None) -> pd.DataFrame:
    import mlflow

    df = pd.read_parquet(CFG.path("processed") / "cell_days_features.parquet")
    df["date"] = pd.to_datetime(df["date"])

    if sample and sample < len(df):
        # Stratified downsample: keep every positive, subsample the negatives.
        # Random Forest on millions of rows is hours; this makes the
        # comparison runnable in a sprint. Report the final winner on the
        # full data.
        pos = df[df["ignition"] == 1]
        neg = df[df["ignition"] == 0].sample(
            max(sample - len(pos), 1), random_state=CFG.project.random_seed)
        df = pd.concat([pos, neg]).sort_values(["season", "date"]).reset_index(drop=True)
        log.warning("SUBSAMPLED to %d rows (%d positives) for tractability. "
                    "Positive rate is now inflated - use this for RANKING "
                    "candidates only, not for headline numbers.",
                    len(df), len(pos))
    feats = feature_columns(df)

    mlflow.set_tracking_uri(mlflow_uri())
    mlflow.set_experiment(CFG.mlflow.experiment_name)

    rows = []
    for name in build_candidates(1.0):
        with mlflow.start_run(run_name=f"compare_{name}"):
            mlflow.log_param("model", name)
            fold_scores = []
            for season, tr, te in leave_one_season_out(df):
                X_tr = df.iloc[tr][feats]
                y_tr = df.iloc[tr]["ignition"].to_numpy()
                X_te = df.iloc[te][feats]
                y_te = df.iloc[te]["ignition"].to_numpy()

                model = build_candidates(compute_scale_pos_weight(y_tr))[name]
                # RF and logistic cannot handle NaN; trees in LightGBM can.
                if name in ("random_forest",):
                    X_tr = X_tr.fillna(X_tr.median())
                    X_te = X_te.fillna(X_tr.median())

                model.fit(X_tr, y_tr)
                p = model.predict_proba(X_te)[:, 1]
                s = evaluate(y_te, p)
                fold_scores.append(s.to_dict())
                log.info("%-14s %s | %s", name, season, s)

            summary = pd.DataFrame(fold_scores).mean(numeric_only=True)
            for k, v in summary.items():
                mlflow.log_metric(k, float(v))
            rows.append({"model": name, **summary.to_dict()})

    return pd.DataFrame(rows).sort_values("pr_auc", ascending=False)


def main() -> None:
    import argparse
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", type=int, default=None,
                    help="Stratified subsample size. Use ~200000 for a fast pass.")
    args = ap.parse_args()
    results = run(args.sample)
    out = CFG.path("reports") / "model_comparison.csv"
    results.to_csv(out, index=False)

    print("\n=== MODEL COMPARISON (mean over held-out seasons) ===")
    print(results[["model", "pr_auc", "pr_auc_lift", "brier", "roc_auc"]]
          .to_string(index=False))
    best = results.iloc[0]
    print(f"\nWinner on PR-AUC: {best['model']} ({best['pr_auc']:.4f})")
    print("This is the evidence for our model-selection decision.\n")


if __name__ == "__main__":
    main()
