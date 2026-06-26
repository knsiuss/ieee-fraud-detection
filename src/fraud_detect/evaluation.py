"""Model evaluation and comparison utilities.

Provides comprehensive evaluation reports (AUC, precision, recall, F1,
confusion matrix), optimal threshold selection via Youden's J statistic,
model comparison tables, and statistical significance testing with
McNemar's test.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)

@dataclass
class EvaluationReport:
    """Comprehensive evaluation result for a single model.

    Attributes
    ----------
    model_name:
        Human-readable model name.
    auc:
        ROC-AUC score.
    average_precision:
        Average precision (PR-AUC).
    f1:
        F1 score at the best threshold.
    precision:
        Precision at the best threshold.
    recall:
        Recall at the best threshold.
    accuracy:
        Accuracy at the best threshold.
    confusion_matrix:
        2×2 confusion matrix at the best threshold.
    best_threshold:
        Optimal decision threshold (Youden's J).
    youden_index:
        Youden's J statistic at the best threshold.
    """

    model_name: str
    auc: float
    average_precision: float
    f1: float
    precision: float
    recall: float
    accuracy: float
    confusion_matrix: np.ndarray
    best_threshold: float
    youden_index: float

def find_best_threshold(
    y_true: pd.Series | np.ndarray,
    y_pred_proba: np.ndarray,
    n_thresholds: int = 1000,
) -> tuple[float, float]:
    """Find the optimal decision threshold via Youden's J statistic.

    Youden's J = sensitivity + specificity - 1. The threshold maximising J
    balances true-positive and true-negative rates.

    Parameters
    ----------
    y_true:
        Ground-truth binary labels.
    y_pred_proba:
        Predicted probabilities for the positive class.
    n_thresholds:
        Number of candidate thresholds to evaluate.

    Returns
    -------
    tuple[float, float]
        ``(best_threshold, youden_index)``.

    Examples
    --------
    >>> import numpy as np, pandas as pd
    >>> rng = np.random.default_rng(42)
    >>> y = pd.Series(rng.integers(0, 2, 100))
    >>> pred = rng.uniform(0, 1, 100)
    >>> threshold, j = find_best_threshold(y, pred)
    >>> 0.0 <= threshold <= 1.0
    True
    >>> 0.0 <= j <= 1.0
    True
    """
    from sklearn.metrics import roc_curve

    fpr, tpr, thresholds = roc_curve(y_true, y_pred_proba)
    youden = tpr - fpr
    best_idx = int(np.argmax(youden))
    return float(thresholds[best_idx]), float(youden[best_idx])

def compute_evaluation(
    y_true: pd.Series | np.ndarray,
    y_pred_proba: np.ndarray,
    model_name: str = "model",
) -> EvaluationReport:
    """Compute a comprehensive evaluation report for a binary classifier.

    Parameters
    ----------
    y_true:
        Ground-truth binary labels.
    y_pred_proba:
        Predicted probabilities for the positive class.
    model_name:
        Label for the report (used in comparison tables).

    Returns
    -------
    EvaluationReport
        Dataclass with all computed metrics.

    Raises
    ------
    ValueError
        If fewer than two distinct classes are present in ``y_true``.

    Examples
    --------
    >>> import numpy as np, pandas as pd
    >>> rng = np.random.default_rng(42)
    >>> y = pd.Series(rng.integers(0, 2, 100))
    >>> pred = rng.uniform(0, 1, 100)
    >>> report = compute_evaluation(y, pred, \"test\")
    >>> report.model_name
    'test'
    >>> isinstance(report.auc, float)
    True
    """
    from sklearn.metrics import average_precision_score

    unique_classes = np.unique(y_true)
    if len(unique_classes) < 2:
        msg = f"y_true must contain both classes 0 and 1; got {unique_classes}"
        raise ValueError(msg)

    threshold, youden = find_best_threshold(y_true, y_pred_proba)
    y_pred_binary = (y_pred_proba >= threshold).astype(int)

    tn, fp, fn, tp = confusion_matrix(y_true, y_pred_binary).ravel()

    return EvaluationReport(
        model_name=model_name,
        auc=float(roc_auc_score(y_true, y_pred_proba)),
        average_precision=float(average_precision_score(y_true, y_pred_proba)),
        f1=float(f1_score(y_true, y_pred_binary, zero_division=0)),
        precision=float(precision_score(y_true, y_pred_binary, zero_division=0)),
        recall=float(recall_score(y_true, y_pred_binary, zero_division=0)),
        accuracy=float(accuracy_score(y_true, y_pred_binary)),
        confusion_matrix=np.array([[tn, fp], [fn, tp]]),
        best_threshold=threshold,
        youden_index=youden,
    )

def compare_models(
    reports: dict[str, EvaluationReport],
) -> pd.DataFrame:
    """Combine multiple ``EvaluationReport`` objects into a sorted comparison table.

    Parameters
    ----------
    reports:
        Mapping from model name to its ``EvaluationReport``.

    Returns
    -------
    pd.DataFrame
        Columns: ``model``, ``auc``, ``avg_precision``, ``f1``, ``precision``,
        ``recall``, ``best_threshold``. Sorted by AUC descending.

    Examples
    --------
    >>> import numpy as np, pandas as pd
    >>> rng = np.random.default_rng(42)
    >>> y = pd.Series(rng.integers(0, 2, 100))
    >>> pred = rng.uniform(0, 1, 100)
    >>> r1 = compute_evaluation(y, pred, \"A\")
    >>> r2 = compute_evaluation(y, pred, \"B\")
    >>> df = compare_models({\"A\": r1, \"B\": r2})
    >>> list(df.columns)
    ['model', 'auc', 'avg_precision', 'f1', 'precision', 'recall', 'best_threshold']
    """
    records = [
        {
            "model": name,
            "auc": round(report.auc, 5),
            "avg_precision": round(report.average_precision, 5),
            "f1": round(report.f1, 5),
            "precision": round(report.precision, 5),
            "recall": round(report.recall, 5),
            "best_threshold": round(report.best_threshold, 4),
        }
        for name, report in reports.items()
    ]
    return (
        pd.DataFrame(records)
        .sort_values("auc", ascending=False)
        .reset_index(drop=True)
    )

def mcnemar_test(
    preds_model1: np.ndarray,
    preds_model2: np.ndarray,
    y_true: pd.Series | np.ndarray,
) -> dict[str, float | int | str]:
    """McNemar's test for statistical significance between two classifiers.

    Tests the null hypothesis that the two models have equal error rates.
    A low p-value (e.g. < 0.05) indicates a statistically significant
    difference in predictions.

    Parameters
    ----------
    preds_model1:
        Binary predictions from model 1 (already thresholded).
    preds_model2:
        Binary predictions from model 2 (already thresholded).
    y_true:
        Ground-truth binary labels.

    Returns
    -------
    dict[str, float | int | str]
        Dictionary with keys ``statistic`` (chi-squared), ``p_value``,
        ``n_total``, ``n_discordant``, and ``conclusion``.

    Examples
    --------
    >>> import numpy as np, pandas as pd
    >>> rng = np.random.default_rng(42)
    >>> y = pd.Series(rng.integers(0, 2, 200))
    >>> m1 = rng.integers(0, 2, 200)
    >>> m2 = rng.integers(0, 2, 200)
    >>> result = mcnemar_test(m1, m2, y)
    >>> sorted(result.keys())
    ['conclusion', 'n_discordant', 'n_total', 'p_value', 'statistic']
    """
    from scipy.stats import chi2

    # Discordant pairs: model1 wrong & model2 right, or model1 right & model2 wrong
    wrong1 = preds_model1 != y_true
    wrong2 = preds_model2 != y_true

    n10 = int(np.sum(wrong1 & ~wrong2))  # model1 wrong, model2 correct
    n01 = int(np.sum(~wrong1 & wrong2))  # model1 correct, model2 wrong
    n_total = n10 + n01

    if n_total == 0:
        return {
            "statistic": 0.0,
            "p_value": 1.0,
            "n_total": int(len(y_true)),
            "n_discordant": 0,
            "conclusion": "Models are identical",
        }

    statistic = float((abs(n10 - n01) - 1) ** 2 / n_total)
    p_value = float(1.0 - chi2.cdf(statistic, df=1))
    conclusion = "Significant difference (p < 0.05)" if p_value < 0.05 else "No significant difference"

    return {
        "statistic": round(statistic, 4),
        "p_value": round(p_value, 5),
        "n_total": int(len(y_true)),
        "n_discordant": n_total,
        "conclusion": conclusion,
    }
