"""Fit a probability calibrator for the served model and report the gain.

The served LightGBM scores rank risk well but are not calibrated likelihoods.
This script fits a monotone calibrator on the labelled time-split holdout and
reports ECE/Brier before and after on a disjoint evaluation half.

Usage::

    PYTHONPATH=src python scripts/calibrate_model.py
    PYTHONPATH=src python scripts/calibrate_model.py --method platt --limit 40000
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "src"))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from fraud_detect import calibration, config, serving  # noqa: E402

HOLDOUT_FRACTION = 0.15
CHUNK = 512
OUTPUT = config.DATA_ROOT / "metadata" / "calibration.json"


def _score(frame: pd.DataFrame, artefact: serving.ModelArtefact) -> np.ndarray:
    probs: list[np.ndarray] = []
    for start in range(0, len(frame), CHUNK):
        chunk = serving.align_features(frame.iloc[start : start + CHUNK], artefact.features)
        probs.append(serving.predict_proba(artefact.model, chunk))
    return np.concatenate(probs)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--method", default="isotonic", choices=list(calibration.METHODS))
    parser.add_argument("--limit", type=int, default=60000, help="max holdout rows to score")
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument(
        "--model-dir",
        type=Path,
        default=config.MODEL_DIR / "current",
        help="served artefact directory",
    )
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args(argv)

    if not config.MERGED_TRAIN_PATH.exists():
        raise SystemExit(f"Missing {config.MERGED_TRAIN_PATH}; run scripts/prepare_data.py first.")

    artefact = serving.load_artefact(args.model_dir)
    frame = pd.read_parquet(
        config.MERGED_TRAIN_PATH,
        columns=list(dict.fromkeys([*artefact.features, "TransactionDT", "isFraud"])),
    ).sort_values("TransactionDT", kind="mergesort")
    holdout = frame.iloc[int(len(frame) * (1.0 - HOLDOUT_FRACTION)) :]
    if len(holdout) > args.limit:
        holdout = holdout.sample(n=args.limit, random_state=args.seed)
    holdout = holdout.reset_index(drop=True)

    probs = _score(holdout, artefact)
    y = holdout["isFraud"].to_numpy(dtype="int64")
    if len(np.unique(y)) < 2:
        raise SystemExit("Holdout has a single class; cannot calibrate.")

    # Calibrate on one half, evaluate on the other (never the same rows).
    rng = np.random.default_rng(args.seed)
    order = rng.permutation(len(y))
    split = len(y) // 2
    fit_idx, eval_idx = order[:split], order[split:]
    calibrator = calibration.fit_calibrator(y[fit_idx], probs[fit_idx], args.method)
    calibrated = calibrator.apply(probs[eval_idx])

    report = {
        "version": calibrator.version,
        "method": calibrator.method,
        "n_fit": int(split),
        "n_eval": int(len(y) - split),
        "base_rate": round(float(y.mean()), 6),
        "raw": {
            "ece": round(calibration.expected_calibration_error(y[eval_idx], probs[eval_idx]), 6),
            "brier": round(calibration.brier_score(y[eval_idx], probs[eval_idx]), 6),
        },
        "calibrated": {
            "ece": round(calibration.expected_calibration_error(y[eval_idx], calibrated), 6),
            "brier": round(calibration.brier_score(y[eval_idx], calibrated), 6),
        },
        "reliability_raw": calibration.reliability_bins(y[eval_idx], probs[eval_idx]),
        "reliability_calibrated": calibration.reliability_bins(y[eval_idx], calibrated),
        "calibrator": calibrator.as_dict(),
        "note": (
            "Fit on the time-split holdout, evaluated on a disjoint half. "
            "Reported ECE/Brier are out-of-fit estimates, not guarantees."
        ),
    }
    calibration.save_calibrator(calibrator, args.output)
    sidecar = args.output.with_name(args.output.stem + "_report.json")
    sidecar.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(
        f"calibrator {calibrator.method} saved to {args.output} | "
        f"ECE {report['raw']['ece']:.4f} -> {report['calibrated']['ece']:.4f} | "
        f"Brier {report['raw']['brier']:.6f} -> {report['calibrated']['brier']:.6f} | "
        f"n_fit={report['n_fit']} n_eval={report['n_eval']} | report {sidecar}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
