"""Integration tests for the FastAPI application via TestClient.

Everything is isolated to a temporary model dir and feedback file so the
tests never touch (or retrain on) the real bootstrap artefact in data/models.
"""

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
from fraud_detect.models import ModelBackend, select_feature_columns, train_model  # noqa: E402
from fraud_detect.policy import DEFAULT_POLICY  # noqa: E402


@pytest.fixture
def client(tmp_path, monkeypatch):
    df = _synthetic()
    feats = select_feature_columns(df)
    res = train_model(df, backend=ModelBackend.LIGHTGBM, num_boost_round=20)
    current = tmp_path / "models" / "current"
    serving.save_artefact(
        current,
        res.model,
        feats,
        serving.median_baseline(feats, df),
        {"roc_auc": res.val_auc, "version": "test-1", "trained_at": "2026-08-06T00:00:00"},
    )
    monkeypatch.setattr(store, "CURRENT_DIR", current)
    monkeypatch.setattr(store, "FEEDBACK_FILE", tmp_path / "feedback.jsonl")
    monkeypatch.setattr(store, "DECISION_DB", tmp_path / "decisions.db")
    monkeypatch.setattr(store, "data_table", _synthetic)
    monkeypatch.setattr(config, "LGBM_NUM_BOOST_ROUND", 20)
    monkeypatch.setattr(config, "LGBM_EARLY_STOPPING_ROUNDS", 5)
    main._clear_cache()
    return TestClient(main.app)


@pytest.fixture
def dclient(tmp_path, monkeypatch):
    """Decisioning fixture: a small model whose features satisfy the contract
    (TransactionAmt, card1, C1, D1) and whose target is strongly driven by x,
    so policy tests are deterministic.
    """
    rng = np.random.default_rng(11)
    n = 600
    # Bimodal, cleanly separable signal so policy mapping is deterministic.
    x = np.where(rng.random(n) < 0.5, -5.0, 5.0)
    df = pd.DataFrame(
        {
            "isFraud": (x > 0).astype(int),
            "TransactionAmt": rng.uniform(1, 500, n),
            "card1": rng.integers(1000, 9999, n),
            "C1": rng.integers(1, 50, n),
            "D1": rng.integers(0, 400, n),
            "x": x,
        }
    )
    feats = select_feature_columns(df)
    res = train_model(df, backend=ModelBackend.LIGHTGBM, num_boost_round=80)
    current = tmp_path / "models" / "current"
    serving.save_artefact(
        current,
        res.model,
        feats,
        serving.median_baseline(feats, df),
        {"roc_auc": res.val_auc, "version": "dtest", "trained_at": "2026-08-06T00:00:00"},
    )
    monkeypatch.setattr(store, "CURRENT_DIR", current)
    monkeypatch.setattr(store, "FEEDBACK_FILE", tmp_path / "feedback.jsonl")
    monkeypatch.setattr(store, "DECISION_DB", tmp_path / "decisions.db")
    monkeypatch.setattr(store, "data_table", lambda: df)
    monkeypatch.setattr(config, "LGBM_NUM_BOOST_ROUND", 80)
    monkeypatch.setattr(config, "LGBM_EARLY_STOPPING_ROUNDS", 5)
    main._clear_cache()
    return TestClient(main.app)


def _synthetic(n: int = 300) -> pd.DataFrame:
    rng = np.random.default_rng(3)
    return pd.DataFrame(
        {
            "isFraud": rng.integers(0, 2, n),
            "x": rng.standard_normal(n),
            "y": rng.standard_normal(n),
        }
    )


class TestMissingModel:
    def test_scoring_returns_503_without_path_leak(self, tmp_path, monkeypatch):
        monkeypatch.setattr(store, "CURRENT_DIR", tmp_path / "does-not-exist")
        main._clear_cache()
        c = TestClient(main.app)
        res = c.post("/api/predict", json={"values": {"x": 1.0}})
        assert res.status_code == 503
        detail = res.json()["detail"]
        assert "train_model" in detail
        assert "tmp_path" not in detail and "\\" not in detail  # no filesystem path

        health = c.get("/api/health").json()
        assert health["model_present"] is False


