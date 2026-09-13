"""FS-21: SHAP explanations for flagged cells.

Owner: Ayon
Jira: FS-21 (SHAP explanations for flagged cells)

WHY EVERY FORECAST CARRIES A REASON
-----------------------------------
A bare "this cell is 18% likely to ignite" is not actionable and not
auditable. A planner needs to know WHY, and we need to know whether the model
learned fire science or an artefact.

SHAP assigns each feature a signed contribution to a single prediction, and
those contributions sum exactly to the prediction. So a cell at 18% might read:

    base rate            0.3%
    + 30-day dry spell  +7.1%
    + max temp 41C      +5.2%
    + 400m from powerline +3.8%
    - recent burn scar  -1.4%
    = 18.0%

For tree models SHAP values are exact and fast, which is one of the reasons
we started with gradient boosting rather than a neural network.

THIS IS ALSO OUR DEBUGGING TOOL. If `cell_id` or `month` shows up as a top
global feature, the model has memorised the grid rather than learned fire
behaviour, and we have a leakage problem to fix.
"""
from __future__ import annotations

import logging

import numpy as np
import pandas as pd

from src.config import CFG

log = logging.getLogger(__name__)


def compute_shap(model, X: pd.DataFrame, max_rows: int = 20_000):
    """TreeSHAP over a sample. Returns (shap_values, sampled_X)."""
    import shap

    if len(X) > max_rows:
        X = X.sample(max_rows, random_state=CFG.project.random_seed)
    explainer = shap.TreeExplainer(model)
    values = explainer.shap_values(X)
    # Older shap returns a list per class for binary problems
    if isinstance(values, list):
        values = values[1]
    return values, X


def global_importance(shap_values: np.ndarray, X: pd.DataFrame) -> pd.DataFrame:
    """Mean absolute SHAP per feature - the global ranking."""
    imp = np.abs(shap_values).mean(axis=0)
    return (
        pd.DataFrame({"feature": X.columns, "mean_abs_shap": imp})
        .sort_values("mean_abs_shap", ascending=False)
        .reset_index(drop=True)
    )


def explain_cell(shap_values: np.ndarray, X: pd.DataFrame, row: int,
                 top_n: int = 5) -> pd.DataFrame:
    """Per-cell explanation: the top_n drivers of one prediction."""
    contrib = pd.DataFrame({
        "feature": X.columns,
        "value": X.iloc[row].to_numpy(),
        "shap": shap_values[row],
    })
    contrib["abs"] = contrib["shap"].abs()
    return (contrib.sort_values("abs", ascending=False)
            .head(top_n).drop(columns="abs").reset_index(drop=True))


def leakage_check(importance: pd.DataFrame) -> list[str]:
    """Flag suspicious top features. Run this every time you retrain."""
    suspicious = {"cell_id", "n_ignitions", "event_id", "season"}
    hits = [f for f in importance.head(10)["feature"] if f in suspicious]
    if hits:
        log.error("LEAKAGE SUSPECTED: %s in top-10 features", hits)
    return hits


def plot_summary(shap_values, X, out_path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import shap

    shap.summary_plot(shap_values, X, show=False, max_display=15)
    plt.tight_layout()
    plt.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close()
    return out_path


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    import joblib

    bundle = joblib.load(CFG.path("models") / "lgbm_final.pkl")
    model, feats = bundle["model"], bundle["features"]

    df = pd.read_parquet(CFG.path("processed") / "cell_days_features.parquet")
    values, X = compute_shap(model, df[feats])

    imp = global_importance(values, X)
    imp.to_csv(CFG.path("reports") / "shap_importance.csv", index=False)

    print("\n=== GLOBAL FEATURE IMPORTANCE (mean |SHAP|) ===")
    print(imp.head(15).to_string(index=False))

    hits = leakage_check(imp)
    if hits:
        print(f"\n!! LEAKAGE WARNING: {hits} are top features. Investigate "
              f"before trusting any score. !!")
    else:
        print("\nLeakage check passed: no identifier columns in the top 10.")

    # Worked example for the report and the dashboard panel
    top_row = int(np.argmax(model.predict_proba(X)[:, 1]))
    print("\n=== EXAMPLE: highest-risk cell in the sample ===")
    print(explain_cell(values, X, top_row).to_string(index=False))

    out = plot_summary(values, X, CFG.path("figures") / "shap_summary.png")
    print(f"\nfigure -> {out}\n")


if __name__ == "__main__":
    main()
