"""Model serving helpers for the fraud-detection API.

This module contains the pure, framework-agnostic logic used to serve a
trained LightGBM model behind the FastAPI service: loading a serialised
artefact, aligning raw inputs to the model's feature space, computing risk
tiers, and explaining individual predictions with SHAP.

Nothing in this module depends on FastAPI or Streamlit, so it can be unit
tested in isolation and reused by scripts and notebooks.

The model is deliberately trained on **numeric columns only** (see
:func:`fraud_detect.models.select_feature_columns`); categorical / object
columns are dropped before training, so every serving path here is
responsible for producing a numeric DataFrame indexed to the exact feature
list the model was trained on.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd

from ._exceptions import MissingArtefactError

#: Value used to fill missing numeric cells before scoring — the same value
#: the training scripts use, so a missing feature is scored identically to
#: how the model saw missing values during training.
FILL_VALUE: float = -999.0

#: Risk-tier thresholds on the fraud probability. Tuned on the validation
#: split of this dataset; the same cut-offs are used across the API and UI.
RISK_LOW: float = 0.15
RISK_MEDIUM: float = 0.50

#: Default name for serialised artefacts inside a model directory.
MODEL_FILE: str = "model.joblib"
FEATURES_FILE: str = "features.json"
BASELINE_FILE: str = "baseline.json"
META_FILE: str = "meta.json"


@dataclass(frozen=True)
class RiskTier:
    """A risk category and the recommended action for a transaction."""

    label: str
    action: str


@dataclass(frozen=True)
class ModelArtefact:
    """Everything needed to serve one trained model version.

    Attributes
    ----------
    model:
        The fitted LightGBM Booster (or any object exposing ``predict``).
    features:
        Ordered feature names the model was trained on. Inputs must be
        aligned to this list before prediction.
    baseline:
        One-row DataFrame (indexed to ``features``) used as the neutral
        default when the caller only supplies a handful of inputs.
    profiles:
        Optional named one-row baselines (e.g. ``fraud`` / ``nonfraud``)
        representing the median of a segment, for the friendly simulator.
    meta:
        Free-form metadata (ROC-AUC, trained timestamp, etc.).
    """

    model: Any
    features: list[str]
    baseline: pd.DataFrame
    meta: dict[str, Any]
    profiles: dict[str, pd.DataFrame] = field(default_factory=dict)


def risk_tier(prob: float) -> RiskTier:
    """Map a fraud probability to a risk tier and a recommended action.

    Examples
    --------
    >>> risk_tier(0.05).label
    'low'
    >>> risk_tier(0.30).label
    'medium'
    >>> risk_tier(0.90).label
    'high'
    """
    if prob < RISK_LOW:
        return RiskTier(
            label="low",
            action="Approve. Transaction looks legitimate.",
        )
    if prob < RISK_MEDIUM:
        return RiskTier(
            label="medium",
            action="Review. Request additional verification (OTP / MFA).",
        )
    return RiskTier(
        label="high",
        action="Block. Pattern strongly matches known fraud.",
    )


def align_features(df: pd.DataFrame, features: list[str]) -> pd.DataFrame:
    """Align ``df`` to the model's feature list.

    Columns not present in ``df`` are added as ``FILL_VALUE``; extra columns
    are dropped. Present-but-empty cells are passed through unchanged — the
    model was trained on NaN natively, so a missing cell is scored the same
    way at serving time. The result has exactly ``len(features)`` columns in
    training order, so it can be fed straight to ``model.predict``.

    Examples
    --------
    >>> df = pd.DataFrame({"TransactionAmt": [120.0], "extra": [1]})
    >>> out = align_features(df, ["TransactionAmt", "C1"])
    >>> list(out.columns)
    ['TransactionAmt', 'C1']
    >>> float(out.iloc[0]["C1"])
    -999.0
    >>> import math
    >>> math.isnan(float(out.iloc[0]["TransactionAmt"]))
    False
    """
    frame = pd.DataFrame(FILL_VALUE, index=df.index, columns=features)
    present = [c for c in features if c in df.columns]
    if present:
        frame[present] = df[present].to_numpy()
    return frame.astype("float32")


def median_baseline(features: list[str], reference_df: pd.DataFrame) -> pd.DataFrame:
    """Build a one-row 'typical transaction' baseline from ``reference_df``.

    Used by the single-transaction scorer: the analyst only edits a handful of
    fields and every other feature defaults to the median seen at training
    time (or ``FILL_VALUE`` for features missing from the reference table).

    Examples
    --------
    >>> ref = pd.DataFrame({"a": [1.0, 2.0, 3.0], "b": [10.0, 20.0, 30.0]})
    >>> row = median_baseline(["a", "b", "c"], ref)
    >>> list(row.columns)
    ['a', 'b', 'c']
    >>> float(row.iloc[0]["a"])
    2.0
    """
    medians: dict[str, float] = {}
    for col in features:
        if col in reference_df.columns and pd.api.types.is_numeric_dtype(reference_df[col]):
            medians[col] = float(reference_df[col].median(skipna=True))
        else:
            medians[col] = FILL_VALUE
    row = pd.DataFrame([medians], columns=features).astype("float32")
    return row


def predict_proba(
    model: Any,
    features: pd.DataFrame,
    n_threads: int = 1,
) -> np.ndarray:
    """Return class-1 (fraud) probabilities for ``features``.

    ``n_threads`` defaults to 1 to avoid the LightGBM OpenMP oversubscription
    hang that previously froze the dashboard in threaded web workers. When the
    model was trained with early stopping, prediction uses its
    ``best_iteration`` so overfit trailing trees do not distort scores.
    """
    kwargs: dict[str, int] = {"num_threads": n_threads}
    best = getattr(model, "best_iteration", None)
    if best is not None:
        kwargs["num_iteration"] = best
    probs = model.predict(features, **kwargs)
    return np.asarray(probs, dtype="float64")


def save_artefact(  # noqa: PLR0913
    artefact_dir: Path | str,
    model: Any,
    features: list[str],
    baseline: pd.DataFrame,
    meta: dict[str, Any] | None = None,
    profiles: dict[str, pd.DataFrame] | None = None,
) -> Path:
    """Serialise a model version into ``artefact_dir`` and return the path.

    Writes ``model.joblib``, ``features.json``, ``baseline.json`` and
    ``meta.json`` so a deployed service can load everything from one folder.
    Named segment medians in ``profiles`` are written as ``baseline_<name>.json``.
    """
    out = Path(artefact_dir)
    out.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, out / MODEL_FILE)
    (out / FEATURES_FILE).write_text(json.dumps(features), encoding="utf-8")
    baseline.to_json(out / BASELINE_FILE, orient="records")
    (out / META_FILE).write_text(json.dumps(meta or {}, indent=2), encoding="utf-8")
    for name, row in (profiles or {}).items():
        (out / f"baseline_{name}.json").write_text(
            row.reset_index(drop=True).to_json(orient="records"),
            encoding="utf-8",
        )
    return out


def load_artefact(artefact_dir: Path | str) -> ModelArtefact:
    """Load a serialised model version from ``artefact_dir``.

    Raises
    ------
    MissingArtefactError
        If any of the required files is missing.
    """
    d = Path(artefact_dir)
    model_path = d / MODEL_FILE
    features_path = d / FEATURES_FILE
    baseline_path = d / BASELINE_FILE

    missing = [p.name for p in (model_path, features_path, baseline_path) if not p.exists()]
    if missing:
        raise MissingArtefactError(
            f"Model artefact incomplete in {d}. Missing: {', '.join(missing)}. "
            "Run `python scripts/train_model.py` first."
        )

    model = joblib.load(model_path)
    features = json.loads(features_path.read_text(encoding="utf-8"))
    baseline = pd.read_json(baseline_path, orient="records").astype("float32")
    meta_path = d / META_FILE
    meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}

    profiles: dict[str, pd.DataFrame] = {}
    for profile_path in sorted(d.glob("baseline_*.json")):
        if profile_path.name == BASELINE_FILE:
            continue
        name = profile_path.stem.removeprefix("baseline_")
        profiles[name] = pd.read_json(profile_path, orient="records").astype("float32")

    return ModelArtefact(
        model=model,
        features=list(features),
        baseline=baseline,
        meta=meta,
        profiles=profiles,
    )


#: Human-readable labels for the most informative features. Features without
#: a label fall back to their raw (often anonymised) name.
FEATURE_LABELS: dict[str, str] = {
    "TransactionAmt": "Transaction amount",
    "card1": "Card issuer code",
    "card2": "Card count (bank id)",
    "card4": "Card network",
    "card5": "Card count (bank)",
    "card6": "Card type",
    "addr1": "Billing address region",
    "addr2": "Billing address city",
    "dist1": "Billing distance",
    "C1": "Card match count",
    "C2": "Card count in 1 hour",
    "C5": "Address count",
    "C6": "Address count in 1 hour",
    "C7": "Address count in 24h",
    "C8": "Address count in 10 days",
    "C13": "Transaction frequency",
    "C14": "Transaction frequency in 1h",
    "D1": "Days since last activity",
    "D2": "Days since last address change",
    "D4": "Days since last card change",
    "D5": "Days since last card change (2)",
    "D10": "Days since last device",
    "D15": "Days since last login",
    "P_emaildomain": "Purchaser email domain",
    "R_emaildomain": "Recipient email domain",
    "id_02": "Device signal (browser)",
    "id_20": "Device signal (session)",
    "id_30": "Device signal (screen)",
}


def _shap_values(model: Any, features: pd.DataFrame) -> np.ndarray:
    """SHAP log-odds contributions for the first row, aligned to ``features``."""
    import shap  # noqa: PLC0415

    explainer = shap.TreeExplainer(model)
    raw = explainer.shap_values(features.iloc[:1].to_numpy())
    # Binary LightGBM returns [neg_class, pos_class]; keep the pos-class row.
    values = np.asarray(raw[-1]) if isinstance(raw, list) else np.asarray(raw)
    return np.ravel(values)


def explain_top_features(
    model: Any,
    features: pd.DataFrame,
    feature_names: list[str],
    top_n: int = 10,
) -> pd.DataFrame:
    """Return the top-``n`` SHAP contributors for the first row of ``features``.

    Positive contributions push the prediction toward fraud, negative ones
    toward safe. Columns: ``feature``, ``contribution``, ``direction``.

    Requires the optional ``shap`` dependency; returns an empty DataFrame if
    it is not installed.
    """
    try:
        values = _shap_values(model, features)
    except ImportError:
        return pd.DataFrame(columns=["feature", "contribution", "direction"])

    out = pd.DataFrame({"feature": feature_names, "contribution": values})
    out["abs_contribution"] = out["contribution"].abs()
    out = out.sort_values("abs_contribution", ascending=False).head(top_n)
    out["direction"] = np.where(out["contribution"] >= 0, "fraud", "safe")
    return out.reset_index(drop=True)[["feature", "contribution", "direction"]]


def decision_drivers(
    model: Any,
    features: pd.DataFrame,
    feature_names: list[str],
    baseline: pd.DataFrame,
    top_n: int = 4,
) -> list[dict[str, Any]]:
    """Describe the top drivers of a prediction in human-readable terms.

    Each driver carries the actual value, the training median, and the
    direction the feature pushes the decision. Empty list if SHAP is missing.
    """
    try:
        contributions = _shap_values(model, features)
    except ImportError:
        return []

    row = features.iloc[0]
    idx = np.argsort(np.abs(contributions))[::-1][:top_n]
    drivers: list[dict[str, Any]] = []
    for i in idx:
        name = feature_names[i]
        value = float(row[name])
        typical = float(baseline[name].iloc[0]) if name in baseline.columns else None
        # Present-but-empty cells arrive as NaN (LightGBM scores them natively);
        # report them as "missing" rather than the raw 'nan' string.
        missing = value == FILL_VALUE or not math.isfinite(value)
        drivers.append(
            {
                "feature": name,
                "label": FEATURE_LABELS.get(name, name),
                "value": None if missing else value,
                "typical": None if typical == FILL_VALUE else typical,
                "value_text": "missing" if missing else f"{value:g}",
                "typical_text": "missing" if typical in (None, FILL_VALUE) else f"{typical:g}",
                "contribution": float(contributions[i]),
                "direction": "fraud" if contributions[i] >= 0 else "safe",
            }
        )
    return drivers


def decision_summary(
    probability: float,
    tier: str,
    drivers: list[dict[str, Any]],
    action: str,
) -> str:
    """One plain-English paragraph explaining a prediction."""
    lead = f"{tier.upper()} risk — {probability * 100:.0f}% fraud probability."
    if not drivers:
        return f"{lead} {action}"
    clauses = []
    for driver in drivers[:3]:
        if driver["value_text"] == "missing":
            clauses.append(f"{driver['label']} is unknown to the model")
        else:
            effect = "raises risk" if driver["direction"] == "fraud" else "lowers risk"
            clause = (
                f"{driver['label']} at {driver['value_text']} (typical {driver['typical_text']})"
            )
            clauses.append(f"{clause} {effect}")
    return f"{lead} Main signals: {'; '.join(clauses)}. {action}"
