"""Unit tests for fraud_detect.policy — decision policy determinism."""

from __future__ import annotations

from fraud_detect.policy import DEFAULT_POLICY, Decision, policy_from_env


class TestDecisionPolicy:
    def test_approve_below_review(self):
        decision, action = DEFAULT_POLICY.apply(0.05)
        assert decision == Decision.APPROVE
        assert "Approve" in action

    def test_manual_review_in_middle(self):
        decision, _ = DEFAULT_POLICY.apply(0.30)
        assert decision == Decision.MANUAL_REVIEW

    def test_decline_above_threshold(self):
        decision, _ = DEFAULT_POLICY.apply(0.90)
        assert decision == Decision.DECLINE

    def test_boundary_decline(self):
        # at decline_above exactly -> DECLINE
        decision, _ = DEFAULT_POLICY.apply(DEFAULT_POLICY.decline_above)
        assert decision == Decision.DECLINE

    def test_custom_policy_from_env(self):
        policy = policy_from_env(review_above=0.4, decline_above=0.8)
        assert policy.version == DEFAULT_POLICY.version
        assert policy.apply(0.5)[0] == Decision.MANUAL_REVIEW  # 0.4<=0.5<0.8
        assert policy.apply(0.9)[0] == Decision.DECLINE

    def test_defaults_without_overrides(self):
        assert policy_from_env() == DEFAULT_POLICY

    def test_policy_dict_records_version_and_thresholds(self):
        d = DEFAULT_POLICY.as_dict()
        assert d["policy_version"] == "v1"
        assert d["review_above"] == 0.15
        assert d["decline_above"] == 0.5
