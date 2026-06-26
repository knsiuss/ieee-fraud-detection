"""Smoke tests for pure helpers in fraud_detect.

These tests deliberately avoid touching the real IEEE-CIS dataset so the
suite runs in any environment (including CI without data).
"""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytest
from sklearn.pipeline import Pipeline

from fraud_detect import config, data, features, io, models, viz
from fraud_detect._exceptions import MissingArtefactError
from fraud_detect.viz import save_figure


# --------------------------------------------------------------------------- #
# data.reduce_mem_usage
# --------------------------------------------------------------------------- #
def test_reduce_mem_usage_downcasts_integers():
    df = pd.DataFrame({"a": np.array([1, 2, 3], dtype=np.int64)})
    out = data.reduce_mem_usage(df, verbose=False)
    assert out["a"].dtype == np.int8


def test_reduce_mem_usage_downcasts_floats():
    df = pd.DataFrame({"a": np.array([0.0, 1.0], dtype=np.float64)})
    out = data.reduce_mem_usage(df, verbose=False)
    assert out["a"].dtype == np.float32


def test_reduce_mem_usage_does_not_mutate_input():
    df = pd.DataFrame({"a": np.array([1, 2, 3], dtype=np.int64)})
    data.reduce_mem_usage(df, verbose=False)
    assert df["a"].dtype == np.int64  # original untouched


# --------------------------------------------------------------------------- #
# data.get_imputation_strategy / categorize_missing
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "pct, dtype, expected",
    [
        (0.0, np.int32, "None needed"),
        (5.0, np.float32, "Median"),
        (20.0, np.float32, "Median + Indicator"),
        (80.0, np.float32, "Indicator only"),
        (97.0, np.float32, "Drop column"),
        (20.0, object, "Mode + Indicator"),
    ],
)
def test_get_imputation_strategy(pct, dtype, expected):
    assert data.get_imputation_strategy("col", pct, dtype) == expected


def test_categorize_missing_buckets():
    assert data.categorize_missing(0) == "No Missing"
    assert data.categorize_missing(5) == "<10% Missing"
    assert data.categorize_missing(40) == "10-50% Missing"
    assert data.categorize_missing(60) == "50-75% Missing"
    assert data.categorize_missing(90) == ">75% Missing"


def test_compute_missing_report_shape_and_strategy():
    df = pd.DataFrame(
        {
            "full": [1, 2, 3],
            "sparse": [1, np.nan, np.nan],
        }
    )
    report = data.compute_missing_report(df)
    assert list(report.columns) == ["column", "missing_pct", "dtype", "strategy"]
    full_row = report[report["column"] == "full"].iloc[0]
    sparse_row = report[report["column"] == "sparse"].iloc[0]
    assert full_row["missing_pct"] == 0.0
    assert full_row["strategy"] == "None needed"
    assert sparse_row["missing_pct"] == pytest.approx(66.67, rel=1e-2)
    assert sparse_row["strategy"] in {"Indicator only", "Median + Indicator"}


def test_load_merged_train(monkeypatch):
    """Verify load_merged_train reads a parquet from MERGED_TRAIN_PATH."""
    df = pd.DataFrame({"a": [1, 2, 3]})
    with TemporaryDirectory() as tmp:
        path = Path(tmp) / "train_merged.parquet"
        df.to_parquet(path)
        monkeypatch.setattr(config, "MERGED_TRAIN_PATH", path)
        loaded = data.load_merged_train()
        pd.testing.assert_frame_equal(loaded, df)


# --------------------------------------------------------------------------- #
# features.add_time_features / add_amount_features / add_email_features
# --------------------------------------------------------------------------- #
def test_add_time_features_vectorised_and_idempotent():
    df = pd.DataFrame({config.TRANSACTION_DT_COLUMN: [0, 3600, 86400]})
    out = features.add_time_features(df)
    # hour 0, 1, 0 (86400s = exactly one day, wraps back to 00:00).
    assert out["hour"].tolist() == [0, 1, 0]
    assert out["day_of_week"].tolist() == [0, 0, 1]
    # All three fall in the night window (hour 0 and 1 are both <= 5).
    assert out["is_night"].tolist() == [1, 1, 1]
    # Re-running does not duplicate or corrupt columns.
    out2 = features.add_time_features(out)
    assert out2.shape == out.shape


def test_add_amount_features():
    df = pd.DataFrame({"TransactionAmt": [10.0, 10.5, 100.0]})
    out = features.add_amount_features(df)
    assert out["amt_is_round"].tolist() == [1, 0, 1]
    assert out["amt_log"].iloc[0] == pytest.approx(np.log1p(10.0))


def test_add_email_features_free_domain_and_match():
    df = pd.DataFrame(
        {
            "P_emaildomain": ["gmail.com", "gmail.com", "protonmail.com"],
            "R_emaildomain": ["gmail.com", "yahoo.com", "protonmail.com"],
        }
    )
    out = features.add_email_features(df)
    assert out["email_match"].tolist() == [1, 0, 1]
    assert out["p_email_is_free"].tolist() == [1, 1, 0]
    assert out["r_email_is_free"].tolist() == [1, 1, 0]


# --------------------------------------------------------------------------- #
# models.select_feature_columns / make_train_val_split
# --------------------------------------------------------------------------- #
def test_select_feature_columns_excludes_id_target_dt():
    df = pd.DataFrame(
        {
            config.TRANSACTION_ID_COLUMN: [1, 2],
            config.TARGET_COLUMN: [0, 1],
            config.TRANSACTION_DT_COLUMN: [10, 20],
            "feature_a": [0.1, 0.2],
        }
    )
    assert models.select_feature_columns(df) == ["feature_a"]


