"""Integration tests for the FastAPI application via TestClient.

Everything is isolated to a temporary model dir and feedback file so the
tests never touch (or retrain on) the real bootstrap artefact in data/models.
"""

from __future__ import annotations

import asyncio
import json
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
from fraud_detect.policy import DEFAULT_POLICY, DecisionPolicy  # noqa: E402


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

    def test_batch_preserves_ids_and_isolates_missing(self, client):
        """Transaction IDs must round-trip exactly (no '.0' mangling) and
        missing IDs get a unique per-row fallback instead of collapsing onto
        a single 'nan' record in the idempotent store.
        """
        csv_text = (
            "TransactionID,x,y\n"
            "3152017,1.0,-1.0\n"  # integer id stays exact
            ",2.0,-2.0\n"  # missing id -> unique fallback
            ",3.0,-3.0\n"  # another missing id -> another fallback
            "abc-1,0.5,0.5\n"  # string id preserved verbatim
        )
        res = client.post(
            "/api/predict/batch",
            files={"file": ("txs.csv", csv_text, "text/csv")},
        )
        assert res.status_code == 200
        body = res.json()
        assert [r["transaction_id"] for r in body["rows"]] == [
            "3152017",
            "row-1",
            "row-2",
            "abc-1",
        ]
        # Mixed-type column (int/NaN/str) reads as object dtype, so the raw id
        # arrives as '3152017' (str) — either way it must round-trip exactly,
        # never '3152017.0'.
        assert str(body["rows"][0]["id"]) == "3152017"
        assert body["rows"][3]["id"] == "abc-1"
        # Every row got its own decision record — none collapsed onto one.
        queue = client.get("/api/review/queue").json()
        assert len(queue) == 4

    def test_stats(self, client):
        body = client.get("/api/stats").json()
        assert body["model"]["version"] == "test-1"

    def test_metrics_summary(self, client):
        res = client.get("/api/metrics/summary")
        assert res.status_code == 200
        body = res.json()
        assert "total_decisions" in body
        assert "counts" in body
        assert "percentages" in body
        assert "tps" in body
        assert "latency" in body

    def test_metrics_timeseries(self, client):
        res = client.get("/api/metrics/timeseries?w=30&bucket=60")
        assert res.status_code == 200
        body = res.json()
        assert isinstance(body, list)
        assert len(body) > 0
        assert "timestamp" in body[0]
        assert "total" in body[0]

    def test_metrics_dispositions(self, client):
        res = client.get("/api/metrics/dispositions")
        assert res.status_code == 200
        body = res.json()
        assert "total_decisions" in body
        assert "confirmed_fraud" in body
        assert "disposition_mix" in body

    def test_metrics_loss(self, client):
        res = client.get("/api/metrics/loss")
        assert res.status_code == 200
        body = res.json()
        assert "total_gmv" in body
        assert "loss_prevented" in body
        assert "chargeback_bps" in body


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
        payload = {"values": {"x": 1.0, "y": 1.0}, "verdict": "fraud"}
        res = client.post("/api/feedback", json=payload)
        assert res.status_code == 200
        assert res.json()["pool_size"] == 1
        assert (tmp_path / "feedback.jsonl").exists()

    def test_retrain_disabled_when_admin_key_not_configured(self, client, monkeypatch):
        monkeypatch.setattr(main, "_ADMIN_KEY", None)
        res = client.post("/api/retrain")
        assert res.status_code == 503
        assert "FRAUD_API_ADMIN_KEY" in res.json()["detail"]

    def test_retrain_runs_and_is_gated(self, client, monkeypatch):
        monkeypatch.setattr(main, "_ADMIN_KEY", "secret")
        # Missing key header -> 403
        res = client.post("/api/retrain")
        assert res.status_code == 403
        # Wrong key header -> 403
        res_wrong = client.post("/api/retrain", headers={"X-Admin-Key": "wrong"})
        assert res_wrong.status_code == 403
        # Correct key header -> 200
        ok = client.post("/api/retrain", headers={"X-Admin-Key": "secret"})
        assert ok.status_code == 200
        body = ok.json()
        assert body["swapped"] in {True, False}
        assert "reason" in body


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


