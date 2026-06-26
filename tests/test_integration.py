"""Integration tests for combined fraud_detect workflows.

These tests verify that functions compose correctly — catching regressions
like the NotFittedError that previously plagued notebook 09.
"""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

import matplotlib
import numpy as np
import pandas as pd
import pytest

from fraud_detect import config, data, features, io, models
from fraud_detect._exceptions import InvalidDataError

# Prevent matplotlib from opening a display during testing.
matplotlib.use("Agg")


# --------------------------------------------------------------------------- #
# End-to-end: reduce_mem_usage on all dtypes
# --------------------------------------------------------------------------- #
def test_reduce_mem_usage_handles_all_dtypes():
    """Verify reduce_mem_usage processes every common dtype without error."""
    df = pd.DataFrame(
        {
            "int8": pd.array([1, 2], dtype="Int8"),
            "int16": pd.array([1, 2], dtype="Int16"),
            "int32": np.array([1, 2], dtype=np.int32),
            "int64": np.array([1, 2], dtype=np.int64),
            "float32": np.array([1.0, 2.0], dtype=np.float32),
            "float64": np.array([1.0, 2.0], dtype=np.float64),
            "object": ["a", "b"],
            "category": pd.Categorical(["x", "y"]),
        }
    )
    out = data.reduce_mem_usage(df, verbose=False)
    assert out.shape == df.shape
    assert list(out.columns) == list(df.columns)


# --------------------------------------------------------------------------- #
# End-to-end: feature engineering pipeline
# --------------------------------------------------------------------------- #
def test_build_all_features_full_pipeline(synthetic_df):
    """Verify the full feature pipeline produces the expected output columns."""
    out = features.build_all_features(synthetic_df)
    # Input columns still present.
    for col in synthetic_df.columns:
        assert col in out.columns
    # Engineered columns present.
    for col in [
        "transaction_dt",
        "hour",
        "day_of_week",
        "day_of_month",
        "is_night",
        "is_weekend",
        "amt_log",
        "amt_decimal",
        "amt_is_round",
        "email_match",
        "p_email_is_free",
        "r_email_is_free",
        "card1_tx_count",
        "card1_amt_mean",
        "card1_amt_std",
        "amt_vs_card_mean",
        "has_identity",
    ]:
        assert col in out.columns, f"Missing engineered column: {col}"


# --------------------------------------------------------------------------- #
# End-to-end: model workflow with synthetic data
# --------------------------------------------------------------------------- #
def test_model_workflow_no_crash(synthetic_df):
    """Verify split -> fit -> evaluate works end-to-end on synthetic data."""
    split = models.make_train_val_split(synthetic_df)
    assert len(split.X_train) > 0
    assert len(split.X_val) > 0

    pipe = models.build_logistic_pipeline()
    result = models.evaluate_classifier(pipe, split)

    assert result["train_auc"] >= 0.0
    assert result["val_auc"] >= 0.0
    assert result["overfitting_gap"] >= 0.0


# --------------------------------------------------------------------------- #
# build_all_features edge cases
# --------------------------------------------------------------------------- #
def test_build_all_features_missing_columns():
    """Should gracefully handle a DataFrame missing optional columns."""
    df = pd.DataFrame({"TransactionID": [1], "TransactionDT": [0], "TransactionAmt": [10.0]})
    out = features.build_all_features(df)
    assert "amt_log" in out.columns
    assert "transaction_dt" in out.columns


def test_build_all_features_idempotent(synthetic_df):
    """Re-running build_all_features should not duplicate or drop columns."""
    once = features.build_all_features(synthetic_df)
    twice = features.build_all_features(once)
    assert sorted(twice.columns) == sorted(once.columns)
    assert twice.shape == once.shape


# --------------------------------------------------------------------------- #
# load_train_features raises InvalidDataError for empty data
# --------------------------------------------------------------------------- #
def test_load_train_features_raises_on_empty(monkeypatch):
    """Verify load_train_features raises InvalidDataError for empty parquet."""
    with TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        empty_path = tmp_path / "train_features.parquet"
        pd.DataFrame().to_parquet(empty_path)
        monkeypatch.setattr(config, "PROCESSED_TRAIN_PATH", empty_path)
        monkeypatch.setattr(config, "MERGED_TRAIN_PATH", Path("/nonexistent/file.parquet"))
        with pytest.raises(InvalidDataError, match="empty"):
            io.load_train_features()


def test_load_train_features_raises_on_missing_target(monkeypatch):
    """Verify load_train_features raises InvalidDataError when target missing."""
    with TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        df_path = tmp_path / "train_features.parquet"
        pd.DataFrame({"TransactionID": [1], "TransactionAmt": [10.0]}).to_parquet(df_path)
        monkeypatch.setattr(config, "PROCESSED_TRAIN_PATH", df_path)
        monkeypatch.setattr(config, "MERGED_TRAIN_PATH", Path("/nonexistent/file.parquet"))
        with pytest.raises(InvalidDataError, match="target column"):
            io.load_train_features()


# --------------------------------------------------------------------------- #
# compute_lightgbm_importance (requires lightgbm)
# --------------------------------------------------------------------------- #
def test_compute_lightgbm_importance(synthetic_df):
    """Verify compute_lightgbm_importance returns correct shape/sort."""
    pytest.importorskip("lightgbm")
    imp = models.compute_lightgbm_importance(synthetic_df, num_boost_round=10)
    assert list(imp.columns) == ["feature", "importance"]
    assert (imp["importance"] >= 0).all()
    # Verify descending sort
    assert imp["importance"].is_monotonic_decreasing
