"""Tests for the API-side adaptive layer integration (api.store).

Fixture-injected test parameters are intentionally unused (they apply the
isolated-store monkeypatching), hence the module-level noqa.
"""

# ruff: noqa: ARG002 - fixture args are requested for their side effects

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from api import store  # noqa: E402
from fraud_detect.bandit_policy import BANDIT_VERSION, BanditState  # noqa: E402


@pytest.fixture
def isolated(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "DECISION_DB", tmp_path / "decisions.db")
    monkeypatch.setattr(store, "BANDIT_STATE_FILE", tmp_path / "bandit" / "bandit_v2.json")
    return tmp_path


def _record(transaction_id: str, decision: str = "DECLINE", score: float = 0.9) -> None:
    store.record_decision(
        transaction_id=transaction_id,
        model_version="test-model",
        contract_version="v1",
        score=score,
        decision=decision,
        action="Decline.",
        policy_version="v2-linucb",
        thresholds={"policy_version": "v2-linucb", "auto_action_above": 0.95},
        reason_codes=[],
        feature_report={"counts": {"supplied": 1, "defaulted": 0, "missing": 0, "rejected": 0}},
        input_features={"C1": 1.0},
    )


class TestBanditEvents:
    def test_record_and_summary(self, isolated):
        data = {
            "transaction_id": "abc",
            "policy_version": "v2-linucb",
            "action": "DECLINE",
            "score": 0.9,
            "propensity": 1.0,
            "explored": False,
            "auto_actioned": True,
            "audit_sampled": False,
            "context": [0.9, 0.1, 0, 0, 0, 0, 1.0],
        }
        store.record_bandit_event(**data)
        summary = store.bandit_summary()
        assert summary["n"] == 1
        assert summary["by_action"]["DECLINE"] == 1
        assert summary["auto_actioned"] == 1
        event = store.get_bandit_event("abc")
        assert event["context"] == [0.9, 0.1, 0, 0, 0, 0, 1.0]

    def test_event_idempotent(self, isolated):
        data = {
            "transaction_id": "abc",
            "policy_version": "v2-linucb",
            "action": "DECLINE",
            "score": 0.9,
            "propensity": 1.0,
            "explored": False,
            "auto_actioned": False,
            "audit_sampled": False,
            "context": [0.9] * 7,
        }
        store.record_bandit_event(**data)
        store.record_bandit_event(**data)
        assert store.bandit_summary()["n"] == 1


class TestRewardLoop:
    def test_update_outcome_fans_reward(self, isolated, monkeypatch):
        # update_outcome -> record_feedback aligns against the served artefact;
        # a fake with an empty feature list keeps the loop self-contained.
        monkeypatch.setattr(
            store, "current_artefact", lambda: SimpleNamespace(features=[])
        )
        data = {
            "transaction_id": "tx-1",
            "policy_version": "v2-linucb",
            "action": "DECLINE",
            "score": 0.9,
            "propensity": 1.0,
            "explored": False,
            "auto_actioned": False,
            "audit_sampled": False,
            "context": [0.9, 0.1, 0, 0, 0, 0, 1.0],
        }
        store.record_bandit_event(**data)
        _record("tx-1")
        updated = store.update_outcome("tx-1", "safe", None)
        assert updated["reviewer_outcome"] == "safe"
        event = store.get_bandit_event("tx-1")
        assert event["reward"] == -2.5  # overturned decline: large penalty
        state = store.load_bandit_state()
        assert state.arms["DECLINE"].n == 1

    def test_repeat_review_does_not_double_reward(self, isolated, monkeypatch):
        monkeypatch.setattr(
            store, "current_artefact", lambda: SimpleNamespace(features=[])
        )
        data = {
            "transaction_id": "tx-2",
            "policy_version": "v2-linucb",
            "action": "DECLINE",
            "score": 0.9,
            "propensity": 1.0,
            "explored": False,
            "auto_actioned": False,
            "audit_sampled": False,
            "context": [0.9, 0.1, 0, 0, 0, 0, 1.0],
        }
        store.record_bandit_event(**data)
        _record("tx-2")
        store.update_outcome("tx-2", "safe", None)
        store.update_outcome("tx-2", "safe", None)
        state = store.load_bandit_state()
        assert state.n_rewards == 1
        assert state.arms["DECLINE"].n == 1
        assert state.arms["DECLINE"].b == pytest.approx([-2.25, -0.25, 0, 0, 0, 0, -2.5])

    def test_changed_verdict_applies_delta(self, isolated, monkeypatch):
        monkeypatch.setattr(
            store, "current_artefact", lambda: SimpleNamespace(features=[])
        )
        data = {
            "transaction_id": "tx-3",
            "policy_version": "v2-linucb",
            "action": "DECLINE",
            "score": 0.9,
            "propensity": 1.0,
            "explored": False,
            "auto_actioned": False,
            "audit_sampled": False,
            "context": [0.9, 0.1, 0, 0, 0, 0, 1.0],
        }
        store.record_bandit_event(**data)
        _record("tx-3")
        store.update_outcome("tx-3", "safe", None)
        store.update_outcome("tx-3", "fraud", None)
        state = store.load_bandit_state()
        assert state.n_rewards == 1
        assert state.arms["DECLINE"].n == 1
        assert state.arms["DECLINE"].b == pytest.approx([0.9, 0.1, 0, 0, 0, 0, 1.0])
        event = store.get_bandit_event("tx-3")
        assert event["reward"] == 1.0

    def test_reward_writes_checkpoint(self, isolated):
        state = BanditState()
        state.arm("APPROVE").update([0.2] * 7, 0.5)
        store.save_bandit_state(state)
        loaded = store.load_bandit_state()
        assert loaded.arms["APPROVE"].n == 1