class TestSseStream:
    """SSE live stream contract (GET /api/decisions/stream).

    The server replays the current queue to every new connection, so the
    client (deduplicated in the React frontend by web/src/stores/useLiveStore.ts)
    must de-duplicate by transaction_id. These tests pin the server side of that
    contract: framing, no sensitive-feature leakage, per-connection de-dupe, and
    the replay-across-connections semantics.
    """

    VALUES = {"TransactionAmt": 120.0, "card1": 5000, "C1": 5, "D1": 10, "x": 3.0}

    def _seed(self, dclient) -> None:
        for tx in ("sse-1", "sse-2"):
            dclient.post("/api/predict", json={"transaction_id": tx, "values": self.VALUES})

    @staticmethod
    def _parse(frames: list[str]) -> list[dict]:
        records = []
        for frame in frames:
            lines = frame.splitlines()
            assert any(line.startswith("id: ") for line in lines), frame
            assert [line for line in lines if line.startswith("event: ")] == ["event: decision"]
            data_lines = [line for line in lines if line.startswith("data: ")]
            assert len(data_lines) == 1
            records.append(json.loads(data_lines[0][len("data: ") :]))
        return records

    def test_frames_emit_decisions_without_input_features(self, dclient):
        self._seed(dclient)
        seen: set[str] = set()
        records = self._parse(list(main._sse_frames(store.list_decisions(limit=200), seen)))
        ids = {r["transaction_id"] for r in records}
        assert {"sse-1", "sse-2"} <= ids
        # Sensitive raw features must never appear on the wire.
        assert all("input_features" not in r for r in records)
        assert all("score" in r and "decision" in r for r in records)

    def test_a_transaction_is_emitted_once_per_connection(self, dclient):
        self._seed(dclient)
        seen: set[str] = set()
        first = list(main._sse_frames(store.list_decisions(limit=200), seen))
        again = list(main._sse_frames(store.list_decisions(limit=200), seen))
        assert len(first) == 2
        assert again == []  # same connection re-polling must not re-emit

    def test_stream_replays_queue_to_each_new_connection(self, dclient):
        self._seed(dclient)
        first = self._parse(list(main._sse_frames(store.list_decisions(limit=200), set())))
        second = self._parse(list(main._sse_frames(store.list_decisions(limit=200), set())))
        assert first and second
        # Every new connection replays the current queue; the client dedupes.
        assert {r["transaction_id"] for r in first} == {r["transaction_id"] for r in second}

    def test_stream_response_has_sse_headers(self):
        response = asyncio.run(main.decisions_stream())
        assert response.media_type == "text/event-stream"
        assert response.headers["cache-control"] == "no-cache"
        assert response.headers["x-accel-buffering"] == "no"

    def test_nan_inputs_never_emit_bare_nan_tokens(self, dclient):
        """An optional field with an empty cell yields NaN/None in the audit fields; the
        review record and SSE frames must still be strict JSON (no bare NaN
        or Infinity tokens) so browser-side EventSource consumers never choke.
        """
        csv_text = (
            "TransactionID,TransactionAmt,card1,C1,D1,x\n"
            "9001,200.0,5000,10,50,\n"  # empty optional field x
        )
        res = dclient.post(
            "/api/predict/batch",
            files={"file": ("t.csv", csv_text, "text/csv")},
        )
        assert res.status_code == 200
        tx = res.json()["rows"][0]["transaction_id"]

        record = dclient.get(f"/api/review/{tx}").json()
        assert "input_features" not in record  # public view omits raw features

        frames = list(main._sse_frames(store.list_decisions(limit=200), set()))
        assert any(tx in f for f in frames)
        for frame in frames:
            assert "NaN" not in frame and "Infinity" not in frame
            data = frame.split("data: ", 1)[1].split("\n\n", 1)[0]
            json.loads(data)  # must parse as strict JSON

    def test_required_field_blank_or_nan_rejected_in_batch(self, dclient):
        csv_text = (
            "TransactionID,TransactionAmt,card1,C1,D1,x\n"
            "9002,200.0,5000,,50,1.0\n"  # empty required C1
        )
        res = dclient.post(
            "/api/predict/batch",
            files={"file": ("t.csv", csv_text, "text/csv")},
        )
        assert res.status_code == 200
        body = res.json()
        assert len(body["errors"]) == 1
        assert "C1" in body["errors"][0]["errors"]

    def test_required_field_nan_or_inf_rejected_in_predict(self, dclient):
        # Raw payload with NaN
        nan_res = dclient.post(
            "/api/predict",
            content='{"values": {"TransactionAmt": NaN, "card1": 5000, "C1": 10, "D1": 50}}',
            headers={"Content-Type": "application/json"},
        )
        assert nan_res.status_code in (400, 422)

        # Raw payload with Infinity
        inf_res = dclient.post(
            "/api/predict",
            content='{"values": {"TransactionAmt": Infinity, "card1": 5000, "C1": 10, "D1": 50}}',
            headers={"Content-Type": "application/json"},
        )
        assert inf_res.status_code in (400, 422)

        # Direct contract validation with non-finite values
        with pytest.raises(main.ContractError) as exc_info:
            main.validate_payload(
                {"TransactionAmt": float("nan"), "card1": 5000, "C1": 10, "D1": 50},
                ["TransactionAmt", "card1", "C1", "D1"],
            )
        assert any("TransactionAmt" in m for m in exc_info.value.messages)

    def test_idempotent_consistency_with_different_payload(self, dclient):
        low_vals = {"TransactionAmt": 50.0, "card1": 5000, "C1": 1, "D1": 1, "x": -5.0}
        high_vals = {"TransactionAmt": 500.0, "card1": 5000, "C1": 50, "D1": 300, "x": 5.0}

        r1 = dclient.post(
            "/api/predict", json={"transaction_id": "tx-idemp-1", "values": low_vals}
        ).json()
        assert "probability" in r1 and "decision" in r1 and "action" in r1

        # Resend with same transaction_id but very high risk payload
        r2 = dclient.post(
            "/api/predict", json={"transaction_id": "tx-idemp-1", "values": high_vals}
        ).json()
        # Must return the original decision and consistent action
        assert r2["probability"] == r1["probability"]
        assert r2["decision"] == r1["decision"]
        assert r2["action"] == r1["action"]
        assert r2["risk_tier"] == r1["risk_tier"]

    def test_idempotent_replay_keeps_original_action_after_policy_change(
        self, dclient, monkeypatch
    ):
        values = {"TransactionAmt": 50.0, "card1": 5000, "C1": 1, "D1": 1, "x": 5.0}
        first = dclient.post(
            "/api/predict", json={"transaction_id": "tx-policy-1", "values": values}
        ).json()
        monkeypatch.setattr(
            main,
            "_POLICY",
            DecisionPolicy(version="v2", review_above=0.99, decline_above=0.999),
        )
        replay = dclient.post(
            "/api/predict", json={"transaction_id": "tx-policy-1", "values": values}
        ).json()
        assert replay["decision"] == first["decision"]
        assert replay["action"] == first["action"]

    def test_batch_rejects_invalid_transaction_id(self, dclient):
        csv_text = "TransactionID,TransactionAmt,card1,C1,D1,x\n<script>,200,5000,10,50,1\n"
        body = dclient.post(
            "/api/predict/batch", files={"file": ("t.csv", csv_text, "text/csv")}
        ).json()
        assert body["count"] == 0
        assert len(body["errors"]) == 1
        assert "Invalid transaction_id" in body["errors"][0]["errors"]

    def test_review_outcome_requires_admin_key(self, dclient, monkeypatch):
        monkeypatch.setattr(main, "_ADMIN_KEY", "secret-key")
        values = {"TransactionAmt": 120.0, "card1": 5000, "C1": 5, "D1": 10, "x": 3.0}
        dclient.post("/api/predict", json={"transaction_id": "tx-outcome-1", "values": values})
        assert (
            dclient.post("/api/review/tx-outcome-1/outcome", json={"verdict": "fraud"}).status_code
            == 403
        )
        assert (
            dclient.post(
                "/api/review/tx-outcome-1/outcome",
                json={"verdict": "fraud"},
                headers={"X-Admin-Key": "secret-key"},
            ).status_code
            == 200
        )

    def test_review_privacy_and_admin_key(self, dclient, monkeypatch):
        monkeypatch.setattr(main, "_ADMIN_KEY", "secret-key")
        values = {"TransactionAmt": 120.0, "card1": 5000, "C1": 5, "D1": 10, "x": 3.0}
        dclient.post("/api/predict", json={"transaction_id": "tx-priv-1", "values": values})

        # Queue list must not contain input_features
        queue = dclient.get("/api/review/queue").json()
        priv_tx = next(item for item in queue if item["transaction_id"] == "tx-priv-1")
        assert "input_features" not in priv_tx

        # Detail without admin key must omit input_features
        detail_pub = dclient.get("/api/review/tx-priv-1").json()
        assert "input_features" not in detail_pub

        # Detail with valid admin key includes input_features
        detail_admin = dclient.get(
            "/api/review/tx-priv-1", headers={"X-Admin-Key": "secret-key"}
        ).json()
        assert "input_features" in detail_admin

    def test_review_queue_limit_validation(self, dclient):
        assert dclient.get("/api/review/queue?limit=-1").status_code == 422
        assert dclient.get("/api/review/queue?limit=0").status_code == 422
        assert dclient.get("/api/review/queue?limit=500").status_code == 422
        assert dclient.get("/api/review/queue?limit=50").status_code == 200

    def test_transaction_id_validation(self, dclient):
        bad_xss = dclient.post(
            "/api/predict",
            json={
                "transaction_id": "<script>alert(1)</script>",
                "values": {"TransactionAmt": 100, "card1": 1000, "C1": 1, "D1": 0},
            },
        )
        assert bad_xss.status_code == 422
        bad_detail = dclient.get("/api/review/<img src=x>")
        assert bad_detail.status_code == 422
