"""Unit tests for fraud_detect.serving — model serving helpers."""

from __future__ import annotations

import numpy as np
import pandas as pd

from fraud_detect import serving
from fraud_detect.serving import (
    align_features,
    explain_top_features,
    load_artefact,
    median_baseline,
    predict_proba,
    risk_tier,
    save_artefact,
)


def _tiny_lightgbm(path, n: int = 200):
    """Train a tiny LightGBM and save it as an artefact in ``path``."""
    import lightgbm as lgb

    rng = np.random.default_rng(1)
    x = pd.DataFrame(
        {
            "a": rng.standard_normal(n),
            "b": rng.standard_normal(n),
            "extra": rng.integers(0, 3, n),
        }
    )
    y = (x["a"] + x["b"] > 0).astype(int)
    model = lgb.train(
        {"objective": "binary", "verbose": -1},
        lgb.Dataset(x, label=y),
        num_boost_round=6,
    )
    features = ["a", "b", "extra"]
    baseline = median_baseline(features, x)
    save_artefact(path, model, features, baseline, {"roc_auc": 0.9, "seed": 1})
    return model, features


class TestRiskTier:
    def test_low(self):
        assert risk_tier(0.05).label == "low"

    def test_medium_at_0_15(self):
        assert risk_tier(0.15).label == "medium"

    def test_high(self):
        assert risk_tier(0.9).label == "high"

    def test_action_always_present(self):
        assert risk_tier(0.7).action


class TestAlignFeatures:
    def test_adds_missing_and_drops_extra(self):
        df = pd.DataFrame({"a": [1.0], "extra": [9.0]})
        out = align_features(df, ["a", "b"])
        assert list(out.columns) == ["a", "b"]
        assert float(out.iloc[0]["b"]) == serving.FILL_VALUE

    def test_float_dtype(self):
        out = align_features(pd.DataFrame({"a": [1, 2]}), ["a"])
        assert out["a"].dtype == np.float32


class TestMedianBaseline:
    def test_median_from_reference(self):
        ref = pd.DataFrame({"a": [1.0, 2.0, 3.0], "b": [10.0, 20.0, 30.0]})
        row = median_baseline(["a", "b", "m"], ref)
        assert float(row.iloc[0]["a"]) == 2.0
        assert float(row.iloc[0]["b"]) == 20.0
        assert float(row.iloc[0]["m"]) == serving.FILL_VALUE


class TestArtefactRoundtrip:
    def test_save_load_roundtrip(self, tmp_path):
        model, features = _tiny_lightgbm(tmp_path / "art")
        assert (tmp_path / "art" / "model.joblib").exists()

        art = load_artefact(tmp_path / "art")
        assert art.features == features
        assert art.meta["roc_auc"] == 0.9

        x = align_features(pd.DataFrame({"a": [0.5], "b": [-0.5]}), art.features)
        prob = predict_proba(art.model, x)
        assert prob.shape == (1,)
        assert 0.0 <= float(prob[0]) <= 1.0


class TestExplain:
    def test_top_n_and_direction(self, tmp_path):
        _tiny_lightgbm(tmp_path / "art")
        art = load_artefact(tmp_path / "art")
        x = align_features(pd.DataFrame({"a": [2.0], "b": [2.0]}), art.features)
        top = explain_top_features(art.model, x, art.features, top_n=2)
        assert len(top) <= 2
        assert set(top.columns) >= {"feature", "contribution", "direction"}
