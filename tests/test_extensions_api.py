"""API tests for the extension features: bandit status/promote, audit reports, appeal."""

# ruff: noqa: ARG002 - fixture args are requested for their side effects

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from api import main, store  # noqa: E402
from fraud_detect import config, serving  # noqa: E402
from fraud_detect.bandit_policy import BANDIT_VERSION, BanditState  # noqa: E402
from fraud_detect.models import ModelBackend, select_feature_columns, train_model  # noqa: E402
from fraud_detect.policy import DEFAULT_POLICY  # noqa: E402


def _synthetic() -> pd.DataFrame:
    rng = np.random.default_rng(11)
    n = 300
    x = np.where(rng.random(n) < 0.5, -5.0, 5.0)
    return pd.DataFrame(
        {
            "isFraud": (x > 0).astype(int),
            "TransactionAmt": rng.uniform(1, 500, n),
            "card1": rng.integers(1000, 9999, n),
            "C1": rng.integers(1, 50, n),
            "D1": rng.integers(0, 400, n),
            "x": x,
        }
    )


@pytest.fixture
def bandit_client(tmp_path, monkeypatch):
    """A served model + bandit enabled (cold-start gate bypassed), isolated."""
    df = _synthetic()
    feats = select_feature_columns(df)
    res = train_model(df, backend=ModelBackend.LIGHTGBM, num_boost_round=40)
    current = tmp_path / "models" / "current"
    serving.save_artefact(
        current,
        res.model,
        feats,
        serving.median_baseline(feats, df),
        {"roc_auc": res.val_auc, "version": "ext-test", "trained_at": "2026-08-06T00:00:00"},
    )
    monkeypatch.setattr(store, "CURRENT_DIR", current)
    monkeypatch.setattr(store, "FEEDBACK_FILE", tmp_path / "feedback.jsonl")
    monkeypatch.setattr(store, "DECISION_DB", tmp_path / "decisions.db")
    monkeypatch.setattr(store, "BANDIT_STATE_FILE", tmp_path / "bandit" / "bandit_v2.json")
    monkeypatch.setattr(store, "data_table", _synthetic)
    monkeypatch.setattr(config, "LGBM_NUM_BOOST_ROUND", 40)
    monkeypatch.setattr(config, "LGBM_EARLY_STOPPING_ROUNDS", 10)
    monkeypatch.setattr(main, "_BANDIT_ENABLED", True)
    monkeypatch.setattr(main, "_BANDIT_MIN_REWARDS", 0)
    monkeypatch.setattr(main, "_BANDIT_STATE", BanditState())
    main._clear_cache()
    return TestClient(main.app)


def _payload(tx: str) -> dict:
    return {
        "transaction_id": tx,
        "values": {"TransactionAmt": 900.0, "card1": 9000.0, "C1": 45.0, "D1": 380.0, "x": 5.0},
    }


def _record_decline(tx: str, score: float = 0.91) -> None:
    """Persist a DECLINE decision row directly (report/appeal tests use the
    stored decision, so they don't depend on the demo model's score)."""
    store.record_decision(
        transaction_id=tx,
        model_version="ext-test",
        contract_version="v1",
        score=score,
        decision="DECLINE",
        action="Decline.",
        policy_version="v1",
        thresholds=DEFAULT_POLICY.as_dict(),
        reason_codes=[],
        feature_report={"counts": {"supplied": 1, "defaulted": 0, "missing": 0, "rejected": 0}},
        input_features={"x": 5.0},
    )


class TestBanditStatus:
    def test_status_reports_enabled_policy(self, bandit_client):
        resp = bandit_client.get("/api/bandit/status")
        assert resp.status_code == 200
        body = resp.json()
        assert body["enabled"] is True
        assert body["policy"]["policy_version"] == BANDIT_VERSION
        assert body["summary"]["n"] == 0

    def test_scoring_records_bandit_event(self, bandit_client):
        resp = bandit_client.post("/api/predict", json=_payload("ext-1"))
        assert resp.status_code == 200
        body = resp.json()
        assert body["policy_version"] == BANDIT_VERSION
        event = store.get_bandit_event("ext-1")
        assert event is not None
        assert event["policy_version"] == BANDIT_VERSION
        assert event["propensity"] > 0
        assert store.bandit_summary()["n"] == 1

    def test_cold_start_defers_to_v1(self, bandit_client, monkeypatch):
        # A fresh checkpoint that has not accumulated enough rewards must not
        # take over decisioning (empty arms tie and would approve everything).
        monkeypatch.setattr(main, "_BANDIT_MIN_REWARDS", 5)
        resp = bandit_client.post("/api/predict", json=_payload("cold-1"))
        assert resp.status_code == 200
        assert resp.json()["policy_version"] == DEFAULT_POLICY.version
        assert store.get_bandit_event("cold-1") is None


