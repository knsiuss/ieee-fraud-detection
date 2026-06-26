"""Feature engineering transforms.

Each function takes a DataFrame and returns a new DataFrame with the
engineered columns appended, leaving the input unchanged. The transforms
mirror what notebook 07 did inline, but vectorised and idempotent so they
can be safely re-run on already-enriched tables.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import config

def add_time_features(
    df: pd.DataFrame,
    dt_col: str = config.TRANSACTION_DT_COLUMN,
    start: str = config.TRANSACTION_DT_START,
) -> pd.DataFrame:
    """Derive calendar and cyclical time features from ``TransactionDT``.

    Adds:

    * ``transaction_dt`` — absolute ``Timestamp`` anchored at ``start``.
    * ``hour`` — hour-of-day (0-23) in a 24h clock from the reference start.
    * ``day_of_week`` — integer 0-6.
    * ``day_of_month`` — integer 1-31.
    * ``is_night`` — 1 if hour is in [22, 23, 0..5], else 0.
    * ``is_weekend`` — 1 if day_of_week in {5, 6}, else 0.

    The new columns overwrite existing ones with the same name, making the
    function safe to re-run.
    """
    out = df.copy()
    base = pd.Timestamp(start)
    out["transaction_dt"] = base + pd.to_timedelta(out[dt_col], unit="s")
    out["hour"] = (out[dt_col] // 3600) % 24
    out["day_of_week"] = (out[dt_col] // 86400) % 7
    out["day_of_month"] = out["transaction_dt"].dt.day
    out["is_night"] = ((out["hour"] >= 22) | (out["hour"] <= 5)).astype(np.int8)
    out["is_weekend"] = out["day_of_week"].isin([5, 6]).astype(np.int8)
    return out

def add_amount_features(
    df: pd.DataFrame,
    amt_col: str = "TransactionAmt",
) -> pd.DataFrame:
    """Add log-amount, decimal-part and round-amount indicator features.

    Parameters
    ----------
    df:
        Input DataFrame with ``TransactionAmt`` column.
    amt_col:
        Name of the transaction amount column.

    Returns
    -------
    pd.DataFrame
        New DataFrame with ``amt_log``, ``amt_decimal``, ``amt_is_round``
        columns appended.

    Examples
    --------
    >>> import pandas as pd
    >>> df = pd.DataFrame({"TransactionAmt": [10.0, 10.5, 100.0]})
    >>> out = add_amount_features(df)
    >>> out["amt_is_round"].tolist()
    [1, 0, 1]
    >>> out["amt_log"].iloc[0]  # log1p(10)
    2.397895272...
    """
    out = df.copy()
    eps = 1e-9
    out["amt_log"] = np.log1p(out[amt_col].clip(lower=eps))
    out["amt_decimal"] = (out[amt_col] - out[amt_col].astype(int)).round(3)
    out["amt_is_round"] = (out["amt_decimal"] == 0).astype(np.int8)
    return out

def add_email_features(
    df: pd.DataFrame,
    purchaser_col: str = "P_emaildomain",
    recipient_col: str = "R_emaildomain",
) -> pd.DataFrame:
    """Add email-domain matching and free-domain indicator features.

    Parameters
    ----------
    df:
        Input DataFrame with purchaser/recipient email domain columns.
    purchaser_col:
        Column name for purchaser email domain.
    recipient_col:
        Column name for recipient email domain.

    Returns
    -------
    pd.DataFrame
        New DataFrame with ``email_match``, ``p_email_is_free``,
        ``r_email_is_free`` columns appended.

    Examples
    --------
    >>> import pandas as pd
    >>> df = pd.DataFrame({"P_emaildomain": ["gmail.com", "gmail.com"],
    ...                    "R_emaildomain": ["gmail.com", "yahoo.com"]})
    >>> out = add_email_features(df)
    >>> out["email_match"].tolist()
    [1, 0]
    >>> out["p_email_is_free"].tolist()
    [1, 1]
    """
    out = df.copy()
    if purchaser_col not in out.columns or recipient_col not in out.columns:
        return out
    free = set(config.FREE_EMAIL_DOMAINS)

    both_present = out[purchaser_col].notna() & out[recipient_col].notna()
    out["email_match"] = ((out[purchaser_col] == out[recipient_col]) & both_present).astype(np.int8)
    out["p_email_is_free"] = (out[purchaser_col].fillna("").isin(free)).astype(np.int8)
    out["r_email_is_free"] = (out[recipient_col].fillna("").isin(free)).astype(np.int8)
    return out

def add_card_aggregations(df: pd.DataFrame) -> pd.DataFrame:
    """Add per-card aggregation features.

    For each ``card1`` group we attach the group size, mean amount, standard
    deviation of the amount, and each row's deviation from the group mean.
    These are leakage-safe when computed on the training set only and joined
    to validation/test via a learned mapping.
    """
    out = df.copy()
    if "card1" not in out.columns or "TransactionAmt" not in out.columns:
        return out

    agg = (
        out.groupby("card1")["TransactionAmt"]
        .agg(card1_tx_count="count", card1_amt_mean="mean", card1_amt_std="std")
        .reset_index()
    )
    # Replace inf std (single-row groups) with NaN
    agg["card1_amt_std"] = agg["card1_amt_std"].replace([np.inf, -np.inf], np.nan)

    for col in ("card1_tx_count", "card1_amt_mean", "card1_amt_std", "amt_vs_card_mean"):
        if col in out.columns:
            out = out.drop(columns=col)
    out = out.merge(agg, on="card1", how="left")
    if "card1_amt_mean" in out.columns and "TransactionAmt" in out.columns:
        out["amt_vs_card_mean"] = (out["TransactionAmt"] - out["card1_amt_mean"]).round(3)
    return out

def add_identity_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add a binary flag indicating whether identity data is available.

    The identity table (``id_01``–``id_38``, ``DeviceType``, ``DeviceInfo``)
    covers only ~25% of transactions. The ``has_identity`` flag captures
    this coverage gap, which can be predictive.
    """
    out = df.copy()
    identity_cols = [c for c in out.columns if c.startswith("id_")]
    if identity_cols:
        out["has_identity"] = out[identity_cols].notna().any(axis=1).astype(np.int8)
    else:
        out["has_identity"] = 0
    return out

def build_all_features(df: pd.DataFrame) -> pd.DataFrame:
    """Apply the full feature-engineering pipeline used in notebook 07."""
    df = add_time_features(df)
    df = add_amount_features(df)
    df = add_email_features(df)
    df = add_card_aggregations(df)
    df = add_identity_features(df)
    return df
