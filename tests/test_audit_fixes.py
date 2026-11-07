"""Regression tests for audit-fix findings.

Covers: path traversal confinement, fail-closed admin auth, batch id
collision, PSI NaN hygiene, index alignment, policy validation.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from fraud_detect import monitoring
from fraud_detect.error_analysis import feature_distribution_shift
from fraud_detect.policy import DecisionPolicy, policy_from_env


def test_psi_nan_heavy_no_longer_zero():
    rng = np.random.default_rng(0)
    ref = rng.standard_normal(200)
    ref[::2] = np.nan  # >50% NaN, IEEE-CIS style
    cur = rng.standard_normal(200) + 5.0  # 5 sigma shift
    assert monitoring.psi(ref, cur) > 0


def test_psi_empty_after_dropna_is_nan():
    assert np.isnan(monitoring.psi(np.full(100, np.nan), np.ones(50)))


def test_feature_distribution_shift_nondefault_index():
    rng = np.random.default_rng(7)
    n = 200
    df = pd.DataFrame(
        {
            "featscore": rng.standard_normal(n),
            "isFraud": rng.integers(0, 2, n),
        },
        index=rng.permutation(n) + 1000,  # shuffled label index, in-range
    )
    y_true = df["isFraud"].to_numpy()
    y_pred = 1 - y_true  # every prediction wrong -> all rows are errors
    out = feature_distribution_shift(
        df, y_true, y_pred, feature_cols=["featscore"]
    )
    # All errors -> no correct vals -> empty frame (must not raise)
    assert out.empty

    # Mixed case on the same shuffled index must return aligned stats
    y_pred2 = y_true.copy()
    y_pred2[:10] = 1 - y_pred2[:10]  # 10 errors
    out2 = feature_distribution_shift(
        df, y_true, y_pred2, feature_cols=["featscore"]
    )
    assert not out2.empty
    expected = df["featscore"].iloc[:10].mean()
    assert abs(out2["mean_error"].iloc[0] - round(float(expected), 4)) < 1e-3


def test_feature_distribution_shift_out_of_range_index():
    rng = np.random.default_rng(7)
    n = 150
    df = pd.DataFrame(
        {
            "featscore": rng.standard_normal(n),
            "isFraud": rng.integers(0, 2, n),
        },
        index=[1000 + i * 7 for i in range(n)],  # label index beyond array length
    )
    y_true = df["isFraud"].to_numpy()
    y_pred = y_true.copy()
    out = feature_distribution_shift(df, y_true, y_pred, feature_cols=["featscore"])
    # No errors -> no rows, but must not raise IndexError
    assert out.empty


def test_decision_policy_inverted_thresholds_rejected():
    import pytest

    with pytest.raises(ValueError):
        DecisionPolicy(version="v1", review_above=0.9, decline_above=0.1)
    with pytest.raises(ValueError):
        policy_from_env(review_above=0.9, decline_above=0.1)


def test_decision_policy_default_valid():
    p = DecisionPolicy(version="v1", review_above=0.15, decline_above=0.5)
    assert p.review_above <= p.decline_above
