"""Lightweight MLOps monitoring helpers.

Production-inspired guards that a reviewer can run against the served model
and stream of scored transactions: per-feature distribution drift (Population
Stability Index), data-quality checks against the expected feature schema,
and prediction-score drift. None of this substitutes for label-based
performance monitoring, which needs trusted labels (see the model card).
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import numpy as np
import pandas as pd

#: Above this PSI a feature is generally considered to have drifted.
PSI_DRIFT_WARN: float = 0.20


def psi(reference: np.ndarray, current: np.ndarray, n_bins: int = 10) -> float:
    """Population Stability Index between two 1-D samples.

    Reference bin edges are derived from ``reference``; both are normalised
    to frequency distributions with a small smoothing factor so empty bins do
    not produce infinities.
    """
    ref = np.asarray(reference, dtype=float)
    cur = np.asarray(current, dtype=float)
    if ref.size < n_bins or cur.size == 0:
        return float("nan")

    edges = np.percentile(ref, np.linspace(0, 100, n_bins + 1))
    edges = np.unique(edges)
    if edges.size < 2:
        return 0.0

    eps = 1e-6
    ref_frac = np.histogram(ref, bins=edges)[0] / ref.size
    cur_frac = np.histogram(cur, bins=edges)[0] / cur.size
    ref_frac = (ref_frac + eps) / (1.0 + eps * ref_frac.size)
    cur_frac = (cur_frac + eps) / (1.0 + eps * cur_frac.size)

    with np.errstate(divide="ignore", invalid="ignore"):
        ratio = cur_frac / ref_frac
        psi = np.sum((cur_frac - ref_frac) * np.log(ratio))
    return float(np.clip(psi, 0.0, None))


def feature_drift(
    features: Sequence[str],
    reference_df: pd.DataFrame,
    current_df: pd.DataFrame,
    n_bins: int = 10,
) -> pd.DataFrame:
    """PSI per numeric feature between ``reference_df`` and ``current_df``."""
    rows: list[dict[str, Any]] = []
    for col in features:
        if col not in reference_df.columns or col not in current_df.columns:
            continue
        ref = reference_df[col].to_numpy()
        cur = current_df[col].to_numpy()
        rows.append({"feature": col, "psi": psi(ref, cur, n_bins)})
    out = pd.DataFrame(rows).sort_values("psi", ascending=False).reset_index(drop=True)
    out["status"] = np.where(
        out["psi"].isna(), "no-data",
        np.where(out["psi"] >= PSI_DRIFT_WARN, "drifted", "ok"),
    )
    return out


def data_quality_check(
    df: pd.DataFrame,
    expected_features: Sequence[str],
) -> dict[str, Any]:
    """Report missingness and schema surprises about ``df``."""
    present = [c for c in expected_features if c in df.columns]
    missing_cols = [c for c in expected_features if c not in df.columns]
    missing_pct = {c: float(df[c].isna().mean()) for c in present}
    return {
        "n_rows": int(len(df)),
        "n_expected_features": int(len(expected_features)),
        "n_present_features": len(present),
        "n_missing_columns": len(missing_cols),
        "missing_columns": missing_cols[:20],
        "worst_missing": sorted(missing_pct.items(), key=lambda kv: -kv[1])[:10],
        "unknown_columns": [c for c in df.columns if c not in set(expected_features)][:20],
    }