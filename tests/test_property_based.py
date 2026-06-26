"""Property-based tests for fraud_detect pure functions.

Uses ``hypothesis`` to discover edge cases that hand-written tests might miss.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from hypothesis import given, settings
from hypothesis import strategies as st

from fraud_detect import config, data, features, models

#: Small integer values safe for int8 downcasting.
_INT8_SAFE = st.integers(min_value=-100, max_value=100)

#: Small positive float values safe for float32.
_FLOAT_SAFE = st.floats(min_value=1e-6, max_value=1e6, allow_nan=False, allow_infinity=False)


# --------------------------------------------------------------------------- #
# Property: reduce_mem_usage output dtypes are never wider than input
# --------------------------------------------------------------------------- #
@given(st.lists(_INT8_SAFE, min_size=1, max_size=5))
@settings(max_examples=50)
def test_reduce_mem_usage_no_upcast_int(values):
    df = pd.DataFrame({"a": np.array(values, dtype=np.int64)})
    out = data.reduce_mem_usage(df, verbose=False)
    input_bits = df["a"].dtype.itemsize * 8
    output_bits = out["a"].dtype.itemsize * 8
    assert output_bits <= input_bits, f"Upcast from {input_bits} to {output_bits}"


@given(st.lists(_FLOAT_SAFE, min_size=1, max_size=5))
@settings(max_examples=50)
def test_reduce_mem_usage_no_upcast_float(values):
    df = pd.DataFrame({"a": np.array(values, dtype=np.float64)})
    out = data.reduce_mem_usage(df, verbose=False)
    input_bits = df["a"].dtype.itemsize * 8
    output_bits = out["a"].dtype.itemsize * 8
    assert output_bits <= input_bits, f"Upcast from {input_bits} to {output_bits}"


# --------------------------------------------------------------------------- #
# Property: add_time_features is idempotent
# --------------------------------------------------------------------------- #
@given(st.lists(st.integers(min_value=0, max_value=86400 * 7), min_size=1))
@settings(max_examples=50)
def test_add_time_features_idempotent(dt_values):
    df = pd.DataFrame({config.TRANSACTION_DT_COLUMN: dt_values})
    out1 = features.add_time_features(df)
    out2 = features.add_time_features(out1)
    assert out2.shape == out1.shape
    pd.testing.assert_frame_equal(out1, out2)


# --------------------------------------------------------------------------- #
# Property: add_amount_features preserves input columns exactly
# --------------------------------------------------------------------------- #
@given(st.lists(_FLOAT_SAFE, min_size=1))
@settings(max_examples=50)
def test_add_amount_features_preserves_input(amounts):
    df = pd.DataFrame({"TransactionAmt": amounts})
    out = features.add_amount_features(df)
    pd.testing.assert_series_equal(df["TransactionAmt"], out["TransactionAmt"], check_dtype=False)


# --------------------------------------------------------------------------- #
# Property: select_feature_columns never returns EXCLUDE_COLUMNS
# --------------------------------------------------------------------------- #
@given(st.lists(_INT8_SAFE, min_size=1))
@settings(max_examples=50)
def test_select_feature_columns_no_excluded(values):
    df = pd.DataFrame(
        {
            "isFraud": values,
            "TransactionID": values,
            "TransactionDT": values,
            "feature_a": values,
        }
    )
    selected = models.select_feature_columns(df)
    assert "feature_a" in selected
    for excluded in config.EXCLUDE_COLUMNS:
        assert excluded not in selected
