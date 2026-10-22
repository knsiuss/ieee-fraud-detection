"""Unit tests for the cost model and cost-optimal decision policy.

These pin the arithmetic a reviewer has to trust: expected costs per action,
the cost-optimal decision being amount-aware, capacity-aware review, and the
offline evaluation used by the backtest script.
"""

from __future__ import annotations

import pytest

from fraud_detect import economics as eco

MODEL = eco.CostModel()


def test_expected_cost_monotonic_in_probability():
    probs = [0.0, 0.05, 0.2, 0.5, 0.8, 1.0]
    for amount in (5.0, 120.0, 900.0):
        approve = [eco.expected_cost(MODEL, eco.APPROVE, amount, p) for p in probs]
        assert approve == sorted(approve)
        decline = [eco.expected_cost(MODEL, eco.DECLINE, amount, p) for p in probs]
        assert decline == sorted(decline, reverse=True)


def test_cost_table_reports_every_action():
    costs = eco.costs_for(MODEL, 100.0, 0.3)
    assert set(costs) == {eco.APPROVE, eco.MANUAL_REVIEW, eco.DECLINE}
    for action, value in costs.items():
        assert value == pytest.approx(eco.expected_cost(MODEL, action, 100.0, 0.3), abs=1e-5)


def test_manual_review_cost_formula():
    amount, p = 200.0, 0.3
    fraud_loss = amount * MODEL.liability_rate + MODEL.chargeback_fee
    free = (1.0 - MODEL.review_catch_rate) * p * fraud_loss
    expected = MODEL.review_cost + free
    assert eco.expected_cost(MODEL, eco.MANUAL_REVIEW, amount, p) == pytest.approx(expected)


def test_realized_cost_matrix():
    amount = 100.0
    fraud_loss = amount * MODEL.liability_rate + MODEL.chargeback_fee
    friction = amount * MODEL.margin_rate + MODEL.friction_cost
    assert eco.realized_cost(MODEL, eco.APPROVE, amount, True) == pytest.approx(fraud_loss)
    assert eco.realized_cost(MODEL, eco.APPROVE, amount, False) == 0.0
    assert eco.realized_cost(MODEL, eco.MANUAL_REVIEW, amount, True) == pytest.approx(
        MODEL.review_cost + (1.0 - MODEL.review_catch_rate) * fraud_loss
    )
    assert eco.realized_cost(MODEL, eco.MANUAL_REVIEW, amount, False) == pytest.approx(
        MODEL.review_cost
    )
    assert eco.realized_cost(MODEL, eco.DECLINE, amount, True) == 0.0
    assert eco.realized_cost(MODEL, eco.DECLINE, amount, False) == pytest.approx(friction)


def test_unknown_action_is_rejected():
    with pytest.raises(ValueError):
        eco.realized_cost(MODEL, "NOT_AN_ACTION", 10.0, True)
    with pytest.raises(ValueError):
        eco.expected_cost(MODEL, "NOT_AN_ACTION", 10.0, 0.5)


def test_decide_is_amount_aware():
    # A 500.-transaction at p=0.12 is worth reviewing...
    assert eco.decide(MODEL, 500.0, 0.12)[0] == eco.MANUAL_REVIEW
    # ...while a 2.-one is cheaper to decline than to review.
    assert eco.decide(MODEL, 2.0, 0.12)[0] == eco.DECLINE
    # Low risk + high amount -> approve; high risk -> decline.
    assert eco.decide(MODEL, 5000.0, 1e-6)[0] == eco.APPROVE
    assert eco.decide(MODEL, 500.0, 0.8)[0] == eco.DECLINE
    action, costs = eco.decide(MODEL, 500.0, 0.12)
    assert costs[action] == min(costs.values())


def test_review_benefit_floor_blocks_cheap_reviews():
    assert eco.decide(MODEL, 500.0, 0.12, benefit_floor=0.0)[0] == eco.MANUAL_REVIEW
    benefit = eco.review_benefit(MODEL, 500.0, 0.12)
    assert benefit > 0.0
    blocked = eco.decide(MODEL, 500.0, 0.12, benefit_floor=benefit + 0.01)[0]
    costs = eco.costs_for(MODEL, 500.0, 0.12)
    assert blocked in {eco.APPROVE, eco.DECLINE}
    assert costs[blocked] == min(costs[eco.APPROVE], costs[eco.DECLINE])
    # A high score is cheaper to decline; reviewing it saves nothing.
    assert eco.review_benefit(MODEL, 500.0, 0.9) == 0.0
    assert eco.decide(MODEL, 500.0, 0.9, benefit_floor=1.0)[0] == eco.DECLINE