class TestReadEndpoints:
    def test_health(self, client):
        body = client.get("/api/health").json()
        assert body["model_present"] is True
        assert body["model_version"] == "test-1"

    def test_model(self, client):
        body = client.get("/api/model").json()
        assert body["version"] == "test-1"
        assert "roc_auc" in body

    def test_predict(self, client):
        res = client.post("/api/predict", json={"values": {"x": 2.0, "y": -2.0}})
        assert res.status_code == 200
        body = res.json()
        assert body["risk_tier"] in {"low", "medium", "high"}
        assert 0.0 <= body["probability"] <= 1.0

    def test_explain(self, client):
        res = client.post("/api/explain", json={"values": {"x": 2.0, "y": 2.0}})
        assert res.status_code == 200
        body = res.json()
        assert body["model_version"] == "test-1"
        assert len(body["features"]) > 0

    def test_batch(self, client):
        csv_bytes = "TransactionID,x,y\n1,1.0,-1.0\n2,-1.0,1.0\n3,0.5,0.5\n"
        res = client.post(
            "/api/predict/batch",
            files={"file": ("txs.csv", csv_bytes, "text/csv")},
        )
        assert res.status_code == 200
        body = res.json()
        assert body["count"] == 3
        assert all(0.0 <= r["probability"] <= 1.0 for r in body["rows"])

    def test_batch_rejects_bad_csv(self, client):
        res = client.post(
            "/api/predict/batch",
            files={"file": ("bad.csv", b"\xff\xfe\xfd\x00\x01 not utf-8", "text/csv")},
        )
        assert res.status_code == 400

    def test_stats(self, client):
        body = client.get("/api/stats").json()
        assert body["model"]["version"] == "test-1"


class TestSimulate:
    def test_sim_fields(self, client):
        body = client.get("/api/sim/fields").json()
        assert body["profiles"] == ["typical", "nonfraud", "fraud"]
        assert len(body["fields"]) >= 3

    def test_simulate_maps_friendly_inputs(self, client):
        res = client.post(
            "/api/simulate",
            json={"profile": "typical", "amount": 50.0, "card_brand": "visa"},
        )
        assert res.status_code == 200
        body = res.json()
        assert body["profile"] == "typical"
        assert body["mapped_values"]["TransactionAmt"] == 50.0
        assert body["mapped_values"]["card1"] == 6200.0  # visa issuer code
        assert body["risk_tier"] in {"low", "medium", "high"}


class TestWriteEndpoints:
    def test_feedback_records(self, client, tmp_path):
        res = client.post(
            "/api/feedback",
            json={"values": {"x": 1.0, "y": 1.0}, "verdict": "fraud"},
        )
        assert res.status_code == 200
        assert res.json()["pool_size"] == 1
        assert (tmp_path / "feedback.jsonl").exists()

    def test_retrain_runs_and_is_gated(self, client):
        res = client.post("/api/retrain")
        assert res.status_code == 200
        body = res.json()
        assert body["swapped"] in {True, False}
        assert "reason" in body

    def test_retrain_requires_admin_key_when_configured(self, client, monkeypatch):
        monkeypatch.setenv("FRAUD_API_ADMIN_KEY", "secret")
        from api import main as main_mod

        monkeypatch.setattr(main_mod, "_ADMIN_KEY", "secret")
        res = client.post("/api/retrain")  # no admin key → 403
        assert res.status_code == 403
        ok = client.post("/api/retrain", headers={"X-Admin-Key": "secret"})
        assert ok.status_code == 200


