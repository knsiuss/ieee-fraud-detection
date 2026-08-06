"""Tests for fraud_detect.monitoring — PSI drift and data-quality checks."""

from __future__ import annotations

import numpy as np
import pandas as pd

from fraud_detect.monitoring import data_quality_check, feature_drift, psi


class TestPsi:
    def test_identical_distribution_is_zero(self):
        rng = np.random.default_rng(1)
        a = rng.standard_normal(500)
        assert abs(psi(a, a)) < 1e-9

    def test_shifted_distribution_drifts(self):
        rng = np.random.default_rng(2)
        ref = rng.standard_normal(500)
        shifted = rng.standard_normal(500) + 3.0
        assert psi(ref, shifted) > 0.5

    def test_tiny_sample_returns_nan(self):
        assert np.isnan(psi(np.array([1.0, 2.0, 3.0]), np.array([1.0])))


class TestFeatureDrift:
    def test_returns_sorted_table_with_status(self):
        rng = np.random.default_rng(3)
        ref = pd.DataFrame({"a": rng.standard_normal(400), "b": rng.standard_normal(400)})
        cur = pd.DataFrame({"a": rng.standard_normal(400) + 2.0, "b": rng.standard_normal(400)})
        table = feature_drift(["a", "b"], ref, cur)
        assert list(table.columns) == ["feature", "psi", "status"]
        assert table.iloc[0]["feature"] == "a"  # drifted feature sorts first
        assert (table["status"] == "drifted").any()


class TestDataQualityCheck:
    def test_reports_missing_columns(self):
        df = pd.DataFrame({"x": [1.0, np.nan], "y": [2.0, 3.0]})
        out = data_quality_check(df, ["x", "y", "z"])
        assert out["n_rows"] == 2
        assert out["n_missing_columns"] == 1
        assert out["missing_columns"] == ["z"]
        assert out["unknown_columns"] == []

    def test_unknown_columns_flagged(self):
        df = pd.DataFrame({"surprise": [1.0]})
        out = data_quality_check(df, ["x"])
        assert out["unknown_columns"] == ["surprise"]
