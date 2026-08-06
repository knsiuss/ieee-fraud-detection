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

from fraud_detect import config, serving  # noqa: E402
from fraud_detect.models import ModelBackend, select_feature_columns, train_model  # noqa: E402

from api import main, store  # noqa: E402


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
    monkeypatch.setattr(store, "data_table", lambda: _synthetic())
    monkeypatch.setattr(config, "LGBM_NUM_BOOST_ROUND", 20)
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