"""Backfill labelled decisions from the historical training corpus.

The dashboard's money views (``/api/metrics/economics``, chargeback BPS,
measured-vs-counterfactual) need decisions whose true outcome is known. This
script closes that loop on a deterministic, labelled holdout:

1. load ``data/interim/train_merged.parquet`` (has ``isFraud``);
2. rebuild the same time-based holdout used by training (top 15 % of
   ``TransactionDT``) so the scored rows are not the model's training rows;
3. score them with the served artefact through the same ``predict_proba``
   path as the API, apply the configured threshold policy;
4. persist the decisions and label them in bulk from ``isFraud``.

Usage::

    PYTHONPATH=src python scripts/labelled_replay.py --limit 2000
    PYTHONPATH=src python scripts/labelled_replay.py --limit 2000 --dry-run
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "src"))

import pandas as pd  # noqa: E402

from fraud_detect import config, policy, serving  # noqa: E402

CONTRACT_VERSION = "v1"
HOLDOUT_FRACTION = 0.15
CHUNK = 512
REPLAY_PREFIX = "replay-"
NOTE = "labelled replay from time-split holdout"


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.environ[name])
    except (KeyError, ValueError):
        return default


def build_policy() -> policy.DecisionPolicy:
    """Threshold policy mirroring the API's env configuration."""
    review = _env_float("DECISION_REVIEW_ABOVE", policy.DEFAULT_POLICY.review_above)
    decline = _env_float("DECISION_DECLINE_ABOVE", policy.DEFAULT_POLICY.decline_above)
    if decline <= review:
        raise SystemExit("DECISION_DECLINE_ABOVE must be above DECISION_REVIEW_ABOVE")
    return policy.DecisionPolicy(
        version=policy.DEFAULT_POLICY.version,
        review_above=review,
        decline_above=decline,
    )


def load_holdout(limit: int, seed: int) -> pd.DataFrame:
    """Sample labelled rows from the time-based holdout tail."""
    if not config.MERGED_TRAIN_PATH.exists():
        raise SystemExit(
            f"Missing {config.MERGED_TRAIN_PATH}; run `python scripts/prepare_data.py` first."
        )
    frame = pd.read_parquet(
        config.MERGED_TRAIN_PATH,
        columns=["TransactionID", "TransactionDT", "isFraud"],
    )
    frame = frame.sort_values("TransactionDT", kind="mergesort").reset_index(drop=True)
    tail = frame.iloc[int(len(frame) * (1.0 - HOLDOUT_FRACTION)) :]
    if tail.empty:
        raise SystemExit("Holdout is empty; check the split fraction.")
    n = min(limit, len(tail))
    return tail.sample(n=n, random_state=seed).reset_index(drop=True)


def score_sample(sample: pd.DataFrame, artefact: serving.ModelArtefact) -> pd.DataFrame:
    """Score the sample with the served artefact and the live policy."""
    columns = list(
        dict.fromkeys([*artefact.features, "TransactionID", "isFraud", "TransactionAmt"])
    )
    frame = pd.read_parquet(config.MERGED_TRAIN_PATH, columns=columns)
    frame = frame.set_index("TransactionID").loc[sample["TransactionID"].tolist()].reset_index()

    pol = build_policy()
    probabilities: list[float] = []
    for start in range(0, len(frame), CHUNK):
        chunk = serving.align_features(frame.iloc[start : start + CHUNK], artefact.features)
        probabilities.extend(serving.predict_proba(artefact.model, chunk).tolist())

    decisions: list[str] = []
    actions: list[str] = []
    for prob in probabilities:
        decision, action = pol.apply(prob)
        decisions.append(decision.value)
        actions.append(action)

    frame["probability"] = probabilities
    frame["decision"] = decisions
    frame["action"] = actions
    return frame


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=2000, help="rows to replay")
    parser.add_argument("--seed", type=int, default=42, help="sampling seed")
    parser.add_argument(
        "--model-dir",
        type=Path,
        default=config.MODEL_DIR / "current",
        help="served artefact directory",
    )
    parser.add_argument("--dry-run", action="store_true", help="score but do not persist")
    args = parser.parse_args(argv)
    if args.limit <= 0:
        parser.error("--limit must be positive")

    from api import store  # local import: keeps --help fast and side-effect free

    artefact = serving.load_artefact(args.model_dir)
    sample = load_holdout(args.limit, args.seed)
    frame = score_sample(sample, artefact)

    version = store.version(artefact)
    pol = build_policy()
    existing = store.replay_transaction_ids()
    started = time.perf_counter()

    pending: list[tuple[str, float, str, str, float]] = []
    labels: list[tuple[str, str, str | None]] = []
    skipped = 0
    for row in frame.itertuples(index=False):
        tx = f"{REPLAY_PREFIX}{int(row.TransactionID)}"
        verdict = "fraud" if int(row.isFraud) == 1 else "safe"
        labels.append((tx, verdict, NOTE))
        if tx in existing:
            skipped += 1
            continue
        amount = float(getattr(row, "TransactionAmt", 0.0) or 0.0)
        pending.append((tx, float(row.probability), str(row.decision), str(row.action), amount))

    if not args.dry_run:
        for tx, prob, decision, action, amount in pending:
            store.record_decision(
                transaction_id=tx,
                model_version=version,
                contract_version=CONTRACT_VERSION,
                score=prob,
                decision=decision,
                action=action,
                policy_version=pol.version,
                thresholds=pol.as_dict(),
                reason_codes=[],
                feature_report={"source": "labelled_replay"},
                input_features={"TransactionAmt": amount},
                latency_ms=None,
            )
        updated = store.bulk_label(labels)
    else:
        updated = len(labels)

    elapsed = time.perf_counter() - started
    print(
        f"replayed {len(frame)} holdout rows: new={len(pending)} existing={skipped} "
        f"labelled={updated} dry_run={args.dry_run} in {elapsed:.1f}s"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
