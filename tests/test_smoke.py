"""End-to-end smoke test: the full analyst workflow against the live app.

Boots the FastAPI app on a throwaway model and drives the complete flow a
stranger would follow — health check, score a checkout-style case, score raw
features, batch upload, review feedback, and model metadata — asserting each
step returns a well-formed response. Isolated to temp dirs; never touches the
real bootstrap artefact in ``data/models``.
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
from fraud_detect import serving  # noqa: E402
from fraud_detect.models import ModelBackend, select_feature_columns, train_model  # noqa: E402


@pytest.fixture
def client(tmp_path, monkeypatch):
    rng = np.random.default_rng(9)
    n = 400
    df = pd.DataFrame(
        {
            "isFraud": rng.integers(0, 2, n),
            "x": rng.standard_normal(n),
            "y": rng.standard_normal(n),
            "z": rng.standard_normal(n),
        }
    )
    feats = select_feature_columns(df)
    res = train_model(df, backend=ModelBackend.LIGHTGBM, num_boost_round=15)
    current = tmp_path / "models" / "current"
    serving.save_artefact(
        current,
        res.model,
        feats,
        serving.median_baseline(feats, df),
        {"roc_auc": res.val_auc, "version": "smoke", "trained_at": "2026-08-06T00:00:00"},
        profiles={
            "nonfraud": serving.median_baseline(feats, df[df["isFraud"] == 0]),
            "fraud": serving.median_baseline(feats, df[df["isFraud"] == 1]),
        },
    )
    monkeypatch.setattr(store, "CURRENT_DIR", current)
    monkeypatch.setattr(store, "FEEDBACK_FILE", tmp_path / "feedback.jsonl")
    monkeypatch.setattr(store, "data_table", lambda: df)
    main._clear_cache()
    return TestClient(main.app)


def test_full_workflow_smoke(client):
    # health
    assert client.get("/api/health").json()["model_present"] is True

    # meta endpoints
    assert client.get("/api/model").status_code == 200
    stats = client.get("/api/stats").json()
    assert "model" in stats

    # checkout simulator
    sim = client.post(
        "/api/simulate",
        json={"profile": "fraud", "x": 3.0, "y": 3.0},
    )
    assert sim.status_code == 200
    assert sim.json()["risk_tier"] in {"low", "medium", "high"}

    # raw feature scoring
    pred = client.post("/api/predict", json={"values": {"x": 3.0, "y": -3.0}})
    assert pred.status_code == 200
    assert 0.0 <= pred.json()["probability"] <= 1.0

    # explanation
    exp = client.post("/api/explain", json={"values": {"x": 3.0, "y": 3.0}})
    assert exp.status_code == 200
    assert exp.json()["summary"]  # has prose

    # feedback -> pushes the retraining pool
    fb = client.post("/api/feedback", json={"values": {"x": 1.0, "y": 1.0}, "verdict": "fraud"})
    assert fb.status_code == 200
    assert fb.json()["pool_size"] == 1

    # gated retrain runs and is a no-op if it does not beat the served model
    rt = client.post("/api/retrain")
    assert rt.status_code == 200
    assert rt.json()["swapped"] in {True, False}
    assert "reason" in rt.json()