class TestBanditPromote:
    def test_promote_requires_configured_admin(self, bandit_client):
        monkeypatch = pytest.MonkeyPatch()
        monkeypatch.setattr(main, "_ADMIN_KEY", None)
        resp = bandit_client.post("/api/bandit/promote")
        assert resp.status_code == 503  # endpoint disabled without admin key
        monkeypatch.undo()

    def test_promote_requires_valid_key(self, bandit_client):
        monkeypatch = pytest.MonkeyPatch()
        monkeypatch.setattr(main, "_ADMIN_KEY", "sekret")
        resp = bandit_client.post("/api/bandit/promote", headers={"X-Admin-Key": "wrong"})
        assert resp.status_code == 403
        monkeypatch.undo()

    def test_promote_without_rewards_reports_reason(self, bandit_client):
        monkeypatch = pytest.MonkeyPatch()
        monkeypatch.setattr(main, "_ADMIN_KEY", "sekret")
        resp = bandit_client.post("/api/bandit/promote", headers={"X-Admin-Key": "sekret"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["promoted"] is False
        assert "No rewarded bandit events" in body["reason"]
        monkeypatch.undo()

    def test_promote_after_rewards(self, bandit_client):
        monkeypatch = pytest.MonkeyPatch()
        monkeypatch.setattr(main, "_ADMIN_KEY", "sekret")
        for i in range(5):
            store.record_bandit_event(
                transaction_id=f"prom-{i}",
                policy_version=BANDIT_VERSION,
                action="DECLINE",
                score=0.9,
                propensity=1.0,
                explored=False,
                auto_actioned=False,
                audit_sampled=False,
                context=[1.0, 0, 0, 0, 0, 0, 1.0],
                reward=1.0,
            )
        resp = bandit_client.post("/api/bandit/promote", headers={"X-Admin-Key": "sekret"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["n_logged"] == 5
        assert body["candidate_ips"] >= body["current_ips"]
        monkeypatch.undo()


class TestAuditReportEndpoint:
    def test_report_fetched_after_generation(self, bandit_client):
        _record_decline("rep-1")
        store.generate_audit_report("rep-1")
        resp = bandit_client.get("/api/review/rep-1/report")
        assert resp.status_code == 200
        body = resp.json()
        assert body["report_id"] == "report-rep-1"
        assert body["transaction_id"] == "rep-1"
        assert body["ai_disclaimer"] == "Generated by AI — subject to human review."
        assert body["decision"] == "DECLINE"
        assert "executive_summary" in body
        assert body["risk_score"]["probability"] == 0.91

    def test_report_for_approve_not_generated(self, bandit_client):
        store.record_decision(
            transaction_id="rep-ok",
            model_version="ext-test",
            contract_version="v1",
            score=0.05,
            decision="APPROVE",
            action="Approve.",
            policy_version="v1",
            thresholds=DEFAULT_POLICY.as_dict(),
            reason_codes=[],
            feature_report={},
            input_features={},
        )
        assert store.generate_audit_report("rep-ok") is None

    def test_report_missing_returns_404(self, bandit_client):
        resp = bandit_client.get("/api/review/never/report")
        assert resp.status_code == 404

    def test_report_regenerates_and_overwrites(self, bandit_client):
        _record_decline("rep-2")
        store.generate_audit_report("rep-2")
        store.generate_audit_report("rep-2")
        resp = bandit_client.get("/api/review/rep-2/report")
        assert resp.status_code == 200


class TestAppealEndpoint:
    def test_appeal_overturns_decline(self, bandit_client):
        _record_decline("app-1")
        resp = bandit_client.post("/api/review/app-1/appeal", json={"note": "customer called in"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["reviewer_outcome"] == "safe"
        assert body["status"] == "REVIEWED"
        record = store.get_decision("app-1")
        assert record["reviewer_outcome"] == "safe"

    def test_appeal_no_body_uses_default_note(self, bandit_client):
        _record_decline("app-1b")
        resp = bandit_client.post("/api/review/app-1b/appeal")
        assert resp.status_code == 200
        assert resp.json()["reviewer_outcome"] == "safe"

    def test_appeal_missing_decision_404(self, bandit_client):
        resp = bandit_client.post("/api/review/never/appeal", json={})
        assert resp.status_code == 404

    def test_appeal_confirmed_fraud_422(self, bandit_client):
        _record_decline("app-2")
        store.update_outcome("app-2", "fraud", "reviewed")
        resp = bandit_client.post("/api/review/app-2/appeal", json={})
        assert resp.status_code == 422

    def test_appeal_fans_reward_into_checkpoint(self, bandit_client):
        store.record_bandit_event(
            transaction_id="app-3",
            policy_version=BANDIT_VERSION,
            action="DECLINE",
            score=0.91,
            propensity=1.0,
            explored=False,
            auto_actioned=False,
            audit_sampled=False,
            context=[0.91, 0.1, 0, 0, 0, 0, 1.0],
        )
        _record_decline("app-3")
        resp = bandit_client.post("/api/review/app-3/appeal", json={"note": "oops"})
        assert resp.status_code == 200
        event = store.get_bandit_event("app-3")
        assert event["reward"] == -2.5  # overturned decline: large penalty
        state = store.load_bandit_state()
        assert state.arms["DECLINE"].n == 1


class TestBanditDecisionThresholds:
    def test_bandit_decision_carries_v1_thresholds(self, bandit_client, monkeypatch):
        # Bandit decisions store no review/decline thresholds of their own,
        # but audit reports read them from the stored decision. If they end up
        # missing, reports (and the LLM prompt) fall back to fabricated
        # 0.15/0.50 defaults that disagree with the deployed config.
        from fraud_detect.policy import DecisionPolicy

        monkeypatch.setattr(
            main,
            "_POLICY",
            DecisionPolicy(version="v1-test", review_above=0.2, decline_above=0.7),
        )
        resp = bandit_client.post("/api/predict", json=_payload("thr-1"))
        assert resp.status_code == 200
        record = store.get_decision("thr-1")
        assert record["thresholds"]["review_above"] == 0.2
        assert record["thresholds"]["decline_above"] == 0.7
        from fraud_detect.audit_report import build_report_context

        context = build_report_context({**record, "risk_tier": "high", "summary": "s"})
        assert context["review_above"] == 0.2
        assert context["decline_above"] == 0.7
