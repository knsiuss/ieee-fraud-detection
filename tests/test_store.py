"""Tests for api/store.py — feedback pool and gated retrain."""

from __future__ import annotations

import json
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from api import store  # noqa: E402
from fraud_detect import config, serving  # noqa: E402
from fraud_detect.models import ModelBackend, select_feature_columns, train_model  # noqa: E402


def _build_df(seed: int = 0, n: int = 600) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    x1 = rng.standard_normal(n)
    return pd.DataFrame(
        {
            "x1": x1,
            "x2": rng.standard_normal(n),
            "noise": rng.standard_normal(n),
            "isFraud": (x1 > 0).astype(int),
        }
    )


@pytest.fixture
def _isolated(tmp_path, monkeypatch):
    """Point the store at a throwaway location and seed a served model."""
    current = tmp_path / "models" / "current"
    df = _build_df()
    feats = select_feature_columns(df)
    res = train_model(df, backend=ModelBackend.LIGHTGBM, num_boost_round=20)
    serving.save_artefact(
        current,
        res.model,
        feats,
        serving.median_baseline(feats, df),
        {"roc_auc": res.val_auc, "version": "test-current", "trained_at": "2026-08-06T00:00:00"},
    )
    monkeypatch.setattr(store, "CURRENT_DIR", current)
    monkeypatch.setattr(store, "CANDIDATES_DIR", tmp_path / "models" / "candidates")
    monkeypatch.setattr(store, "FEEDBACK_FILE", tmp_path / "feedback.jsonl")
    monkeypatch.setattr(store, "DECISION_DB", tmp_path / "decisions.db")
    monkeypatch.setattr(config, "LGBM_NUM_BOOST_ROUND", 20)
    monkeypatch.setattr(config, "LGBM_EARLY_STOPPING_ROUNDS", 5)
    return tmp_path


class TestJsonSafe:
    """Non-finite floats (NaN/inf) must never survive into JSON output."""

    def test_scalar_non_finite_becomes_none(self):
        assert store.json_safe(float("nan")) is None
        assert store.json_safe(float("inf")) is None
        assert store.json_safe(float("-inf")) is None

    def test_recursive_dict_and_list(self):
        assert store.json_safe({"a": float("nan"), "b": [1.5, float("nan")]}) == {
            "a": None,
            "b": [1.5, None],
        }

    def test_finite_values_pass_through(self):
        assert store.json_safe({"ok": 1.5, "s": "x", "n": 3}) == {"ok": 1.5, "s": "x", "n": 3}
        assert store.json_safe("plain") == "plain"


class TestFeedbackPool:
    def test_record_and_read(self, _isolated):
        art = store.current_artefact()
        values = {f: 0.5 for f in art.features[:3]}
        size = store.record_feedback(values, 1, transaction_id="tx-fb-1")
        assert size == 1
        assert store.feedback_pool_size() == 1

        pool = store.feedback_pool_df()
        assert "isFraud" in pool.columns
        assert len(pool) == 1
        assert int(pool.iloc[0]["isFraud"]) == 1

    def test_feedback_deduplication(self, _isolated):
        art = store.current_artefact()
        values = {f: 0.5 for f in art.features[:3]}
        # First verdict: fraud
        store.record_feedback(values, 1, transaction_id="tx-dup-1")
        assert store.feedback_pool_size() == 1
        # Second verdict on same transaction: safe
        store.record_feedback(values, 0, transaction_id="tx-dup-1")
        # Pool size must remain 1 and updated to safe
        assert store.feedback_pool_size() == 1
        pool = store.feedback_pool_df()
        assert len(pool) == 1
        assert int(pool.iloc[0]["isFraud"]) == 0

    def test_empty_pool(self, _isolated):
        assert store.feedback_pool_df().empty
        assert store.feedback_pool_size() == 0


