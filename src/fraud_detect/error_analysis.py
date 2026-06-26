"""Error analysis and segmentation for binary classification models.

Provides tools to understand *where* a model fails: error rates segmented
by categorical features, distribution shifts between errors and correct
predictions, and quick inspection of the most confident false positives
and false negatives.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from . import config

logger = logging.getLogger(__name__)

@dataclass
class ErrorProfile:
    """Segmented error analysis for a binary classifier.

    Attributes
    ----------
    overall:
        Aggregate metrics (``error_rate``, ``n_errors``, ``n_total``,
        ``fp_rate``, ``fn_rate``).
    by_segment:
        Per-segment error rates (one row per segment level).
    worst_segments:
        Top-*n* segments with the highest error rate.
    feature_distribution_shift:
        For each numeric feature, the mean difference between error and
        correct predictions, or ``None`` if not computed.
    """

    overall: dict[str, float | int]
    by_segment: pd.DataFrame
    worst_segments: pd.DataFrame
    feature_distribution_shift: pd.DataFrame | None = None

def compute_error_profile(
    df: pd.DataFrame,
    y_true: pd.Series | np.ndarray,
    y_pred: np.ndarray,
    segment_cols: list[str] | None = None,
    top_n: int = 10,
) -> ErrorProfile:
    """Compute a full error profile with optional segmentation.

    Parameters
    ----------
    df:
        Original feature DataFrame (used for segmentation).
    y_true:
        Ground-truth binary labels.
    y_pred:
        Binary predictions (already thresholded).
    segment_cols:
        List of categorical columns to segment by. If ``None``, defaults to
        ``ProductCD``, ``DeviceType``, plus time-based features if present.
    top_n:
        Number of worst-performing segments to return.

    Returns
    -------
    ErrorProfile
        Dataclass with overall metrics, per-segment breakdown, worst segments,
        and optional feature distribution shift.

    Examples
    --------
    >>> import pandas as pd, numpy as np
    >>> rng = np.random.default_rng(42)
    >>> n = 100
    >>> df = pd.DataFrame({\"ProductCD\": rng.choice([\"W\", \"H\"], n),
    ...                    \"DeviceType\": rng.choice([\"desktop\", \"mobile\"], n)})
    >>> y_true = pd.Series(rng.integers(0, 2, n))
    >>> y_pred = rng.integers(0, 2, n)
    >>> profile = compute_error_profile(df, y_true, y_pred)
    >>> isinstance(profile.overall[\"error_rate\"], float)
    True
    >>> not profile.by_segment.empty
    True
    """
    segment_cols = segment_cols or _default_segment_cols(df)
    y_true = np.asarray(y_true)
    y_pred = np.asarray(y_pred)

    errors = (y_true != y_pred).astype(int)
    n_total = len(y_true)
    n_errors = int(errors.sum())
    error_rate = n_errors / n_total if n_total > 0 else 0.0

    # False-positive and false-negative rates
    fp = int(np.sum((y_pred == 1) & (y_true == 0)))
    fn = int(np.sum((y_pred == 0) & (y_true == 1)))
    fp_rate = fp / max(n_total, 1)
    fn_rate = fn / max(n_total, 1)

    overall: dict[str, float | int] = {
        "error_rate": round(error_rate, 5),
        "n_errors": n_errors,
        "n_total": n_total,
        "fp": fp,
        "fn": fn,
        "fp_rate": round(fp_rate, 5),
        "fn_rate": round(fn_rate, 5),
    }

    # Per-segment error rates
    seg_records: list[dict] = []
    for col in segment_cols:
        if col not in df.columns:
            continue
        grouped = pd.DataFrame({"error": errors, col: df[col]}).groupby(col)
        for name, group in grouped:
            seg_records.append({
                "segment_col": col,
                "segment_value": str(name) if not pd.isna(name) else "NaN",
                "n_samples": len(group),
                "n_errors": int(group["error"].sum()),
                "error_rate": round(group["error"].mean(), 5),
            })

    by_segment = pd.DataFrame(seg_records) if seg_records else pd.DataFrame()
    if not by_segment.empty:
        by_segment = by_segment.sort_values("error_rate", ascending=False).reset_index(drop=True)
        worst_segments = by_segment.head(top_n).copy()
    else:
        worst_segments = pd.DataFrame()

    return ErrorProfile(
        overall=overall,
        by_segment=by_segment,
        worst_segments=worst_segments,
    )

def _default_segment_cols(df: pd.DataFrame) -> list[str]:
    """Return a sensible default set of columns for segmentation."""
    candidates = []
    for col in ["ProductCD", "DeviceType", "hour"]:
        if col in df.columns:
            candidates.append(col)
    if "day_of_week" in df.columns:
        candidates.append("day_of_week")
    if "P_emaildomain" in df.columns:
        candidates.append("P_emaildomain")
    return candidates

def segment_errors(
    df: pd.DataFrame,
    y_true: pd.Series | np.ndarray,
    y_pred: np.ndarray,
    segment_cols: list[str],
) -> pd.DataFrame:
    """Compute error rate per segment for the specified columns.

    Parameters
    ----------
    df:
        Original feature DataFrame.
    y_true:
        Ground-truth binary labels.
    y_pred:
        Binary predictions.
    segment_cols:
        Columns to segment by.

    Returns
    -------
    pd.DataFrame
        Columns: ``segment_col``, ``segment_value``, ``n_samples``,
        ``n_errors``, ``error_rate``.

    Examples
    --------
    >>> import pandas as pd, numpy as np
    >>> df = pd.DataFrame({\"cat\": [\"a\", \"a\", \"b\"]})
    >>> y_true = pd.Series([0, 1, 0])
    >>> y_pred = np.array([0, 0, 0])
    >>> result = segment_errors(df, y_true, y_pred, [\"cat\"])
    >>> len(result)
    2
    """
    return compute_error_profile(
        df, y_true, y_pred, segment_cols=segment_cols
    ).by_segment

def feature_distribution_shift(
    df: pd.DataFrame,
    y_true: pd.Series | np.ndarray,
    y_pred: np.ndarray,
    feature_cols: list[str] | None = None,
) -> pd.DataFrame:
    """Compare numeric feature means between errors and correct predictions.

    A large absolute difference suggests the model struggles in certain
    regions of that feature's distribution.

    Parameters
    ----------
    df:
        Original feature DataFrame.
    y_true:
        Ground-truth binary labels.
    y_pred:
        Binary predictions.
    feature_cols:
        Numeric columns to compare. Defaults to all numeric columns.

    Returns
    -------
    pd.DataFrame
        Columns: ``feature``, ``mean_correct``, ``mean_error``, ``diff``,
        ``p_value`` (Kolmogorov-Smirnov test). Sorted by ``abs(diff)`` desc.

    Examples
    --------
    >>> import pandas as pd, numpy as np
    >>> rng = np.random.default_rng(42)
    >>> n = 100
    >>> df = pd.DataFrame({\"amt\": rng.uniform(0, 100, n),
    ...                    \"f2\": rng.standard_normal(n)})
    >>> y_true = pd.Series(rng.integers(0, 2, n))
    >>> y_pred = rng.integers(0, 2, n)
    >>> shift = feature_distribution_shift(df, y_true, y_pred)
    >>> \"amt\" in shift[\"feature\"].values
    True
    """
    from scipy.stats import ks_2samp

    y_true = np.asarray(y_true)
    y_pred = np.asarray(y_pred)
    errors = (y_true != y_pred).astype(int)

    feature_cols = feature_cols or list(df.select_dtypes(include=[np.number]).columns)
    # Remove excluded columns
    feature_cols = [c for c in feature_cols if c not in config.EXCLUDE_COLUMNS]

    records: list[dict] = []
    for col in feature_cols:
        if col not in df.columns:
            continue
        col_data = df[col].dropna()
        error_mask = errors[col_data.index] == 1
        correct_mask = ~error_mask

        error_vals = col_data[error_mask]
        correct_vals = col_data[correct_mask]

        if len(error_vals) > 0 and len(correct_vals) > 0:
            mean_error = float(error_vals.mean())
            mean_correct = float(correct_vals.mean())
            _, p_value = ks_2samp(error_vals, correct_vals)
            records.append({
                "feature": col,
                "mean_correct": round(mean_correct, 4),
                "mean_error": round(mean_error, 4),
                "diff": round(mean_error - mean_correct, 4),
                "p_value": round(p_value, 5),
            })

    result = pd.DataFrame(records) if records else pd.DataFrame()
    if not result.empty:
        result = result.assign(abs_diff=result["diff"].abs()).sort_values(
            "abs_diff", ascending=False
        ).drop(columns="abs_diff").reset_index(drop=True)
    return result

def top_false_positives(
    df: pd.DataFrame,
    y_true: pd.Series | np.ndarray,
    y_pred_proba: np.ndarray,
    n: int = 20,
) -> pd.DataFrame:
    """Return the *n* most confident false-positive predictions.

    Parameters
    ----------
    df:
        Original feature DataFrame (copied to avoid mutation).
    y_true:
        Ground-truth binary labels.
    y_pred_proba:
        Predicted probabilities for the positive class.
    n:
        Number of false positives to return.

    Returns
    -------
    pd.DataFrame
        Subset of ``df`` containing the top-*n* false positives, sorted by
        predicted probability descending, with a ``predicted_probability``
        column appended.

    Examples
    --------
    >>> import pandas as pd, numpy as np
    >>> df = pd.DataFrame({\"amt\": [10, 20, 30]})
    >>> y_true = pd.Series([0, 0, 1])
    >>> y_pred = np.array([0.9, 0.1, 0.8])
    >>> fps = top_false_positives(df, y_true, y_pred, n=2)
    >>> len(fps)
    1
    """
    y_true = np.asarray(y_true)
    fp_mask = (y_pred_proba >= 0.5) & (y_true == 0)
    fp_indices = np.where(fp_mask)[0]

    if len(fp_indices) == 0:
        return pd.DataFrame()

    # Sort by predicted probability descending
    fp_probas = y_pred_proba[fp_indices]
    sorted_order = np.argsort(fp_probas)[::-1]
    top_indices = fp_indices[sorted_order[:n]]

    result = df.iloc[top_indices].copy()
    result["predicted_probability"] = y_pred_proba[top_indices]
    return result.reset_index(drop=True)

def top_false_negatives(
    df: pd.DataFrame,
    y_true: pd.Series | np.ndarray,
    y_pred_proba: np.ndarray,
    n: int = 20,
) -> pd.DataFrame:
    """Return the *n* most confident false-negative predictions.

    Parameters
    ----------
    df:
        Original feature DataFrame (copied to avoid mutation).
    y_true:
        Ground-truth binary labels.
    y_pred_proba:
        Predicted probabilities for the positive class.
    n:
        Number of false negatives to return.

    Returns
    -------
    pd.DataFrame
        Subset of ``df`` containing the top-*n* false negatives, sorted by
        predicted probability ascending (most confidently missed first),
        with a ``predicted_probability`` column appended.
    """
    y_true = np.asarray(y_true)
    fn_mask = (y_pred_proba < 0.5) & (y_true == 1)
    fn_indices = np.where(fn_mask)[0]

    if len(fn_indices) == 0:
        return pd.DataFrame()

    # Sort by predicted probability ascending (most confidently wrong first)
    fn_probas = y_pred_proba[fn_indices]
    sorted_order = np.argsort(fn_probas)
    top_indices = fn_indices[sorted_order[:n]]

    result = df.iloc[top_indices].copy()
    result["predicted_probability"] = y_pred_proba[top_indices]
    return result.reset_index(drop=True)

def confusion_by_amount_bins(
    df: pd.DataFrame,
    y_true: pd.Series | np.ndarray,
    y_pred: np.ndarray,
    amt_col: str = "TransactionAmt",
    n_bins: int = 10,
) -> pd.DataFrame:
    """Compute confusion-matrix metrics bucketed by transaction amount.

    Parameters
    ----------
    df:
        Feature DataFrame with an amount column.
    y_true:
        Ground-truth binary labels.
    y_pred:
        Binary predictions.
    amt_col:
        Name of the amount column.
    n_bins:
        Number of equal-width bins.

    Returns
    -------
    pd.DataFrame
        One row per amount bin with columns: ``amount_bin``, ``n_samples``,
        ``n_fraud``, ``error_rate``, ``fp_rate``, ``fn_rate``.

    Examples
    --------
    >>> import pandas as pd, numpy as np
    >>> df = pd.DataFrame({\"TransactionAmt\": [10, 100, 50, 200]})
    >>> y_true = pd.Series([0, 1, 0, 1])
    >>> y_pred = np.array([0, 0, 0, 1])
    >>> result = confusion_by_amount_bins(df, y_true, y_pred, n_bins=2)
    >>> len(result)
    2
    """
    if amt_col not in df.columns:
        msg = f"Amount column '{amt_col}' not found in DataFrame"
        raise ValueError(msg)

    y_true = np.asarray(y_true)
    y_pred = np.asarray(y_pred)

    df_binned = df[[amt_col]].copy()
    df_binned["amount_bin"] = pd.cut(df_binned[amt_col], bins=n_bins, duplicates="drop")
    df_binned["is_error"] = (y_true != y_pred).astype(int)
    df_binned["is_fp"] = ((y_pred == 1) & (y_true == 0)).astype(int)
    df_binned["is_fn"] = ((y_pred == 0) & (y_true == 1)).astype(int)
    df_binned["is_fraud"] = y_true

    grouped = df_binned.groupby("amount_bin", observed=True)
    result = grouped.agg(
        n_samples=("is_error", "count"),
        n_fraud=("is_fraud", "sum"),
        error_rate=("is_error", "mean"),
        fp_rate=("is_fp", "mean"),
        fn_rate=("is_fn", "mean"),
    ).reset_index()

    for col in ["error_rate", "fp_rate", "fn_rate"]:
        if col in result.columns:
            result[col] = result[col].round(5)
    return result
