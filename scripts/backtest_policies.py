"""Offline policy backtest: threshold policy vs cost-optimal decisioning.

Scores a labelled sample with the *served* model, then compares the expected
net monetary cost of three decision policies on exactly the same transactions:

1. **deployed threshold policy v1** -- review >= 0.15, decline >= 0.50 (the
   policy the demo ships with).
2. **best fixed threshold pair** -- the lowest-cost point of a two-threshold
   grid sweep. This is an optimistic bound for *any* threshold policy.
3. **best fixed pair within review capacity** -- the fair baseline: same
   maximum review share as the cost policy, so the comparison isolates *where*
   capacity is spent, not how much of it is available.
4. **cost-optimal decisioning** -- per-transaction expected-cost minimisation
   with a review-benefit floor (what ``DECISION_POLICY=cost`` does live).

The point is to make the business case reviewable: every number is derived from
the same cost model the service uses, and the report states its assumptions and
caveats instead of hiding them.

Writes ``data/metadata/policy_backtest.json``.

Usage
-----
    python scripts/backtest_policies.py [--limit 200000] [--data PATH] [--out PATH]
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

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from fraud_detect import config, economics, serving  # noqa: E402
from fraud_detect.policy import DEFAULT_POLICY  # noqa: E402

OUT_PATH = config.METADATA_DIR / "policy_backtest.json"
MODEL_DIR = config.MODEL_DIR / "current"


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--data", type=Path, default=config.MERGED_TRAIN_PATH)
    parser.add_argument("--limit", type=int, default=200_000, help="max rows to score")
    parser.add_argument("--out", type=Path, default=OUT_PATH)
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args(argv)


def _savings(policy: dict, baseline_net_cost: float, n: int) -> dict[str, float]:
    saved = round(float(baseline_net_cost) - float(policy["net_cost"]), 2)
    return {
        "savings_vs_v1": saved,
        "savings_per_1k": round(saved / max(n, 1) * 1000.0, 2),
    }


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    if not Path(args.data).exists():
        print(f"error: data file not found: {args.data}", file=sys.stderr)
        return 2
    art = serving.load_artefact(MODEL_DIR)

    df = pd.read_parquet(args.data)
    if args.limit and len(df) > args.limit:
        df = df.sample(n=args.limit, random_state=args.seed).reset_index(drop=True)
    if config.TARGET_COLUMN not in df.columns:
        print(f"error: {config.TARGET_COLUMN!r} missing from {args.data}", file=sys.stderr)
        return 2

    amounts = df["TransactionAmt"].astype(float).to_numpy()
    labels = df[config.TARGET_COLUMN].astype(bool).to_numpy()
    probs = np.asarray(serving.predict_proba(art.model, serving.align_features(df, art.features)))
    model = economics.CostModel()

    threshold = economics.evaluate(
        model,
        amounts=amounts,
        probs=probs,
        labels=labels,
        review_above=DEFAULT_POLICY.review_above,
        decline_above=DEFAULT_POLICY.decline_above,
    )
    sweep = economics.sweep_cost_policy(
        model,
        amounts=amounts,
        probs=probs,
        labels=labels,
        review_grid=np.round(np.arange(0.02, 0.62, 0.05), 4),
        decline_grid=np.round(np.arange(0.10, 0.96, 0.05), 4),
    )
    best_fixed = economics.best_point(sweep, baseline_net_cost=threshold["net_cost"])
    # Apples-to-apples baseline: the best fixed pair that respects the same
    # review capacity the cost policy is allowed to use.
    capacity_pct = model.max_review_rate * 100.0
    within_capacity = [r for r in sweep if r["review_burden_pct"] <= capacity_pct + 0.01]
    best_fixed_capacity = economics.best_point(
        within_capacity, baseline_net_cost=threshold["net_cost"]
    )
    if best_fixed_capacity is None:
        best_fixed_capacity = {**threshold, "note": "no swept pair fits review capacity"}
    floor = economics.benefit_floor(model, amounts, probs, model.max_review_rate)
    cost_policy = economics.evaluate_cost_policy(
        model, amounts=amounts, probs=probs, labels=labels, benefit_floor=floor
    )

    n = threshold["n"]
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "dataset": {
            "path": str(Path(args.data)),
            "rows": n,
            "fraud_rate_pct": round(float(np.mean(labels)) * 100.0, 3),
            "total_amount": round(float(np.sum(amounts)), 2),
            "avg_amount": round(float(np.mean(amounts)), 2),
        },
        "model": {
            "version": art.meta.get("version"),
            "features": len(art.features),
        },
        "cost_model": model.as_dict(),
        "capacity": {
            "max_review_rate_pct": round(model.max_review_rate * 100.0, 2),
            "review_benefit_floor": round(floor, 4),
            "recommended_env": {
                "DECISION_POLICY": "cost",
                "DECISION_REVIEW_BENEFIT_FLOOR": round(floor, 4),
            },
        },
        "policies": {
            "threshold_v1": {
                **threshold,
                "policy_version": DEFAULT_POLICY.version,
            },
            "threshold_best_fixed": {
                **best_fixed,
                **_savings(best_fixed, threshold["net_cost"], n),
            },
            "threshold_best_within_capacity": {
                **best_fixed_capacity,
                **_savings(best_fixed_capacity, threshold["net_cost"], n),
            },
            "cost_optimal": {**cost_policy, **_savings(cost_policy, threshold["net_cost"], n)},
        },
        "caveats": [
            "Net cost is defined by the stated cost model, not by accounting data.",
            "The best fixed threshold is an in-sample upper bound for threshold policies.",
            "The cost policy is scored on the stored scores of the same model.",
            "threshold_best_within_capacity is the fair baseline: same review capacity,"
            " best fixed thresholds.",
            "Fraud losses apply liability_rate; margin uses gross margin on the sale.",
        ],
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2), encoding="utf-8")

    header = f"{'policy':<20}{'net cost':>14}{'per txn':>10}{'fraud caught':>14}{'review %':>10}"
    print(header)
    print("-" * len(header))
    for name in (
        "threshold_v1",
        "threshold_best_fixed",
        "threshold_best_within_capacity",
        "cost_optimal",
    ):
        row = report["policies"][name]
        print(
            f"{name:<20}{row['net_cost']:>14,.2f}{row['cost_per_transaction']:>10.2f}"
            f"{row['fraud_caught']:>14}{row['review_burden_pct']:>10.2f}"
        )
    print(f"\nwrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
