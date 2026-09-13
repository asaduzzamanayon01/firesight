"""FS-19: Probability calibration with isotonic regression.

Owner: Ayon
Jira: FS-19 (Probability calibration with isotonic regression)

WHY CALIBRATION IS A DELIVERABLE, NOT A NICETY
----------------------------------------------
`scale_pos_weight` fixes the imbalance problem for RANKING, but it destroys
the probabilities: the model is trained as though positives were ~300x more
common than they are, so its outputs are wildly inflated. A raw score of 0.6
does not mean a 60% chance of ignition.

That is fatal for the actual use case. DFES allocating crews needs "this cell
has a 5% chance" to mean 5%, so that risk can be summed and compared across
cells. A ranking alone cannot support resource allocation.

Isotonic regression learns a monotonic map from raw score -> true frequency.
Monotonic means the RANKING IS PRESERVED EXACTLY, so PR-AUC and ROC-AUC are
unchanged; only Brier score and the reliability curve improve. If a marker
asks "doesn't calibration hurt your PR-AUC?", that is the answer.

CRITICAL: calibration is fitted on OUT-OF-FOLD predictions. Fitting it on
in-sample predictions produces a calibrator that is itself overfitted and
looks perfect in testing and fails in deployment.
"""
from __future__ import annotations

import logging
import pickle

import numpy as np
import pandas as pd

from src.config import CFG
from src.evaluation.metrics import evaluate, plot_reliability

log = logging.getLogger(__name__)


class IsotonicCalibrator:
    """Thin wrapper so the calibrator persists and reloads as one object."""

    def __init__(self):
        from sklearn.isotonic import IsotonicRegression
        self.iso = IsotonicRegression(out_of_bounds="clip", y_min=0.0, y_max=1.0)
        self.fitted_ = False

    def fit(self, y_prob_raw: np.ndarray, y_true: np.ndarray) -> IsotonicCalibrator:
        self.iso.fit(np.asarray(y_prob_raw, dtype=float),
                     np.asarray(y_true, dtype=float))
        self.fitted_ = True
        return self

    def transform(self, y_prob_raw: np.ndarray) -> np.ndarray:
        if not self.fitted_:
            raise RuntimeError("call fit() first")
        return np.clip(self.iso.predict(np.asarray(y_prob_raw, dtype=float)), 0.0, 1.0)

    def save(self, path) -> None:
        with open(path, "wb") as f:
            pickle.dump(self, f)

    @staticmethod
    def load(path) -> IsotonicCalibrator:
        with open(path, "rb") as f:
            return pickle.load(f)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    proc = CFG.path("processed")
    oof = pd.read_parquet(proc / "oof_predictions.parquet").dropna(subset=["y_prob"])

    y, raw = oof["ignition"].to_numpy(), oof["y_prob"].to_numpy()

    # Hold out the final season so we can report calibration on data the
    # calibrator has never seen. Fitting and reporting on the same rows would
    # be circular.
    seasons = sorted(oof["season"].unique())
    holdout = seasons[-1]
    tr, te = oof["season"] != holdout, oof["season"] == holdout

    cal = IsotonicCalibrator().fit(raw[tr.to_numpy()], y[tr.to_numpy()])
    adj_te = cal.transform(raw[te.to_numpy()])

    before = evaluate(y[te.to_numpy()], raw[te.to_numpy()])
    after = evaluate(y[te.to_numpy()], adj_te)

    print(f"\n=== CALIBRATION (held-out season {holdout}) ===")
    print(f"before  {before}")
    print(f"after   {after}")
    print(f"\nBrier improved {(1 - after.brier/before.brier)*100:+.1f}%")
    print(f"PR-AUC changed {(after.pr_auc - before.pr_auc):+.6f} "
          f"(should be ~0: isotonic is monotonic, so ranking is preserved)")

    fig = CFG.path("figures")
    plot_reliability(y[te.to_numpy()], raw[te.to_numpy()],
                     fig / "calibration_before.png", "Before calibration")
    plot_reliability(y[te.to_numpy()], adj_te,
                     fig / "calibration_after.png", "After isotonic calibration")

    # Refit on everything for the deployed artefact
    final = IsotonicCalibrator().fit(raw, y)
    final.save(CFG.path("models") / "calibrator.pkl")

    oof["y_prob_calibrated"] = final.transform(raw)
    oof.to_parquet(proc / "oof_predictions_calibrated.parquet", index=False)
    print(f"\ncalibrator -> {CFG.path('models') / 'calibrator.pkl'}")
    print(f"figures -> {fig}\n")


if __name__ == "__main__":
    main()
