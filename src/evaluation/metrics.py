"""Evaluation metrics for a severely imbalanced binary problem.

Owner: Ayon
Jira: FS-16 (Build evaluation harness: PR-AUC, Brier, reliability curve)

ACCURACY IS BANNED IN THIS PROJECT.
With a 0.3% positive rate, "always predict no fire" scores 99.7% accuracy and
catches zero fires. Every function here exists to make that failure visible.

WHAT EACH METRIC ANSWERS
------------------------
pr_auc        Can we RANK cells? Of the cells we flag, how many burn?
              No true-negative term, so the 99.7% majority cannot flatter it.
              Random baseline = the positive rate itself (~0.003), NOT 0.5.

roc_auc       Reported only for comparison with published papers. It looks
              impressive on imbalanced data and is close to meaningless here.

brier         Are the PROBABILITIES right? Mean squared error of p vs outcome.
              Lower is better. Decomposes into reliability + resolution.

reliability   When we say 20%, does it burn 20% of the time? This is what
              makes the forecast usable for resource allocation rather than
              just a ranking.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    roc_auc_score,
)


@dataclass
class Scores:
    pr_auc: float
    pr_auc_lift: float      # how many times better than random
    roc_auc: float
    brier: float
    brier_skill: float      # vs a constant base-rate forecast
    positive_rate: float
    n: int
    n_positive: int

    def to_dict(self) -> dict:
        return asdict(self)

    def __str__(self) -> str:
        return (
            f"PR-AUC {self.pr_auc:.4f} ({self.pr_auc_lift:.1f}x random)  "
            f"Brier {self.brier:.5f} (BSS {self.brier_skill:+.3f})  "
            f"ROC-AUC {self.roc_auc:.4f}  "
            f"n={self.n:,} pos={self.n_positive:,} ({self.positive_rate*100:.3f}%)"
        )


def evaluate(y_true: np.ndarray, y_prob: np.ndarray) -> Scores:
    """Compute the full score set. y_prob must be probabilities, not labels."""
    y_true = np.asarray(y_true).astype(int)
    y_prob = np.asarray(y_prob, dtype=float)

    if y_true.shape != y_prob.shape:
        raise ValueError(f"shape mismatch: {y_true.shape} vs {y_prob.shape}")
    if not ((y_prob >= 0) & (y_prob <= 1)).all():
        raise ValueError("y_prob must lie in [0, 1] - did you pass logits?")

    base = y_true.mean()
    if base in (0.0, 1.0):
        raise ValueError("y_true has only one class - cannot evaluate")

    pr = average_precision_score(y_true, y_prob)
    brier = brier_score_loss(y_true, y_prob)
    brier_ref = brier_score_loss(y_true, np.full_like(y_prob, base))

    return Scores(
        pr_auc=float(pr),
        pr_auc_lift=float(pr / base),
        roc_auc=float(roc_auc_score(y_true, y_prob)),
        brier=float(brier),
        # Brier Skill Score: 1 = perfect, 0 = no better than always predicting
        # the base rate, negative = worse than that.
        brier_skill=float(1 - brier / brier_ref) if brier_ref > 0 else float("nan"),
        positive_rate=float(base),
        n=int(y_true.size),
        n_positive=int(y_true.sum()),
    )


def reliability_curve(y_true: np.ndarray, y_prob: np.ndarray, n_bins: int = 10,
                      strategy: str = "quantile"):
    """Observed frequency vs predicted probability, per bin.

    strategy='quantile' puts equal COUNTS in each bin. With a 0.3% positive
    rate, uniform-width bins leave the top bins nearly empty and the curve
    becomes noise, so quantile is the sane default here.

    Returns (mean_predicted, observed_frequency, bin_counts).
    """
    y_true = np.asarray(y_true).astype(int)
    y_prob = np.asarray(y_prob, dtype=float)

    if strategy == "quantile":
        edges = np.unique(np.quantile(y_prob, np.linspace(0, 1, n_bins + 1)))
    else:
        edges = np.linspace(0, 1, n_bins + 1)

    idx = np.clip(np.digitize(y_prob, edges[1:-1]), 0, len(edges) - 2)

    pred, obs, cnt = [], [], []
    for b in range(len(edges) - 1):
        m = idx == b
        if m.sum() == 0:
            continue
        pred.append(y_prob[m].mean())
        obs.append(y_true[m].mean())
        cnt.append(int(m.sum()))
    return np.array(pred), np.array(obs), np.array(cnt)


def precision_at_k(y_true: np.ndarray, y_prob: np.ndarray, k: int) -> float:
    """Of the top-k riskiest cells, what fraction actually ignited?

    This is the metric DFES would actually care about: if we can pre-position
    crews against 50 cells tomorrow, how many real fires do those 50 cover?
    Far more interpretable to a non-ML stakeholder than PR-AUC.
    """
    y_true = np.asarray(y_true).astype(int)
    order = np.argsort(-np.asarray(y_prob, dtype=float))[:k]
    return float(y_true[order].mean())


def recall_at_k(y_true: np.ndarray, y_prob: np.ndarray, k: int) -> float:
    """Of all fires that happened, what fraction fell in the top-k cells?"""
    y_true = np.asarray(y_true).astype(int)
    total = y_true.sum()
    if total == 0:
        return float("nan")
    order = np.argsort(-np.asarray(y_prob, dtype=float))[:k]
    return float(y_true[order].sum() / total)


def plot_reliability(y_true, y_prob, out_path, title="Reliability"):
    """Save a reliability diagram with a histogram of predictions underneath."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    pred, obs, cnt = reliability_curve(y_true, y_prob)
    fig, (ax, ax2) = plt.subplots(
        2, 1, figsize=(6, 7), height_ratios=[3, 1], sharex=True
    )
    lim = max(pred.max(), obs.max()) * 1.1
    ax.plot([0, lim], [0, lim], "--", color="grey", lw=1, label="perfect calibration")
    ax.plot(pred, obs, "o-", color="#b45309", label="model")
    ax.set_ylabel("Observed ignition frequency")
    ax.set_title(title)
    ax.legend()
    ax.grid(alpha=0.3)

    ax2.bar(pred, cnt, width=lim / 40, color="#16202e")
    ax2.set_yscale("log")
    ax2.set_xlabel("Predicted probability")
    ax2.set_ylabel("Count (log)")
    ax2.grid(alpha=0.3)

    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    return out_path


def plot_pr_curve(y_true, y_prob, out_path, title="Precision-Recall"):
    """PR curve with the random-baseline line drawn at the positive rate."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from sklearn.metrics import precision_recall_curve

    p, r, _ = precision_recall_curve(y_true, y_prob)
    base = np.asarray(y_true).mean()

    fig, ax = plt.subplots(figsize=(6, 5))
    ax.plot(r, p, color="#b45309", lw=2,
            label=f"model (AP={average_precision_score(y_true, y_prob):.4f})")
    ax.axhline(base, ls="--", color="grey", lw=1,
               label=f"random (={base:.4f})")
    ax.set_xlabel("Recall")
    ax.set_ylabel("Precision")
    ax.set_title(title)
    ax.legend()
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    return out_path
