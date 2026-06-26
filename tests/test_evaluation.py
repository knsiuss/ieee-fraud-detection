"""Tests for the evaluation module (fraud_detect.evaluation).

Uses synthetic binary data to verify metric computation, threshold
optimisation, model comparison, and McNemar's test.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from fraud_detect import evaluation as ev


@pytest.fixture
def binary_data() -> tuple[pd.Series, np.ndarray]:
    """Balanced binary data for evaluation tests."""
    rng = np.random.default_rng(42)
    n = 500
    y_true = pd.Series(rng.integers(0, 2, n))
    y_pred_proba = np.clip(y_true.astype(float) + rng.normal(0, 0.3, n), 0, 1)
    return y_true, y_pred_proba


# --------------------------------------------------------------------------- #
# find_best_threshold
# --------------------------------------------------------------------------- #


def test_find_best_threshold_returns_float(binary_data):
    y_true, y_pred_proba = binary_data
    threshold, youden = ev.find_best_threshold(y_true, y_pred_proba)
    assert isinstance(threshold, float)
    assert isinstance(youden, float)
    assert 0.0 <= threshold <= 1.0
    assert 0.0 <= youden <= 1.0


def test_find_best_threshold_perfect_predictions():
    y_true = pd.Series([0, 0, 1, 1])
    y_pred = np.array([0.1, 0.2, 0.9, 0.8])
    threshold, youden = ev.find_best_threshold(y_true, y_pred)
    assert threshold > 0.0
    assert youden > 0.0


# --------------------------------------------------------------------------- #
# compute_evaluation
# --------------------------------------------------------------------------- #


def test_compute_evaluation_returns_report(binary_data):
    y_true, y_pred_proba = binary_data
    report = ev.compute_evaluation(y_true, y_pred_proba, model_name="test_model")
    assert report.model_name == "test_model"
    assert 0.0 <= report.auc <= 1.0
    assert 0.0 <= report.average_precision <= 1.0
    assert 0.0 <= report.f1 <= 1.0
    assert 0.0 <= report.precision <= 1.0
    assert 0.0 <= report.recall <= 1.0
    assert 0.0 <= report.accuracy <= 1.0
    assert report.confusion_matrix.shape == (2, 2)


def test_compute_evaluation_raises_on_single_class():
    y_true = pd.Series([0, 0, 0])
    y_pred = np.array([0.1, 0.2, 0.3])
    with pytest.raises(ValueError, match="must contain both classes"):
        ev.compute_evaluation(y_true, y_pred)


# --------------------------------------------------------------------------- #
# EvaluationReport dataclass
# --------------------------------------------------------------------------- #


def test_evaluation_report_fields():
    report = ev.EvaluationReport(
        model_name="test",
        auc=0.9,
        average_precision=0.85,
        f1=0.8,
        precision=0.75,
        recall=0.85,
        accuracy=0.8,
        confusion_matrix=np.array([[100, 10], [20, 70]]),
        best_threshold=0.5,
        youden_index=0.6,
    )
    assert report.auc == 0.9
    assert report.confusion_matrix[0, 0] == 100


# --------------------------------------------------------------------------- #
# compare_models
# --------------------------------------------------------------------------- #


def test_compare_models_returns_dataframe(binary_data):
    y_true, y_pred = binary_data
    r1 = ev.compute_evaluation(y_true, y_pred, "Model A")
    r2 = ev.compute_evaluation(y_true, y_pred + 0.05, "Model B")
    df = ev.compare_models({"A": r1, "B": r2})
    assert isinstance(df, pd.DataFrame)
    assert list(df.columns) == [
        "model", "auc", "avg_precision", "f1", "precision", "recall", "best_threshold"
    ]
    assert len(df) == 2


def test_compare_models_sorted_by_auc(binary_data):
    y_true, y_pred = binary_data
    r_bad = ev.compute_evaluation(y_true, np.full_like(y_pred, 0.5), "Bad")
    r_good = ev.compute_evaluation(y_true, y_pred, "Good")
    df = ev.compare_models({"Bad": r_bad, "Good": r_good})
    assert df.iloc[0]["model"] == "Good"


# --------------------------------------------------------------------------- #
# mcnemar_test
# --------------------------------------------------------------------------- #


@pytest.fixture
def binary_classification_data():
    rng = np.random.default_rng(42)
    n = 500
    y_true = pd.Series(rng.integers(0, 2, n))
    # Two models with slightly different predictions
    preds_1 = y_true.values.copy()
    preds_2 = y_true.values.copy()
    # Flip some predictions
    flip_idx = rng.choice(n, size=30, replace=False)
    preds_2[flip_idx] = 1 - preds_2[flip_idx]
    return y_true, preds_1, preds_2


def test_mcnemar_test_returns_dict(binary_classification_data):
    y_true, preds_1, preds_2 = binary_classification_data
    result = ev.mcnemar_test(preds_1, preds_2, y_true)
    expected_keys = {"statistic", "p_value", "n_total", "n_discordant", "conclusion"}
    assert expected_keys.issubset(result.keys())
    assert result["n_total"] == 500
    assert result["statistic"] >= 0.0


def test_mcnemar_test_identical_models():
    y_true = pd.Series([0, 0, 1, 1, 0, 1])
    preds = np.array([0, 0, 1, 1, 0, 1])
    result = ev.mcnemar_test(preds, preds, y_true)
    assert result["conclusion"] == "Models are identical"
    assert result["n_discordant"] == 0