def test_benefit_floor_keeps_review_share_bounded():
    amounts = [100.0 + 10.0 * i for i in range(100)]
    probs = [i / 100.0 for i in range(100)]
    floor = eco.benefit_floor(MODEL, amounts, probs, 0.10)
    eligible = sum(
        1 for a, p in zip(amounts, probs, strict=True) if eco.review_benefit(MODEL, a, p) >= floor
    )
    assert eligible <= 10
    assert eco.benefit_floor(MODEL, [], [], 0.1) == 0.0
    assert eco.benefit_floor(MODEL, amounts, probs, 1.0) == 0.0
    # Zero capacity must exclude review entirely.
    assert eco.benefit_floor(MODEL, amounts, probs, 0.0) == float("inf")


def test_breakeven_thresholds_are_ordered_and_monotone():
    for amount in (10.0, 100.0, 1000.0):
        thresholds = eco.breakeven_thresholds(MODEL, amount)
        assert 0.0 <= thresholds["review_above"] <= thresholds["decline_above"] <= 1.0
    small = eco.breakeven_thresholds(MODEL, 10.0)
    large = eco.breakeven_thresholds(MODEL, 1000.0)
    assert large["review_above"] < small["review_above"]
    assert large["decline_above"] > small["decline_above"]


def test_evaluate_threshold_policy_matches_hand_calculation():
    rows = eco.evaluate(
        MODEL,
        amounts=[100.0, 50.0, 500.0, 20.0],
        probs=[0.9, 0.05, 0.3, 0.7],
        labels=[1, 0, 0, 1],
        review_above=0.15,
        decline_above=0.5,
    )
    # Rows 1 and 4: fraud declined -> no cost. Row 2: legit approved -> no
    # cost. Row 3: legit reviewed -> one review cost.
    assert rows["actions"] == {eco.APPROVE: 1, eco.MANUAL_REVIEW: 1, eco.DECLINE: 2}
    assert rows["costs"][eco.MANUAL_REVIEW] == pytest.approx(MODEL.review_cost)
    assert rows["net_cost"] == pytest.approx(MODEL.review_cost)
    assert rows["cost_per_transaction"] == pytest.approx(MODEL.review_cost / 4)
    assert rows["fraud_caught"] == 2
    assert rows["fraud_missed"] == 0
    assert rows["review_burden_pct"] == pytest.approx(25.0)


def test_evaluate_rejects_inverted_thresholds():
    with pytest.raises(ValueError):
        eco.evaluate(
            MODEL,
            amounts=[10.0],
            probs=[0.5],
            labels=[1],
            review_above=0.6,
            decline_above=0.4,
        )


def test_evaluate_cost_policy_respects_review_capacity():
    probs = [i / 100.0 for i in range(100)]
    labels = [1 if p > 0.5 else 0 for p in probs]
    amounts = [100.0] * 100
    floor = eco.benefit_floor(MODEL, amounts, probs, 0.5)
    result = eco.evaluate_cost_policy(
        MODEL, amounts=amounts, probs=probs, labels=labels, benefit_floor=floor
    )
    assert result["kind"] == "cost"
    assert result["n"] == 100
    assert result["review_burden_pct"] <= 50.01
    assert result["review_benefit_floor"] == pytest.approx(floor)
    assert sum(result["actions"].values()) == 100


def test_sweep_finds_lowest_cost_point():
    amounts = [50.0, 120.0, 400.0, 30.0, 900.0]
    probs = [0.01, 0.2, 0.7, 0.05, 0.55]
    labels = [0, 0, 1, 0, 0]
    rows = eco.sweep_cost_policy(
        MODEL,
        amounts=amounts,
        probs=probs,
        labels=labels,
        review_grid=[0.1, 0.3],
        decline_grid=[0.3, 0.6],
    )
    # Grid pairs with decline >= review only: (0.1,0.3), (0.1,0.6), (0.3,0.3), (0.3,0.6).
    assert len(rows) == 4
    best = eco.best_point(rows, baseline_net_cost=10_000.0)
    assert best is not None
    assert best["net_cost"] == min(r["net_cost"] for r in rows)
    assert best["savings"] == pytest.approx(10_000.0 - best["net_cost"], abs=0.02)


def test_empty_inputs_are_safe():
    empty = eco.evaluate(
        MODEL, amounts=[], probs=[], labels=[], review_above=0.15, decline_above=0.5
    )
    assert empty["n"] == 0
    assert empty["net_cost"] == 0.0
    assert eco.best_point([], baseline_net_cost=0.0) is None