class TestDecisioning:
    def test_joblib_artefact_is_the_scoring_engine(self, dclient):
        values = {"TransactionAmt": 120.0, "card1": 5000, "C1": 5, "D1": 10, "x": 3.0}
        r = dclient.post("/api/predict", json={"values": values}).json()
        art = store.current_artefact()
        x = serving.align_features(pd.DataFrame([values]), art.features)
        expected = float(serving.predict_proba(art.model, x)[0])
        assert abs(r["probability"] - expected) < 1e-5

    def test_decision_persisted_and_idempotent(self, dclient):
        values = {"TransactionAmt": 120.0, "card1": 5000, "C1": 5, "D1": 10, "x": 3.0}
        r1 = dclient.post("/api/predict", json={"transaction_id": "tx-1", "values": values}).json()
        r2 = dclient.post("/api/predict", json={"transaction_id": "tx-1", "values": values}).json()
        assert r1["transaction_id"] == "tx-1"
        assert r1["probability"] == r2["probability"]
        queue = dclient.get("/api/review/queue").json()
        assert any(x["transaction_id"] == "tx-1" for x in queue)
        assert dclient.get("/api/review/tx-1").json()["status"] == "NEW"

    def test_policy_maps_high_score_to_decline_low_to_approve(self, dclient):
        high = dclient.post(
            "/api/predict",
            json={
                "values": {"TransactionAmt": 250.0, "card1": 5000, "C1": 25, "D1": 200, "x": 12.0}
            },
        ).json()
        low = dclient.post(
            "/api/predict",
            json={
                "values": {"TransactionAmt": 250.0, "card1": 5000, "C1": 25, "D1": 200, "x": -12.0}
            },
        ).json()
        # The model must separate on the signal feature.
        assert high["probability"] > low["probability"]
        # The decision is exactly the versioned policy's mapping of the score.
        assert high["decision"] == DEFAULT_POLICY.apply(high["probability"])[0].value
        assert low["decision"] == DEFAULT_POLICY.apply(low["probability"])[0].value
        assert high["policy_version"] == "v1"
        assert high["contract_version"] == "v1"

    def test_malformed_schema_rejected(self, dclient):
        unknown = dclient.post(
            "/api/predict",
            json={"values": {"TransactionAmt": 1, "card1": 1, "C1": 1, "D1": 0, "bogus": 1}},
        )
        assert unknown.status_code == 422
        missing = dclient.post("/api/predict", json={"values": {"x": 1.0}})
        assert missing.status_code == 422
        assert any("TransactionAmt" in m for m in missing.json()["detail"])

    def test_batch_matches_single(self, dclient):
        values = {"TransactionAmt": 200.0, "card1": 5000, "C1": 10, "D1": 50, "x": 1.0}
        single = dclient.post("/api/predict", json={"transaction_id": "1", "values": values}).json()
        csv_text = "TransactionID,TransactionAmt,card1,C1,D1,x\n1,200.0,5000,10,50,1.0\n"
        batch = dclient.post(
            "/api/predict/batch", files={"file": ("t.csv", csv_text, "text/csv")}
        ).json()
        row = batch["rows"][0]
        assert round(row["probability"], 6) == round(single["probability"], 6)
        assert row["decision"] == single["decision"]

    def test_feedback_reaches_review_record(self, dclient):
        r = dclient.post(
            "/api/predict",
            json={
                "transaction_id": "fb-1",
                "values": {"TransactionAmt": 120.0, "card1": 5000, "C1": 5, "D1": 10, "x": 3.0},
            },
        ).json()
        tx = r["transaction_id"]
        out = dclient.post(
            f"/api/review/{tx}/outcome", json={"verdict": "fraud", "note": "n"}
        ).json()
        assert out["status"] == "REVIEWED"
        assert out["reviewer_outcome"] == "fraud"
        detail = dclient.get(f"/api/review/{tx}").json()
        assert detail["status"] == "REVIEWED"
        assert store.feedback_pool_size() >= 1
