"""Tests for the evaluation harness.

These are the tests that stop us shipping a meaningless result. The most
important one is test_accuracy_trap, which encodes the core project insight
as an executable assertion.
"""
import numpy as np
import pytest

from src.evaluation.metrics import (
    evaluate,
    precision_at_k,
    recall_at_k,
    reliability_curve,
)

RNG = np.random.default_rng(0)


def make_imbalanced(n=20_000, rate=0.003, signal=1.0):
    y = RNG.binomial(1, rate, n)
    noise = RNG.normal(0, 1, n)
    p = 1 / (1 + np.exp(-(signal * y * 3 + noise)))
    return y, p


def test_perfect_model_scores_one():
    y = np.array([0, 0, 0, 1, 0, 0, 1, 0])
    s = evaluate(y, y.astype(float))
    assert s.pr_auc == pytest.approx(1.0)
    assert s.brier == pytest.approx(0.0)


def test_random_model_pr_auc_approximates_base_rate():
    """The key property of PR-AUC: random == positive rate, not 0.5."""
    y = RNG.binomial(1, 0.01, 50_000)
    p = RNG.random(50_000)
    s = evaluate(y, p)
    assert s.pr_auc == pytest.approx(0.01, abs=0.006)
    assert s.pr_auc_lift == pytest.approx(1.0, abs=0.6)


def test_accuracy_trap():
    """A constant 'never predict fire' model must score badly on our metrics.

    This is the whole reason accuracy is banned in this project. If this test
    ever fails, someone has changed the metrics to something that can be
    gamed by the majority class.
    """
    y = RNG.binomial(1, 0.003, 50_000)
    always_no = np.full(len(y), 1e-6)

    accuracy = ((always_no > 0.5).astype(int) == y).mean()
    assert accuracy > 0.99, "the trap: accuracy looks excellent"

    s = evaluate(y, always_no)
    assert s.pr_auc < 0.02, "PR-AUC must expose the useless model"
    assert s.brier_skill < 0.01, "Brier skill must show no skill over base rate"


def test_brier_skill_of_base_rate_forecast_is_zero():
    y = RNG.binomial(1, 0.05, 20_000)
    s = evaluate(y, np.full(len(y), y.mean()))
    assert s.brier_skill == pytest.approx(0.0, abs=1e-9)


def test_signal_beats_random():
    y, p = make_imbalanced(signal=1.0)
    y_r, p_r = make_imbalanced(signal=0.0)
    assert evaluate(y, p).pr_auc > evaluate(y_r, p_r).pr_auc


def test_rejects_logits():
    y = np.array([0, 1, 0, 1])
    with pytest.raises(ValueError, match="\\[0, 1\\]"):
        evaluate(y, np.array([-2.0, 3.0, 0.5, 1.2]))


def test_rejects_single_class():
    with pytest.raises(ValueError, match="only one class"):
        evaluate(np.zeros(10, dtype=int), np.full(10, 0.1))


def test_reliability_curve_is_monotone_for_calibrated_input():
    n = 100_000
    p = RNG.random(n) * 0.2
    y = RNG.binomial(1, p)
    pred, obs, cnt = reliability_curve(y, p, n_bins=8)
    assert cnt.sum() == n
    # A perfectly calibrated forecast should track the diagonal
    assert np.corrcoef(pred, obs)[0, 1] > 0.9


def test_precision_and_recall_at_k():
    y = np.array([1, 1, 0, 0, 0, 0, 0, 0, 0, 0])
    p = np.array([0.9, 0.8, 0.7, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1])
    assert precision_at_k(y, p, 2) == pytest.approx(1.0)
    assert recall_at_k(y, p, 2) == pytest.approx(1.0)
    assert precision_at_k(y, p, 4) == pytest.approx(0.5)
