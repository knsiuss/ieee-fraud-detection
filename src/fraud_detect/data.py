"""Data loading, memory optimisation and missing-value reporting.

The :func:`reduce_mem_usage` helper is the single source of truth for dtype
downcasting — previously duplicated in ``data_prep.py`` and several
notebooks. :func:`compute_missing_report` and :func:`get_imputation_strategy`
replace ad-hoc logic that lived inline in notebook 04.
"""

from __future__ import annotations

import logging
from typing import Literal

import numpy as np
import pandas as pd

from . import config

logger = logging.getLogger(__name__)

ImputationStrategy = Literal[
    "None needed",
    "Drop column",
    "Indicator only",
    "Median",
    "Median + Indicator",
    "Mode + Indicator",
    "Constant (-999)",
]

def _downcast_column(df: pd.DataFrame, col: str) -> None:
    """Downcast a single column in-place (helper for reduce_mem_usage)."""
    col_type = df[col].dtype

    if not pd.api.types.is_numeric_dtype(col_type):
        if df[col].dtype == object:
            df[col] = df[col].astype("category")
        return

    c_min, c_max = df[col].min(), df[col].max()
    if pd.isna(c_min):  # all-NA column — skip downcasting
        return

    if pd.api.types.is_integer_dtype(col_type):
        if c_min > np.iinfo(np.int8).min and c_max < np.iinfo(np.int8).max:
            df[col] = df[col].astype(np.int8)
        elif c_min > np.iinfo(np.int16).min and c_max < np.iinfo(np.int16).max:
            df[col] = df[col].astype(np.int16)
        elif c_min > np.iinfo(np.int32).min and c_max < np.iinfo(np.int32).max:
            df[col] = df[col].astype(np.int32)
        else:
            df[col] = df[col].astype(np.int64)
    elif pd.api.types.is_float_dtype(col_type):
        if c_min > np.finfo(np.float32).min and c_max < np.finfo(np.float32).max:
            df[col] = df[col].astype(np.float32)
        else:
            df[col] = df[col].astype(np.float64)

def reduce_mem_usage(df: pd.DataFrame, verbose: bool = True) -> pd.DataFrame:
    """Downcast numeric columns to the smallest dtype that holds the data.

    Integer columns are tried against int8 → int16 → int32 → int64, and
    floating columns against float32 → float64 (float16 is skipped to avoid
    NaN-handling surprises in downstream libraries). Object columns are
    converted to ``category`` when memory is saved.

    Parameters
    ----------
    df:
        DataFrame to optimise. A copy is returned; the input is not mutated.
    verbose:
        When true, log before/after memory usage and the reduction ratio.

    Returns
    -------
    pandas.DataFrame
        A new DataFrame with downcasted dtypes.

    Examples
    --------
    >>> import pandas as pd, numpy as np
    >>> df = pd.DataFrame({"a": np.array([1, 2, 3], dtype=np.int64),
    ...                    "b": np.array([0.5, 1.5, 2.5], dtype=np.float64)})
    >>> out = reduce_mem_usage(df, verbose=False)
    >>> out["a"].dtype
    numpy.int8
    >>> out["b"].dtype
    numpy.float32
    """
    df = df.copy()
    start_mem = df.memory_usage(deep=True).sum() / 1024**2

    for col in df.columns:
        _downcast_column(df, col)

    end_mem = df.memory_usage(deep=True).sum() / 1024**2
    if verbose:
        reduction = 100 * (start_mem - end_mem) / start_mem if start_mem else 0.0
        logger.info(
            "Memory: %.1fMB -> %.1fMB (%.1f%% reduction)",
            start_mem,
            end_mem,
            reduction,
        )
    return df

def categorize_missing(pct: float) -> str:
    """Bucket a missing-percentage into a human-readable label."""
    if pct == 0:
        return "No Missing"
    if pct < 10:
        return "<10% Missing"
    if pct < 50:
        return "10-50% Missing"
    if pct < 75:
        return "50-75% Missing"
    return ">75% Missing"

def get_imputation_strategy(
    col: str,  # noqa: ARG001 — kept for public API stability
    missing_pct: float,
    dtype: np.dtype | str,
) -> ImputationStrategy:
    """Return the recommended imputation strategy for a column.

    Thresholds come from :mod:`fraud_detect.config` so they can be tuned in
    one place.

    * ``>95%`` missing → drop the column (signal too sparse).
    * ``>75%`` missing → keep only a missing-indicator.
    * ``>10%`` missing → impute (median for numeric, mode for categorical)
      *and* add a missing-indicator.
    * ``<=10%`` missing → impute without an indicator.
    * ``0%`` missing → no action.
    """
    if missing_pct == 0:
        return "None needed"
    if missing_pct > config.DROP_THRESHOLD * 100:
        return "Drop column"
    if missing_pct > config.INDICATOR_ONLY_THRESHOLD * 100:
        return "Indicator only"

    is_numeric = pd.api.types.is_numeric_dtype(dtype)
    if missing_pct > config.MODERATE_THRESHOLD * 100:
        return "Median + Indicator" if is_numeric else "Mode + Indicator"
    return "Median" if is_numeric else "Mode + Indicator"

def compute_missing_report(df: pd.DataFrame) -> pd.DataFrame:
    """Build a per-column missingness report with imputation strategies.

    Parameters
    ----------
    df:
        Input DataFrame (typically the merged training table).

    Returns
    -------
    pandas.DataFrame
        Columns: ``column``, ``missing_pct``, ``dtype``, ``strategy``.

    Examples
    --------
    >>> import pandas as pd, numpy as np
    >>> df = pd.DataFrame({"x": [1, 2, 3], "y": [np.nan, np.nan, 3.0]})
    >>> report = compute_missing_report(df)
    >>> report["column"].tolist()
    ['x', 'y']
    >>> report.set_index("column")["missing_pct"].round(1).to_dict()
    {'x': 0.0, 'y': 66.7}
    """
    total = len(df)
    records = []
    for col in df.columns:
        missing_count = int(df[col].isna().sum())
        missing_pct = (missing_count / total * 100) if total else 0.0
        records.append(
            {
                "column": col,
                "missing_pct": round(missing_pct, 4),
                "dtype": str(df[col].dtype),
                "strategy": get_imputation_strategy(col, missing_pct, df[col].dtype),
            }
        )
    return pd.DataFrame(records)

def load_merged_train() -> pd.DataFrame:
    """Load the merged transaction+identity training parquet (notebook 01)."""
    from .io import read_parquet

    return read_parquet(config.MERGED_TRAIN_PATH)
