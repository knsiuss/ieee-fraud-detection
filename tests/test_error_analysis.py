"""Tests for the error analysis module (fraud_detect.error_analysis).

Uses synthetic data so the suite runs quickly without the real dataset.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from fraud_detect import error_analysis as ea


@pytest.fixture
def sample_data() -> tuple[pd.DataFrame, pd.Series, np.ndarray]:
    """Small synthetic DataFrame with predictions."""
    rng = np.random.default_rng(42)
    n = 200
    df = pd.DataFrame({
        "ProductCD": rng.choice(["W", "H", "C"], n),
        "DeviceType": rng.choice(["desktop", "mobile"], n),
        "TransactionAmt": rng.uniform(1, 500, n),
        "hour": rng.integers(0, 23, n),
    })
    y_true = pd.Series(rng.integers(0, 2, n))
    y_pred = rng.integers(0, 2, n)
    return df, y_true, y_pred


# --------------------------------------------------------------------------- #
# compute_error_profile
# --------------------------------------------------------------------------- #


def test_compute_error_profile_returns_profile(sample_data):
    df, y_true, y_pred = sample_data
    profile = ea.compute_error_profile(df, y_true, y_pred)
    assert isinstance(profile, ea.ErrorProfile)
    assert "error_rate" in profile.overall
    assert "n_total" in profile.overall
    assert 0.0 <= profile.overall["error_rate"] <= 1.0
    assert not profile.by_segment.empty
    assert not profile.worst_segments.empty


def test_compute_error_profile_overall_metrics(sample_data):
    df, y_true, y_pred = sample_data
    profile = ea.compute_error_profile(df, y_true, y_pred)
    assert profile.overall["n_total"] == len(y_true)
    assert profile.overall["n_errors"] == int((y_true != y_pred).sum())


# --------------------------------------------------------------------------- #
# segment_errors
# --------------------------------------------------------------------------- #


def test_segment_errors_returns_dataframe(sample_data):
    df, y_true, y_pred = sample_data
    seg = ea.segment_errors(df, y_true, y_pred, ["ProductCD"])
    assert isinstance(seg, pd.DataFrame)
    assert list(seg.columns) == ["segment_col", "segment_value", "n_samples", "n_errors", "error_rate"]
    assert len(seg) >= 1


# --------------------------------------------------------------------------- #
# feature_distribution_shift
# --------------------------------------------------------------------------- #


def test_feature_distribution_shift_returns_dataframe(sample_data):
    df, y_true, y_pred = sample_data
    shift = ea.feature_distribution_shift(df, y_true, y_pred, feature_cols=["TransactionAmt"])
    assert isinstance(shift, pd.DataFrame)
    assert "feature" in shift.columns
    assert "diff" in shift.columns


def test_feature_distribution_shift_no_crash_on_empty(sample_data):
    df, y_true, y_pred = sample_data
    shift = ea.feature_distribution_shift(df, y_true, y_pred, feature_cols=["nonexistent"])
    assert isinstance(shift, pd.DataFrame)
    assert shift.empty


# --------------------------------------------------------------------------- #
# top_false_positives / top_false_negatives
# --------------------------------------------------------------------------- #


def test_top_false_positives_returns_correct(sample_data):
    df, y_true, _ = sample_data
    # Create predictable fake probabilities that produce some FPs
    rng = np.random.default_rng(42)
    y_pred_proba = rng.uniform(0, 1, len(y_true))
    fps = ea.top_false_positives(df, y_true, y_pred_proba, n=5)
    if not fps.empty:
        assert "predicted_probability" in fps.columns
        assert len(fps) <= 5


def test_top_false_negatives_returns_correct(sample_data):
    df, y_true, _ = sample_data
    rng = np.random.default_rng(42)
    y_pred_proba = rng.uniform(0, 1, len(y_true))
    fns = ea.top_false_negatives(df, y_true, y_pred_proba, n=5)
    if not fns.empty:
        assert "predicted_probability" in fns.columns


# --------------------------------------------------------------------------- #
# confusion_by_amount_bins
# --------------------------------------------------------------------------- #


def test_confusion_by_amount_bins_returns_dataframe(sample_data):
    df, y_true, y_pred = sample_data
    result = ea.confusion_by_amount_bins(df, y_true, y_pred, amt_col="TransactionAmt", n_bins=5)
    assert isinstance(result, pd.DataFrame)
    expected_cols = {"amount_bin", "n_samples", "n_fraud", "error_rate", "fp_rate", "fn_rate"}
    assert expected_cols.issubset(result.columns)
    assert len(result) >= 1


def test_confusion_by_amount_bins_missing_column(sample_data):
    df, y_true, y_pred = sample_data
    with pytest.raises(ValueError, match="Amount column"):
        ea.confusion_by_amount_bins(df, y_true, y_pred, amt_col="nonexistent")


# --------------------------------------------------------------------------- #
# ErrorProfile dataclass
# --------------------------------------------------------------------------- #


def test_error_profile_defaults():
    """Verify ErrorProfile accepts None for optional fields."""
    profile = ea.ErrorProfile(
        overall={"error_rate": 0.1, "n_total": 100, "n_errors": 10},
        by_segment=pd.DataFrame(),
        worst_segments=pd.DataFrame(),
    )
    assert profile.feature_distribution_shift is None