class TestRetrainGate:
    def test_returns_summary(self, _isolated):
        result = store.retrain_and_swap(data_df=_build_df(seed=1))
        assert set(result) >= {"swapped", "old_auc", "new_auc", "reason"}
        assert isinstance(result["swapped"], bool)
        assert result["feedback_rows"] == 0

    def test_strong_feedback_candidate_swaps(self, _isolated):
        df = _build_df(seed=1)
        # Serve a deliberately weak model (trained on a tiny slice) so the
        # feedback-driven candidate reliably clears the gate.
        weak = df.head(80)
        feats_w = select_feature_columns(weak)
        res_w = train_model(weak, backend=ModelBackend.LIGHTGBM, num_boost_round=8)
        serving.save_artefact(
            store.CURRENT_DIR,
            res_w.model,
            feats_w,
            serving.median_baseline(feats_w, weak),
            {"version": "weak"},
        )
        # Perfectly separable feedback rows: x1 < 0 → safe, x1 > 0 → fraud.
        fb = pd.DataFrame(
            {
                "x1": np.concatenate([np.full(150, -4.0), np.full(150, 4.0)]),
                "x2": 0.0,
                "noise": 0.0,
                "isFraud": [0] * 150 + [1] * 150,
            }
        )
        with store.FEEDBACK_FILE.open("a", encoding="utf-8") as fh:
            for _, row in fb.iterrows():
                payload = {
                    **{c: float(row[c]) for c in ["x1", "x2", "noise"]},
                    "isFraud": int(row["isFraud"]),
                }
                fh.write(json.dumps(payload) + "\n")

        result = store.retrain_and_swap(data_df=df)
        assert result["swapped"] is True, result["reason"]
        assert result["new_auc"] >= result["old_auc"]
        assert result["feedback_rows"] == len(fb)

    def test_raises_without_served_model(self, tmp_path, monkeypatch):
        monkeypatch.setattr(store, "CURRENT_DIR", tmp_path / "missing")
        with pytest.raises(RuntimeError, match="train_model"):
            store.retrain_and_swap(data_df=_build_df())


class TestHonestMetrics:
    """Aggregates that must refuse to report nonsense when data is thin."""

    def test_chargeback_requires_min_labelled_approvals(self):
        rows = [{"decision": "APPROVE", "outcome": "fraud", "amount": 100.0}]
        assert store._chargeback_bps(rows) is None

    def test_chargeback_reported_at_min_sample(self):
        rows = [
            {"decision": "APPROVE", "outcome": "fraud", "amount": 100.0}
        ] * store._MIN_LABELLED_APPROVED
        assert store._chargeback_bps(rows) == 10000.0

    def test_chargeback_zero_when_labeled_approvals_are_clean(self):
        rows = [{"decision": "APPROVE", "outcome": "safe", "amount": 50.0}] * 20
        assert store._chargeback_bps(rows) == 0.0

    def _latency_conn(self, old_ms: float, new_ms: float) -> sqlite3.Connection:
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        conn.execute("CREATE TABLE decisions (timestamp TEXT, latency_ms REAL)")
        stale = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
        fresh = datetime.now(timezone.utc).isoformat()
        conn.executemany(
            "INSERT INTO decisions (timestamp, latency_ms) VALUES (?, ?)",
            [(stale, old_ms), (fresh, new_ms)],
        )
        return conn

    def test_latency_ignores_samples_outside_window(self):
        conn = self._latency_conn(5000.0, 180.0)
        try:
            out = store._latency(conn)
        finally:
            conn.close()
        assert out["samples"] == 1
        assert out["p50_ms"] == 180.0
        assert out["window_seconds"] == 900

    def test_latency_empty_when_no_recent_samples(self):
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        conn.execute("CREATE TABLE decisions (timestamp TEXT, latency_ms REAL)")
        stale = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
        conn.execute("INSERT INTO decisions VALUES (?, ?)", (stale, 5000.0))
        try:
            out = store._latency(conn)
        finally:
            conn.close()
        assert out["samples"] == 0
        assert out["p50_ms"] is None
