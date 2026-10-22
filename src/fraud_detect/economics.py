"""Decision economics: cost matrix, expected cost, cost-optimal policy, sweeps.

The threshold policy (``policy v1``) picks score cuts. This module picks the
action that minimises *expected monetary cost* per transaction, given the
model's fraud probability and the transaction amount. Every assumption is an
explicit, versioned field so finance can challenge (and change) it without a
retrain.

Costs are positive numbers = money lost. A safe APPROVE is the baseline (its
revenue is not counted as a gain, which keeps the comparison between policies
fair: both are measured against the same baseline).

Review is capacity-constrained (``max_review_rate``). The cost model alone
almost always prefers reviewing, because a $2 review beats a $25 chargeback;
real teams have a fixed number of analysts, so :func:`benefit_floor` turns that
capacity into a score cut that is applied at serving time.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import asdict, dataclass
from typing import Any

import numpy as np

APPROVE = "APPROVE"
MANUAL_REVIEW = "MANUAL_REVIEW"
DECLINE = "DECLINE"
ACTIONS: tuple[str, ...] = (APPROVE, MANUAL_REVIEW, DECLINE)

# Tie-break order for equal costs: prefer the least customer friction.
_TIE_BREAK = {APPROVE: 0, MANUAL_REVIEW: 1, DECLINE: 2}


@dataclass(frozen=True)
class CostModel:
    """Per-transaction cost assumptions (USD).

    Attributes:
        margin_rate: Gross margin earned on approved legitimate volume.
        review_cost: Fully-loaded cost of one manual review case.
        chargeback_fee: Network + operations cost of one realised fraud.
        friction_cost: Goodwill/support cost of one false decline.
        liability_rate: Share of the fraudulent amount the merchant absorbs.
        review_catch_rate: Share of reviewed frauds actually blocked; the rest
            still becomes a chargeback after review.
        max_review_rate: Review capacity as a share of traffic (0.05 = 5%).
            Review capacity is allocated to the largest review benefits, see
            :func:`benefit_floor`; it is not a cap on the reviewed share itself.
        version: Stable identifier recorded on every decision for audit.
    """

    margin_rate: float = 0.30
    review_cost: float = 2.00
    chargeback_fee: float = 25.00
    friction_cost: float = 1.50
    liability_rate: float = 1.00
    review_catch_rate: float = 0.85
    max_review_rate: float = 0.05
    version: str = "cost-v1"

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def expected_cost(model: CostModel, action: str, amount: float, probability: float) -> float:
    """Expected monetary cost of ``action`` for one transaction."""
    amount = max(float(amount), 0.0)
    p = min(max(float(probability), 0.0), 1.0)
    fraud_loss = amount * model.liability_rate + model.chargeback_fee
    if action == APPROVE:
        return p * fraud_loss
    if action == MANUAL_REVIEW:
        return model.review_cost + p * (1.0 - model.review_catch_rate) * fraud_loss
    if action == DECLINE:
        return (1.0 - p) * (amount * model.margin_rate + model.friction_cost)
    raise ValueError(f"unknown action: {action!r}")


def realized_cost(model: CostModel, action: str, amount: float, is_fraud: bool) -> float:
    """Cost actually incurred by ``action`` on a transaction with a known label."""
    amount = max(float(amount), 0.0)
    fraud_loss = amount * model.liability_rate + model.chargeback_fee
    if action == APPROVE:
        return fraud_loss if is_fraud else 0.0
    if action == MANUAL_REVIEW:
        residual = (1.0 - model.review_catch_rate) * fraud_loss if is_fraud else 0.0
        return model.review_cost + residual
    if action == DECLINE:
        return 0.0 if is_fraud else amount * model.margin_rate + model.friction_cost
    raise ValueError(f"unknown action: {action!r}")


def costs_for(model: CostModel, amount: float, probability: float) -> dict[str, float]:
    """Expected cost of every action, in a stable order."""
    return {a: round(expected_cost(model, a, amount, probability), 6) for a in ACTIONS}


def review_benefit(model: CostModel, amount: float, probability: float) -> float:
    """Expected money a review saves versus the better of approve/decline.

    Review capacity should go where it saves the most, and that saving is *not*
    monotone in the fraud probability: a very high score is cheaper to decline
    and a very low one cheaper to approve, so the mid-range is often where a
    human adds the most value. This number is what :func:`benefit_floor` gates.
    """
    costs = costs_for(model, amount, probability)
    best_other = min(costs[APPROVE], costs[DECLINE])
    return max(0.0, best_other - costs[MANUAL_REVIEW])


def benefit_floor(
    model: CostModel,
    amounts: Iterable[float] | Sequence[float],
    probs: Iterable[float] | Sequence[float],
    max_review_rate: float,
) -> float:
    """Review-benefit cut that keeps the reviewed share within capacity.

    Offline this is the ``k``-th largest benefit on a recent sample (``k`` =
    ``max_review_rate * n``); deploy it as ``DECISION_REVIEW_BENEFIT_FLOOR`` and
    the live policy reviews the same share of traffic, allocated by benefit.
    """
    amount_arr, prob_arr, _ = _as_arrays(amounts, probs, probs)
    n = int(amount_arr.size)
    rate = min(max(float(max_review_rate), 0.0), 1.0)
    if n == 0:
        return 0.0
    k = int(round(n * rate))
    if k <= 0:
        return float("inf")
    if k >= n:
        return 0.0
    benefits = _review_benefit_vector(model, amount_arr, prob_arr)
    return float(np.sort(benefits)[-k])


def _review_benefit_vector(
    model: CostModel, amount_arr: np.ndarray, prob_arr: np.ndarray
) -> np.ndarray:
    """Vectorised :func:`review_benefit`."""
    fraud_loss = amount_arr * model.liability_rate + model.chargeback_fee
    decline_p = amount_arr * model.margin_rate + model.friction_cost
    approve = prob_arr * fraud_loss
    review = model.review_cost + prob_arr * (1.0 - model.review_catch_rate) * fraud_loss
    decline = (1.0 - prob_arr) * decline_p
    return np.maximum(0.0, np.minimum(approve, decline) - review)


def decide(
    model: CostModel,
    amount: float,
    probability: float,
    *,
    benefit_floor: float | None = None,
) -> tuple[str, dict[str, float]]:
    """Cost-optimal action plus the full expected-cost table (for auditing).

    ``benefit_floor`` is the review-capacity cut (see :func:`benefit_floor`);
    when supplied, MANUAL_REVIEW is only a candidate if its expected saving is
    at least ``benefit_floor``.
    """
    costs = costs_for(model, amount, probability)
    candidates = list(ACTIONS)
    if (
        benefit_floor is not None
        and benefit_floor > 0.0
        and review_benefit(model, amount, probability) < benefit_floor
    ):
        candidates.remove(MANUAL_REVIEW)
    action = min(candidates, key=lambda a: (costs[a], _TIE_BREAK[a]))
    return action, costs


def breakeven_thresholds(model: CostModel, amount: float) -> dict[str, float]:
    """Probability cut-points where each action overtakes plain APPROVE.

    These are the *implied* thresholds of the cost model at this amount. They
    are reported on decisions that used the cost policy so downstream readers
    (audit report, LLM prompt) still find ``review_above`` / ``decline_above``.
    """
    amount = max(float(amount), 0.0)
    fraud_loss = amount * model.liability_rate + model.chargeback_fee
    decline_p = amount * model.margin_rate + model.friction_cost

    review_above = model.review_cost / (model.review_catch_rate * fraud_loss) if fraud_loss else 1.0
    denom = decline_p + fraud_loss
    decline_above = decline_p / denom if denom else 1.0
    return {
        "review_above": round(min(max(review_above, 0.0), 1.0), 6),
        "decline_above": round(min(max(decline_above, 0.0), 1.0), 6),
    }


def policy_action(review_above: float, decline_above: float, probability: float) -> str:
    """Threshold-policy action (v1 semantics) for one probability."""
    if probability >= decline_above:
        return DECLINE
    if probability >= review_above:
        return MANUAL_REVIEW
    return APPROVE


def _as_arrays(
    amounts: Iterable[float] | Sequence[float],
    probs: Iterable[float] | Sequence[float],
    labels: Iterable[Any] | Sequence[Any],
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    amount_arr = np.asarray(list(amounts), dtype=float)
    prob_arr = np.asarray(list(probs), dtype=float)
    label_arr = np.asarray([bool(x) for x in labels], dtype=bool)
    if not (amount_arr.shape == prob_arr.shape == label_arr.shape):
        raise ValueError("amounts, probs and labels must have the same length")
    return amount_arr, np.clip(prob_arr, 0.0, 1.0), label_arr


def _cost_vectors(
    model: CostModel, amount_arr: np.ndarray, prob_arr: np.ndarray
) -> dict[str, np.ndarray]:
    """Vectorised expected cost per action."""
    fraud_loss = amount_arr * model.liability_rate + model.chargeback_fee
    decline_p = amount_arr * model.margin_rate + model.friction_cost
    return {
        APPROVE: prob_arr * fraud_loss,
        MANUAL_REVIEW: model.review_cost + prob_arr * (1.0 - model.review_catch_rate) * fraud_loss,
        DECLINE: (1.0 - prob_arr) * decline_p,
    }


def _realized_vectors(
    model: CostModel, amount_arr: np.ndarray, label_arr: np.ndarray
) -> dict[str, np.ndarray]:
    """Vectorised realised cost per action."""
    fraud_loss = amount_arr * model.liability_rate + model.chargeback_fee
    decline_p = amount_arr * model.margin_rate + model.friction_cost
    return {
        APPROVE: np.where(label_arr, fraud_loss, 0.0),
        MANUAL_REVIEW: model.review_cost
        + np.where(label_arr, (1.0 - model.review_catch_rate) * fraud_loss, 0.0),
        DECLINE: np.where(label_arr, 0.0, decline_p),
    }


def _summarise(
    action: np.ndarray,
    cost_vectors: dict[str, np.ndarray],
    label_arr: np.ndarray,
) -> dict[str, Any]:
    n = int(action.size)
    if n == 0:
        return {
            "n": 0,
            "actions": {a: 0 for a in ACTIONS},
            "fraud_caught": 0,
            "fraud_missed": 0,
            "net_cost": 0.0,
            "costs": {a: 0.0 for a in ACTIONS},
            "cost_per_transaction": 0.0,
            "review_burden_pct": 0.0,
        }
    per_action = {a: float(np.sum(np.where(action == a, cost_vectors[a], 0.0))) for a in ACTIONS}
    net = float(sum(per_action.values()))
    return {
        "n": n,
        "actions": {a: int(np.sum(action == a)) for a in ACTIONS},
        "fraud_caught": int(np.sum(label_arr & (action != APPROVE))),
        "fraud_missed": int(np.sum(label_arr & (action == APPROVE))),
        "net_cost": round(net, 2),
        "costs": {a: round(v, 2) for a, v in per_action.items()},
        "cost_per_transaction": round(net / n, 4),
        "review_burden_pct": round(float(np.mean(action == MANUAL_REVIEW)) * 100.0, 2),
    }


def evaluate(  # noqa: PLR0913
    model: CostModel,
    *,
    amounts: Iterable[float],
    probs: Iterable[float],
    labels: Iterable[Any],
    review_above: float,
    decline_above: float,
) -> dict[str, Any]:
    """Realised economics of a threshold policy over labelled transactions."""
    if decline_above < review_above:
        raise ValueError("decline_above must be >= review_above")
    amount_arr, prob_arr, label_arr = _as_arrays(amounts, probs, labels)
    costs = _realized_vectors(model, amount_arr, label_arr)
    action = np.where(
        prob_arr >= decline_above,
        DECLINE,
        np.where(prob_arr >= review_above, MANUAL_REVIEW, APPROVE),
    )
    return {
        **_summarise(np.asarray(action), costs, label_arr),
        "kind": "threshold",
        "review_above": round(float(review_above), 4),
        "decline_above": round(float(decline_above), 4),
    }


def evaluate_cost_policy(  # noqa: PLR0913
    model: CostModel,
    *,
    amounts: Iterable[float],
    probs: Iterable[float],
    labels: Iterable[Any],
    benefit_floor: float = 0.0,
) -> dict[str, Any]:
    """Realised economics of the cost policy with capacity-gated reviews."""
    amount_arr, prob_arr, label_arr = _as_arrays(amounts, probs, labels)
    costs = _realized_vectors(model, amount_arr, label_arr)
    key = "review_benefit_floor"
    if amount_arr.size == 0:
        empty = _summarise(np.asarray([]), costs, label_arr)
        return {**empty, "kind": "cost", key: round(float(benefit_floor), 4)}
    ev = _cost_vectors(model, amount_arr, prob_arr)
    benefits = _review_benefit_vector(model, amount_arr, prob_arr)
    # Candidates: APPROVE/DECLINE always, MANUAL_REVIEW only above the floor.
    review_base = np.where(benefits >= benefit_floor, ev[MANUAL_REVIEW], np.inf)
    idx = np.argmin(np.vstack([ev[APPROVE], review_base, ev[DECLINE]]), axis=0)
    action = np.asarray([APPROVE, MANUAL_REVIEW, DECLINE])[idx]
    return {
        **_summarise(action, costs, label_arr),
        "kind": "cost",
        "policy_version": model.version,
        key: round(float(benefit_floor), 4),
    }


def sweep_cost_policy(  # noqa: PLR0913
    model: CostModel,
    *,
    amounts: Iterable[float],
    probs: Iterable[float],
    labels: Iterable[Any],
    review_grid: Iterable[float] | None = None,
    decline_grid: Iterable[float] | None = None,
) -> list[dict[str, Any]]:
    """Grid-sweep a two-threshold policy and return every evaluated point."""
    review_values = (
        list(review_grid)
        if review_grid is not None
        else list(np.round(np.arange(0.02, 0.62, 0.04), 4))
    )
    decline_values = (
        list(decline_grid)
        if decline_grid is not None
        else list(np.round(np.arange(0.10, 0.96, 0.05), 4))
    )
    amount_arr, prob_arr, label_arr = _as_arrays(amounts, probs, labels)
    rows: list[dict[str, Any]] = []
    for review_above in review_values:
        for decline_above in decline_values:
            if decline_above < review_above:
                continue
            rows.append(
                evaluate(
                    model,
                    amounts=amount_arr,
                    probs=prob_arr,
                    labels=label_arr,
                    review_above=float(review_above),
                    decline_above=float(decline_above),
                )
            )
    return rows


def best_point(rows: Sequence[dict[str, Any]], baseline_net_cost: float) -> dict[str, Any] | None:
    """Lowest-cost sweep row, annotated with savings vs the baseline policy."""
    if not rows:
        return None
    best = min(rows, key=lambda r: float(r["net_cost"]))
    saved = float(baseline_net_cost) - float(best["net_cost"])
    return {
        **best,
        "baseline_net_cost": round(float(baseline_net_cost), 2),
        "savings": round(saved, 2),
        "savings_per_1k": round(saved / max(int(best["n"]), 1) * 1000.0, 2),
    }
