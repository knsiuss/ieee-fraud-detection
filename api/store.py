"""Versioned model store, feedback pool, and retrain gating.

The service keeps the currently served model in ``data/models/current/`` and
optionally trains candidates on demand. A candidate is **only swapped into
``current`` when it scores at least as well as the served model on the same
held-out validation split** — an anti-regression gate so the auto-learning
loop can never silently degrade the deployed model.

Reviewer feedback (from ``POST /api/feedback``) accumulates in
``data/feedback/feedback.jsonl`` and is folded into the next retrain.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import train_test_split

from fraud_detect import config, tuning
from fraud_detect.models import ModelBackend, select_feature_columns, train_model
from fraud_detect.serving import (
    ModelArtefact,
    align_features,
    load_artefact,
    median_baseline,
    predict_proba,
    save_artefact,
)

#: Served model lives in its own folder so a failed write never leaves a
#: half-written ``current``.
CURRENT_DIR: Path = config.MODEL_DIR / "current"
CANDIDATES_DIR: Path = config.MODEL_DIR / "candidates"
FEEDBACK_FILE: Path = config.DATA_ROOT / "feedback" / "feedback.jsonl"

GATE_MIN_IMPROVEMENT: float = 0.0  # >= current wins
HOLD_OUT_SIZE: float = 0.2
HOLD_OUT_SEED: int = 42


# Model store


def current_artefact() -> ModelArtefact:
    """Load the served model artefact (raises if not trained yet)."""
    return load_artefact(CURRENT_DIR)


def version(art: ModelArtefact) -> str:
    """Human-friendly version id for an artefact, derived from its metadata."""
    return str(art.meta.get("version") or art.meta.get("trained_at", "dev")[:16])


def model_info() -> dict[str, Any]:
    """Public metadata for ``GET /api/model``."""
    art = current_artefact()
    info = dict(art.meta)
    info.setdefault("version", version(art))
    info.setdefault("status", "ready")
    return info


def public_stats() -> dict[str, Any]:
    """Lightweight aggregates for the web UI's overview tab."""
    out: dict[str, Any] = {"model": model_info(), "overview": {}, "top_features": []}

    stats_csv = Path(__file__).resolve().parents[1] / "dashboard" / "data" / "overall_stats.csv"
    if stats_csv.exists():
        df = pd.read_csv(stats_csv)
        out["overview"] = {str(r["metric"]): r["value"] for _, r in df.iterrows()}

    mfi = Path(__file__).resolve().parents[1] / "dashboard" / "data" / "model_feat_importance.csv"
    if mfi.exists():
        top = pd.read_csv(mfi).head(10)
        out["top_features"] = [
            {"feature": str(r.feature), "importance": float(r.importance)} for r in top.itertuples()
        ]
    return out


# Feedback pool


def record_feedback(values: dict[str, float], verdict: int) -> int:
    """Persist one reviewed transaction into the retraining pool.

    The row is aligned to the **currently served** feature list, so the pool
    always holds the same schema the training code expects.
    """
    FEEDBACK_FILE.parent.mkdir(parents=True, exist_ok=True)
    art = current_artefact()
    row = align_features(pd.DataFrame([values]), art.features).iloc[0]
    record: dict[str, Any] = {c: float(row[c]) for c in art.features}
    record["isFraud"] = int(verdict)
    record["_reviewed_at"] = datetime.now(timezone.utc).isoformat()
    with FEEDBACK_FILE.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record) + "\n")
    return len(list(FEEDBACK_FILE.open(encoding="utf-8")))


def feedback_pool_df() -> pd.DataFrame:
    """Load reviewed transactions as a DataFrame (``features`` + ``isFraud``)."""
    if not FEEDBACK_FILE.exists():
        return pd.DataFrame()
    rows = [json.loads(line) for line in FEEDBACK_FILE.open(encoding="utf-8") if line.strip()]
    df = pd.DataFrame(rows)
    if "isFraud" not in df.columns:
        return pd.DataFrame()
    return df.drop(columns=["_reviewed_at"], errors="ignore")


def feedback_pool_size() -> int:
    """Number of reviewed transactions currently in the pool."""
    if not FEEDBACK_FILE.exists():
        return 0
    return sum(1 for line in FEEDBACK_FILE.open(encoding="utf-8") if line.strip())


# Training data