class TestPromotionGate:
    def _events(self):
        context = [1.0, 0, 0, 0, 0, 0, 1.0]
        return [
            {
                "transaction_id": f"e{i}",
                "policy_version": "v2-linucb",
                "action": "DECLINE",
                "score": 0.9,
                "propensity": 1.0,
                "explored": False,
                "auto_actioned": False,
                "audit_sampled": False,
                "context": context,
                "reward": 1.0,
            }
            for i in range(5)
        ]

    def test_promotes_good_candidate(self, isolated, monkeypatch):
        for event in self._events():
            store.record_bandit_event(**event)
        result = store.promote_bandit_state()
        assert result["promoted"] is True
        assert result["candidate_ips"] >= result["current_ips"]
        state = store.load_bandit_state()
        assert state.version == BANDIT_VERSION
        assert state.arms["DECLINE"].n == 5

    def test_archives_candidate_without_improvement(self, isolated, monkeypatch, tmp_path):
        for event in self._events():
            store.record_bandit_event(**event)
        archival_dir = tmp_path / "bandit"
        monkeypatch.setattr(store, "BANDIT_STATE_FILE", archival_dir / "bandit_v2.json")

        # The live policy already learned everything the candidate can learn;
        # requiring a meaningful improvement (min_improvement) must keep it.
        live = BanditState()
        for _ in range(10):
            live.arm("DECLINE").update([1.0, 0, 0, 0, 0, 0, 1.0], 1.0)
        store.save_bandit_state(live)

        result = store.promote_bandit_state(min_improvement=0.5)
        assert result["promoted"] is False
        assert result["candidate_ips"] < result["current_ips"] + 0.5
        assert list(archival_dir.glob("bandit_archive_*.json"))

    def test_promoted_state_keeps_reward_count(self, isolated, monkeypatch):
        for event in self._events():
            store.record_bandit_event(**event)
        result = store.promote_bandit_state()
        assert result["promoted"] is True
        state = store.load_bandit_state()
        # The cold-start gate (main._BANDIT_MIN_REWARDS) reads n_rewards; a
        # promotion must not reset it or the live bandit falls back to v1.
        assert state.n_rewards == 5

    def test_no_events_returns_reason(self, isolated):
        result = store.promote_bandit_state()
        assert result["promoted"] is False
        assert "no rewarded" in result["reason"].lower()


class TestAuditReports:
    def test_row_has_baseline_fields(self, isolated):
        data = {
            "transaction_id": "rep-1",
            "policy_version": "v2-linucb",
            "action": "DECLINE",
            "score": 0.9,
            "propensity": 1.0,
            "explored": False,
            "auto_actioned": False,
            "audit_sampled": False,
            "context": [0.9] * 7,
        }
        store.record_bandit_event(**data)
        _record("rep-1")
        report = store.generate_audit_report("rep-1")
        assert report is not None
        assert report["report_id"] == "report-rep-1"
        assert report["transaction_id"] == "rep-1"
        assert report["ai_disclaimer"] == "Generated by AI — subject to human review."
        assert report["executive_summary"]
        assert report["drivers"] == []
        stored = store.get_audit_report("rep-1")
        assert stored == report

    def test_missing_report_returns_none(self, isolated):
        assert store.get_audit_report("never") is None

    def test_no_report_for_approve(self, isolated):
        _record("app-1", decision="APPROVE", score=0.05)
        assert store.generate_audit_report("app-1") is None
