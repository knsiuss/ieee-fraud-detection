"""Tests for api/store.py — feedback pool and gated retrain."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from fraud_detect import config, serving  # noqa: E402
from fraud_detect.models import ModelBackend, select_feature_columns, train_model  # noqa: E402

from api import store  # noqa: E402


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
def isolated(tmp_path, monkeypatch):
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
    monkeypatch.setattr(config, "LGBM_NUM_BOOST_ROUND", 20)
    monkeypatch.setattr(config, "LGBM_EARLY_STOPPING_ROUNDS", 5)
    return tmp_path


class TestFeedbackPool:
    def test_record_and_read(self, isolated):
        art = store.current_artefact()
        values = {f: 0.5 for f in art.features[:3]}
        size = store.record_feedback(values, 1)
        assert size == 1
        assert store.feedback_pool_size() == 1

        pool = store.feedback_pool_df()
        assert "isFraud" in pool.columns
        assert len(pool) == 1
        assert int(pool.iloc[0]["isFraud"]) == 1

    def test_empty_pool(self, isolated):
        assert store.feedback_pool_df().empty
        assert store.feedback_pool_size() == 0


class TestRetrainGate:
    def test_returns_summary(self, isolated):
        result = store.retrain_and_swap(data_df=_build_df(seed=1))
        assert set(result) >= {"swapped", "old_auc", "new_auc", "reason"}
        assert isinstance(result["swapped"], bool)
        assert result["feedback_rows"] == 0

    def test_strong_feedback_candidate_swaps(self, isolated):
        df = _build_df(seed=1)
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
                fh.write(json.dumps({**{c: float(row[c]) for c in ["x1", "x2", "noise"]}, "isFraud": int(row["isFraud"])}) + "\n")

        result = store.retrain_and_swap(data_df=df)
        assert result["swapped"] is True, result["reason"]
        assert result["new_auc"] >= result["old_auc"]
        assert result["feedback_rows"] == len(fb)

    def test_raises_without_served_model(self, tmp_path, monkeypatch):
        monkeypatch.setattr(store, "CURRENT_DIR", tmp_path / "missing")
        with pytest.raises(RuntimeError, match="train_model"):
            store.retrain_and_swap(data_df=_build_df())
