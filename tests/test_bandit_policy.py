"""Tests for fraud_detect.bandit_policy — adaptive decision layer (v2)."""

from __future__ import annotations

import random

from fraud_detect.bandit_policy import (
    BANDIT_VERSION,
    CONTEXT_DIM,
    BanditPolicy,
    BanditState,
    build_context,
    evaluate_off_policy,
    fit_offline,
    maybe_promote_bandit,
    reward_for,
)


class TestReward:
    def test_decline_correct_positive(self):
        assert reward_for("DECLINE", "fraud") == 1.0

    def test_decline_overturned_large_penalty(self):
        assert reward_for("DECLINE", "safe") == -2.5

    def test_approve_correct_small_positive(self):
        assert reward_for("APPROVE", "safe") == 0.5

    def test_approve_slipped_fraud_largest_penalty(self):
        assert reward_for("APPROVE", "fraud") == -3.0
        assert reward_for("APPROVE", "fraud") < reward_for("DECLINE", "safe")

    def test_review_rows_defined(self):
        assert reward_for("MANUAL_REVIEW", "fraud") == 0.8
        assert reward_for("MANUAL_REVIEW", "safe") == 0.1

    def test_unknown_outcome_no_reward(self):
        assert reward_for("DECLINE", "pending") is None
        assert reward_for("DECLINE", None) is None


class TestContext:
    def test_dimension(self):
        ctx = build_context(0.4, [], {"TransactionAmt": 120.0})
        assert len(ctx) == CONTEXT_DIM
        assert ctx[-1] == 1.0  # intercept

    def test_score_and_amount(self):
        ctx = build_context(0.7, [], {"TransactionAmt": 100.0})
        assert ctx[0] == 0.7
        assert abs(ctx[1] - 0.0) < 1.0

    def test_drivers_sorted_and_padded(self):
        drivers = [
            {"contribution": 0.1},
            {"contribution": 3.0},
            {"contribution": -2.0},
        ]
        ctx = build_context(0.5, drivers, {})
        top4 = ctx[2:6]
        assert top4[0] == 3.0
        assert top4[1] == -2.0
        assert top4[2] == 0.1

    def test_missing_amount_maps_to_zero(self):
        ctx = build_context(0.5, [], {})
        assert ctx[1] == 0.0


class TestDecide:
    def test_auto_action_above_cutoff(self):
        policy = BanditPolicy(audit_sample_rate=0.0, rng=random.Random(0))
        state = BanditState()
        choice = policy.decide(0.97, [0.97, 0.0, 0, 0, 0, 0, 1.0], state)
        assert choice.decision.value == "DECLINE"
        assert choice.auto_actioned is True
        assert choice.needs_review is False
        assert choice.reason_code.startswith("bandit:auto-decline")

    def test_auto_action_audit_sample(self):
        policy = BanditPolicy(audit_sample_rate=1.0, rng=random.Random(1))
        state = BanditState()
        choice = policy.decide(0.97, [0.97] + [0.0] * 6, state)
        assert choice.auto_actioned is True
        assert choice.audit_sampled is True
        assert choice.needs_review is True  # sampled => routed back to review

    def test_below_cutoff_is_not_auto_actioned(self):
        policy = BanditPolicy(rng=random.Random(2))
        state = BanditState()
        choice = policy.decide(0.30, [0.30] + [0.0] * 6, state)
        assert choice.auto_actioned is False

    def test_greedy_prefers_rewarding_arm(self):
        policy = BanditPolicy(epsilon=0.0, rng=random.Random(3))
        state = BanditState()
        context = build_context(0.5, [], {"TransactionAmt": 50.0})
        # Make APPROVE clearly the best arm by rewarding it richly.
        state.arm("APPROVE").update(context, 1.0)
        state.arm("APPROVE").update(context, 1.0)
        choice = policy.decide(0.5, context, state)
        assert choice.decision.value == "APPROVE"

    def test_exploration_when_epsilon_high(self):
        policy = BanditPolicy(epsilon=1.0, rng=random.Random(4))
        state = BanditState()
        choice = policy.decide(0.3, [0.3] + [0.0] * 6, state)
        assert choice.explored is True
        assert abs(choice.propensity - 1.0 / 3) < 1e-9

    def test_propensity_strictly_positive(self):
        policy = BanditPolicy(epsilon=0.05, rng=random.Random(5))
        state = BanditState()
        choice = policy.decide(0.3, [0.3] + [0.0] * 6, state)
        assert 0 < choice.propensity <= 1.0


class TestStatePersistence:
    def test_save_load_roundtrip(self, tmp_path):
        state = BanditState()
        state.arm("DECLINE").update([1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0], 2.0)
        state.n_decisions = 4
        path = tmp_path / "bandit_v2.json"
        from fraud_detect.bandit_policy import load_state, save_state

        save_state(state, path)
        loaded = load_state(path)
        assert loaded is not None
        assert loaded.version == BANDIT_VERSION
        assert loaded.arms["DECLINE"].n == 1
        assert loaded.arms["DECLINE"].b[0] == 2.0

    def test_load_missing_returns_none(self, tmp_path):
        from fraud_detect.bandit_policy import load_state

        assert load_state(tmp_path / "nope.json") is None


class TestOffPolicy:
    def test_fit_offline_updates_arms(self):
        events = [
            {"context": [1.0, 0, 0, 0, 0, 0, 1.0], "action": "DECLINE", "reward": 1.0},
            {"context": [1.0, 0, 0, 0, 0, 0, 1.0], "action": "DECLINE", "reward": 1.0},
        ]
        state = fit_offline(events)
        assert state.arms["DECLINE"].n == 2
        assert state.arms["DECLINE"].b[0] == 2.0
        assert "APPROVE" in state.arms  # lazily created at eval

    def test_ips_perfect_agreement(self):
        context = [1.0, 0, 0, 0, 0, 0, 1.0]
        events = [
            {"context": context, "action": "DECLINE", "propensity": 1.0, "reward": 1.0},
            {"context": context, "action": "DECLINE", "propensity": 1.0, "reward": 1.0},
        ]
        candidate = fit_offline(events)
        result = evaluate_off_policy(events, candidate)
        assert result["n_overlap"] == 2
        assert result["ips"] == 1.0

    def test_ips_no_overlap_zero(self):
        context = [1.0, 0, 0, 0, 0, 0, 1.0]
        events = [
            {"context": context, "action": "DECLINE", "propensity": 1.0, "reward": 1.0},
        ]
        current = BanditState()  # greedy on untrained arms never matches DECLINE
        result = evaluate_off_policy(events, current)
        assert result["n_overlap"] == 0
        assert result["ips"] == 0.0

    def test_promote_good_candidate(self):
        context = [1.0, 0, 0, 0, 0, 0, 1.0]
        events = [
            {"context": context, "action": "DECLINE", "propensity": 1.0, "reward": 1.0}
            for _ in range(4)
        ]
        candidate = fit_offline(events)
        current = BanditState()
        result = maybe_promote_bandit(candidate, current, events, min_improvement=0.0)
        assert result["promoted"] is True
        assert result["candidate_ips"] >= result["current_ips"]

    def test_promote_rejects_unproven_candidate(self):
        context = [1.0, 0, 0, 0, 0, 0, 1.0]
        events = [
            {"context": context, "action": "DECLINE", "propensity": 1.0, "reward": 1.0}
        ]
        losing = BanditState()  # no learned signal => cannot prove itself
        result = maybe_promote_bandit(losing, losing, events, min_improvement=0.0)
        assert result["promoted"] is False