def data_table() -> pd.DataFrame:
    """Resolve the base training table (processed -> merged -> demo sample)."""
    candidates = [
        config.PROCESSED_TRAIN_PATH,
        config.MERGED_TRAIN_PATH,
        Path(__file__).resolve().parents[1] / "dashboard" / "data" / "sample.parquet",
    ]
    for path in candidates:
        if path.exists():
            return pd.read_parquet(path)
    raise FileNotFoundError(
        "No training data found. Run `python scripts/train_model.py` or add data."
    )


def held_out_split(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Stratified train/validation split with a fixed seed."""
    y = df[config.TARGET_COLUMN]
    train, val = train_test_split(
        df,
        test_size=HOLD_OUT_SIZE,
        stratify=y,
        random_state=HOLD_OUT_SEED,
    )
    return train, val


def eval_auc(artefact: ModelArtefact, df: pd.DataFrame) -> float:
    """ROC-AUC of ``artefact`` on the labelled rows of ``df``."""
    x = align_features(df, artefact.features)
    y = df[config.TARGET_COLUMN].astype(int).to_numpy()
    return float(roc_auc_score(y, predict_proba(artefact.model, x)))


# Retrain + gated swap


def _base_params() -> dict[str, Any]:
    tuned = tuning.load_best_params(ModelBackend.LIGHTGBM, fallback_to_defaults=True)
    return {**config.LGBM_PARAMS, **tuned}


def retrain_and_swap(data_df: pd.DataFrame | None = None) -> dict[str, Any]:
    """Train a candidate and swap it into ``current`` if it beats the gate.

    Steps
    -----
    1. Hold out a fixed validation split from the base data.
    2. Train a candidate on the rest + the reviewer feedback pool.
    3. Evaluate the served model and the candidate on the *same* validation.
    4. Swap only if ``candidate_auc >= current_auc``; otherwise discard.

    Returns a summary dict with ``swapped``, ``old_auc``, ``new_auc``.
    """
    try:
        current = current_artefact()
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(
            "No served model to compare against. Run `python scripts/train_model.py` first."
        ) from exc

    df = data_table() if data_df is None else data_df
    train_df, val_df = held_out_split(df)

    # Fold reviewer feedback into the training side only (validation stays
    # clean so it measures generalisation, not memory of reviewed rows).
    feedback = feedback_pool_df()
    if not feedback.empty:
        feats = select_feature_columns(train_df)
        fb_aligned = align_features(feedback, feats)
        fb_aligned[config.TARGET_COLUMN] = feedback[config.TARGET_COLUMN].astype(int)
        train_df = pd.concat(
            [train_df[feats + [config.TARGET_COLUMN]], fb_aligned],
            ignore_index=True,
        )

    result = train_model(train_df, backend=ModelBackend.LIGHTGBM, params=_base_params())
    candidate = result.model
    features = select_feature_columns(train_df)
    baseline = median_baseline(features, train_df)

    old_auc = eval_auc(current, val_df)
    new_auc = eval_auc(
        ModelArtefact(model=candidate, features=features, baseline=baseline, meta={}),
        val_df,
    )

    swapped = new_auc >= old_auc + GATE_MIN_IMPROVEMENT
    if swapped:
        profiles = {
            "nonfraud": median_baseline(features, df.loc[df[config.TARGET_COLUMN] == 0]),
            "fraud": median_baseline(features, df.loc[df[config.TARGET_COLUMN] == 1]),
        }
        meta = {
            "backend": "lightgbm",
            "roc_auc": new_auc,
            "train_auc": result.train_auc,
            "n_rows": int(len(train_df)),
            "n_features": len(features),
            "feedback_rows": int(len(feedback)),
            "trained_at": datetime.now(timezone.utc).isoformat(),
            "gate": "passed",
        }
        save_artefact(CURRENT_DIR, candidate, features, baseline, meta, profiles=profiles)
    else:
        # Keep a trace of the rejected candidate for reproducibility.
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
        save_artefact(CANDIDATES_DIR / f"rejected_{stamp}", candidate, features, baseline, {})

    return {
        "swapped": bool(swapped),
        "old_auc": old_auc,
        "new_auc": new_auc,
        "old_version": model_info().get("version"),
        "feedback_rows": int(len(feedback)),
        "reason": (
            "New model beats the served model on validation; swapped."
            if swapped
            else "New model did not beat the served model on validation; kept current."
        ),
    }