def test_make_train_val_split_shapes_and_stratification():
    rng = np.random.default_rng(0)
    n = 200
    df = pd.DataFrame(
        {
            config.TARGET_COLUMN: rng.integers(0, 2, n),
            "f1": rng.standard_normal(n),
            "f2": rng.standard_normal(n),
        }
    )
    split = models.make_train_val_split(df, test_size=0.25)
    assert len(split.X_train) == 150
    assert len(split.X_val) == 50
    # Stratification keeps the positive rate close between splits.
    train_rate = split.y_train.mean()
    val_rate = split.y_val.mean()
    assert abs(train_rate - val_rate) < 0.1


# --------------------------------------------------------------------------- #
# data.categorize_missing edge cases
# --------------------------------------------------------------------------- #
def test_categorize_missing_float_and_large():
    assert data.categorize_missing(0.0) == "No Missing"
    assert data.categorize_missing(100.0) == ">75% Missing"
    assert data.categorize_missing(9.999) == "<10% Missing"
    assert data.categorize_missing(74.999) == "50-75% Missing"


# --------------------------------------------------------------------------- #
# features.add_card_aggregations
# --------------------------------------------------------------------------- #
def test_add_card_aggregations_idempotent():
    df = pd.DataFrame({"card1": [1, 1, 2], "TransactionAmt": [10.0, 20.0, 30.0]})
    out1 = features.add_card_aggregations(df)
    out2 = features.add_card_aggregations(out1)
    assert out2.shape == out1.shape
    assert out2.columns.tolist() == out1.columns.tolist()


def test_add_card_aggregations_missing_card1():
    df = pd.DataFrame({"TransactionAmt": [10.0, 20.0]})
    out = features.add_card_aggregations(df)
    assert out.equals(df)  # no-op when card1 missing


# --------------------------------------------------------------------------- #
# features.build_all_features composition
# --------------------------------------------------------------------------- #
def test_build_all_features_adds_expected_columns(synthetic_df):
    out = features.build_all_features(synthetic_df)
    expected_new = {
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
    }
    assert expected_new.issubset(out.columns)


# --------------------------------------------------------------------------- #
# models.build_logistic_pipeline
# --------------------------------------------------------------------------- #
def test_build_logistic_pipeline_steps():
    pipe = models.build_logistic_pipeline()
    assert isinstance(pipe, Pipeline)
    assert len(pipe.steps) == 3
    assert pipe.steps[0][0] == "imputer"
    assert pipe.steps[1][0] == "scaler"
    assert pipe.steps[2][0] == "model"


# --------------------------------------------------------------------------- #
# models.evaluate_classifier return shape
# --------------------------------------------------------------------------- #
def test_evaluate_classifier_returns_expected_keys(synthetic_df):

    split = models.make_train_val_split(synthetic_df)
    pipe = models.build_logistic_pipeline()
    result = models.evaluate_classifier(pipe, split)
    assert sorted(result.keys()) == ["overfitting_gap", "train_auc", "val_auc"]
    for v in result.values():
        assert 0.0 <= v <= 1.0


# --------------------------------------------------------------------------- #
# io raises MissingArtefactError
# --------------------------------------------------------------------------- #
def test_read_parquet_raises_on_missing():
    with pytest.raises(MissingArtefactError):
        io.read_parquet(Path("/nonexistent/file.parquet"))


def test_read_csv_raises_on_missing():
    with pytest.raises(MissingArtefactError):
        io.read_csv(Path("/nonexistent/file.csv"))


def test_write_then_read_round_trip():
    df = pd.DataFrame({"a": [1, 2, 3]})
    with TemporaryDirectory() as tmp:
        path = Path(tmp) / "test.parquet"
        io.write_parquet(df, path)
        assert path.exists()
        loaded = io.read_parquet(path)
        pd.testing.assert_frame_equal(df, loaded)


def test_write_csv_creates_file():
    """Verify write_csv writes a file with the expected content."""
    df = pd.DataFrame({"a": [1, 2, 3], "b": ["x", "y", "z"]})
    with TemporaryDirectory() as tmp:
        path = Path(tmp) / "subdir" / "test.csv"
        io.write_csv(df, path, index=False)
        assert path.exists()
        loaded = pd.read_csv(path)
        pd.testing.assert_frame_equal(loaded, df)


# --------------------------------------------------------------------------- #
# viz.save_figure helper
# --------------------------------------------------------------------------- #
def test_save_figure_creates_file():
    fig, ax = plt.subplots()
    ax.plot([1, 2], [3, 4])
    with TemporaryDirectory() as tmp:
        path = Path(tmp) / "subdir" / "test.png"
        save_figure(fig, path)
        assert path.exists()
    plt.close(fig)


# --------------------------------------------------------------------------- #
# viz plot functions — smoke tests (return type, no crash)
# --------------------------------------------------------------------------- #
def test_plot_target_distribution_returns_figure(synthetic_df):
    fig, ax = viz.plot_target_distribution(synthetic_df["isFraud"])
    assert isinstance(fig, plt.Figure)
    assert isinstance(ax, plt.Axes)
    plt.close(fig)


def test_plot_fraud_rate_by_category_returns_figure(synthetic_df):
    fig, ax = viz.plot_fraud_rate_by_category(synthetic_df, "ProductCD")
    assert isinstance(fig, plt.Figure)
    assert isinstance(ax, plt.Axes)
    plt.close(fig)


def test_plot_target_correlation_returns_figure(synthetic_df):
    fig, ax = viz.plot_target_correlation(synthetic_df)
    assert isinstance(fig, plt.Figure)
    assert isinstance(ax, plt.Axes)
    plt.close(fig)
