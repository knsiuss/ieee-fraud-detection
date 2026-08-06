"""Honest model evaluation: random vs time-aware validation.

The IEEE-CIS transactions have a temporal axis (``TransactionDT``). A random
train/test split lets the model memorise time-correlated signal, which
inflates validation metrics. This script trains the same LightGBM on both a
random split and a time-ordered split, and reports the full metric set so the
gap is visible and honest.

Reported metrics
    - ROC-AUC and PR-AUC (skew-robust)
    - Brier score + calibration buckets (mean prediction vs actual rate)
    - precision / recall at fixed thresholds (0.15, 0.5)
    - precision / recall at realistic review capacities (top 1% and 5% of the
      riskiest transactions)
    - segment-level AUC: identity present/absent, early vs late half of the
      validation window, amount below/above median

Writes ``data/metadata/evaluation.json`` so the numbers are reproducible.

Usage
    python scripts/evaluate_model.py [--data PATH]
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

_SRC = Path(__file__).resolve().parents[1] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

import lightgbm as lgb  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from sklearn.metrics import (  # noqa: E402
    average_precision_score,
    brier_score_loss,
    confusion_matrix,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split  # noqa: E402

from fraud_detect import config, tuning  # noqa: E402
from fraud_detect.models import ModelBackend, select_feature_columns  # noqa: E402

OUT_PATH = config.METADATA_DIR / "evaluation.json"
TIME_QUANTILE = 0.8


def _params() -> dict:
    tuned = tuning.load_best_params(ModelBackend.LIGHTGBM, fallback_to_defaults=True)
    return {**config.LGBM_PARAMS, **tuned}


def _fit(x_tr, y_tr, x_va, y_va):
    params = _params()
    train_set = lgb.Dataset(x_tr, label=y_tr)
    val_set = lgb.Dataset(x_va, label=y_va, reference=train_set)
    return lgb.train(
        params,
        train_set,
        num_boost_round=config.LGBM_NUM_BOOST_ROUND,
        valid_sets=[val_set],
        valid_names=["valid"],
        callbacks=[
            lgb.early_stopping(config.LGBM_EARLY_STOPPING_ROUNDS, verbose=False),
            lgb.log_evaluation(0),
        ],
    )


def _calibration(y, probs, n_bins: int = 10) -> list[dict]:
    df = pd.DataFrame({"prob": probs, "y": y})
    df["bin"] = pd.qcut(df["prob"], n_bins, duplicates="drop")
    out = []
    for _, group in df.groupby("bin", observed=True):
        out.append(
            {
                "bin": f"{group['prob'].min():.3f}-{group['prob'].max():.3f}",
                "mean_pred": float(group["prob"].mean()),
                "actual_rate": float(group["y"].mean()),
                "n": int(len(group)),
            }
        )
    return out


def _metrics(y, probs) -> dict:
    y = np.asarray(y, dtype=int)
    probs = np.asarray(probs, dtype=float)
    n = len(y)
    out = {
        "roc_auc": float(roc_auc_score(y, probs)),
        "pr_auc": float(average_precision_score(y, probs)),
        "brier": float(brier_score_loss(y, probs)),
        "n": int(n),
        "fraud_rate": float(y.mean()),
    }
    for threshold in (0.15, 0.5):
        pred = (probs >= threshold).astype(int)
        out[f"precision@{threshold}"] = float(precision_score(y, pred, zero_division=0))
        out[f"recall@{threshold}"] = float(recall_score(y, pred, zero_division=0))
        out[f"flagged@{threshold}"] = float(pred.mean())
        tn, fp, fn, tp = confusion_matrix(y, pred).ravel()
        out[f"confusion@{threshold}"] = {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)}
    order = np.argsort(-probs)
    for cap in (0.01, 0.05):
        k = max(1, int(n * cap))
        flagged = y[order[:k]]
        out[f"precision_top{int(cap * 100)}pct"] = float(flagged.mean())
        out[f"recall_top{int(cap * 100)}pct"] = float(flagged.sum() / max(1, int(y.sum())))
    out["calibration"] = _calibration(y, probs)
    return out


def _segment_auc(y, probs, mask) -> float | None:
    y = np.asarray(y, dtype=int)
    probs = np.asarray(probs, dtype=float)
    mask = np.asarray(mask, dtype=bool)
    if mask.sum() < 50 or len(np.unique(y[mask])) < 2:
        return None
    return float(roc_auc_score(y[mask], probs[mask]))


def _segment_report(df, probs, y) -> dict:
    y_arr = y.to_numpy()
    has_id = df[[c for c in df.columns if c.startswith("id_")]].notna().any(axis=1).to_numpy()
    valid = df[config.TRANSACTION_DT_COLUMN].to_numpy()
    mid = valid.min() + 0.5 * (valid.max() - valid.min())
    amt = df["TransactionAmt"].to_numpy()
    amt_median = float(np.median(amt))
    return {
        "identity_present": _segment_auc(y_arr, probs, has_id),
        "identity_absent": _segment_auc(y_arr, probs, ~has_id),
        "valid_early_half": _segment_auc(y_arr, probs, valid < mid),
        "valid_late_half": _segment_auc(y_arr, probs, valid >= mid),
        "amount_high": _segment_auc(y_arr, probs, amt >= amt_median),
        "amount_low": _segment_auc(y_arr, probs, amt < amt_median),
    }


def _run_split(df, x, y, split_name: str) -> dict:
    if split_name == "random":
        x_tr, x_va, y_tr, y_va = train_test_split(
            x, y, test_size=1 - TIME_QUANTILE, stratify=y, random_state=config.RANDOM_STATE
        )
        val_df = df.loc[x_va.index]
    else:
        cut = df[config.TRANSACTION_DT_COLUMN].quantile(TIME_QUANTILE)
        train_mask = df[config.TRANSACTION_DT_COLUMN] < cut
        val_df = df.loc[~train_mask]
        x_tr, x_va = x.loc[train_mask], x.loc[~train_mask]
        y_tr, y_va = y.loc[train_mask], y.loc[~train_mask]

    model = _fit(x_tr, y_tr, x_va, y_va)
    probs = model.predict(x_va, num_iteration=model.best_iteration, num_threads=1)
    report = _metrics(y_va, probs)
    report["segments"] = _segment_report(val_df, probs, y_va)
    report["train_rows"] = int(len(x_tr))
    report["val_rows"] = int(len(x_va))
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", default=None, help="Override the training table.")
    args = parser.parse_args()

    path = Path(args.data) if args.data else config.MERGED_TRAIN_PATH
    print(f"Loading {path}")
    df = pd.read_parquet(path)

    features = select_feature_columns(df)
    x = df[features].fillna(-999).astype("float32")
    y = df[config.TARGET_COLUMN]

    print("Training + evaluating on RANDOM split …")
    random_report = _run_split(df, x, y, "random")
    print("Training + evaluating on TIME-ORDERED split …")
    time_report = _run_split(df, x, y, "time")

    report = {
        "data": {
            "source": str(path),
            "n_rows": int(len(df)),
            "n_features": len(features),
            "time_quantile_train": TIME_QUANTILE,
        },
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
        "random_split": random_report,
        "time_split": time_report,
    }
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print("\n=== Random split ===")
    print(
        f"  ROC-AUC {random_report['roc_auc']:.4f} | PR-AUC {random_report['pr_auc']:.4f}"
        f" | Brier {random_report['brier']:.4f}"
    )
    print(
        f"  precision@top1% {random_report['precision_top1pct']:.4f}"
        f" | @top5% {random_report['precision_top5pct']:.4f}"
    )
    print("\n=== Time-ordered split ===")
    print(
        f"  ROC-AUC {time_report['roc_auc']:.4f} | PR-AUC {time_report['pr_auc']:.4f}"
        f" | Brier {time_report['brier']:.4f}"
    )
    print(
        f"  precision@top1% {time_report['precision_top1pct']:.4f}"
        f" | @top5% {time_report['precision_top5pct']:.4f}"
    )
    print(f"\nReport written to {OUT_PATH}")


if __name__ == "__main__":
    main()
