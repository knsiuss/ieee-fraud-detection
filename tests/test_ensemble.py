"""Tests for the ensemble module (fraud_detect.ensemble).

Uses synthetic data and dummy model wrappers so tests run quickly without
training real gradient-boosting models.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from fraud_detect import ensemble as en
from fraud_detect.models import ModelBackend, ModelResult


# --------------------------------------------------------------------------- #
# Fixtures
# --------------------------------------------------------------------------- #


@pytest.fixture
def dummy_model_result() -> ModelResult:
    """A ModelResult wrapping a simple threshold classifier."""
    return ModelResult(
        backend=ModelBackend.LIGHTGBM,
        model=_DummyModel(),
        train_auc=0.75,
        val_auc=0.73,
    )


@pytest.fixture
def dummy_model_result_xgb() -> ModelResult:
    """A ModelResult wrapping another dummy classifier."""
    return ModelResult(
        backend=ModelBackend.XGBOOST,
        model=_DummyModel(offset=0.1),
        train_auc=0.72,
        val_auc=0.71,
    )


@pytest.fixture
def models_dict(
    dummy_model_result: ModelResult,
    dummy_model_result_xgb: ModelResult,
) -> dict[ModelBackend, ModelResult]:
    return {
        ModelBackend.LIGHTGBM: dummy_model_result,
        ModelBackend.XGBOOST: dummy_model_result_xgb,
    }


@pytest.fixture
def sample_data() -> tuple[pd.DataFrame, pd.Series]:
    rng = np.random.default_rng(42)
    n = 100
    X = pd.DataFrame({"f1": rng.standard_normal(n), "f2": rng.standard_normal(n)})
    y = pd.Series(rng.integers(0, 2, n))
    return X, y


# --------------------------------------------------------------------------- #
# EnsembleStrategy / EnsembleConfig
# --------------------------------------------------------------------------- #


class _DummyModel:
    """Minimal model stand-in that returns predictable probabilities."""

    def __init__(self, offset: float = 0.0) -> None:
        self._offset = offset

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        n = X.shape[0]
        p = np.full(n, 0.5 + self._offset)
        p = np.clip(p, 0.0, 1.0)
        return np.column_stack([1.0 - p, p])


def test_ensemble_strategy_values() -> None:
    assert en.EnsembleStrategy.HARD_VOTING.value == "hard_voting"
    assert en.EnsembleStrategy.SOFT_VOTING.value == "soft_voting"
    assert en.EnsembleStrategy.STACKING.value == "stacking"


def test_ensemble_config_defaults() -> None:
    cfg = en.EnsembleConfig(
        strategy=en.EnsembleStrategy.SOFT_VOTING,
        model_backends=[ModelBackend.LIGHTGBM],
    )
    assert cfg.weights is None
    assert cfg.meta_learner == "logistic"
    assert cfg.random_state == 42


def test_ensemble_config_weight_mismatch() -> None:
    with pytest.raises(ValueError, match="Number of weights"):
        en.EnsembleConfig(
            strategy=en.EnsembleStrategy.SOFT_VOTING,
            model_backends=[ModelBackend.LIGHTGBM, ModelBackend.XGBOOST],
            weights=[1.0],  # only one weight for two backends
        )


# --------------------------------------------------------------------------- #
# build_voting_ensemble — soft voting
# --------------------------------------------------------------------------- #


def test_soft_voting_ensemble_predict_proba_shape(
    models_dict: dict[ModelBackend, ModelResult],
) -> None:
    cfg = en.EnsembleConfig(
        strategy=en.EnsembleStrategy.SOFT_VOTING,
        model_backends=[ModelBackend.LIGHTGBM, ModelBackend.XGBOOST],
    )
    ensemble = en.build_voting_ensemble(models_dict, cfg)
    X = pd.DataFrame({"f1": [0.5, -0.3], "f2": [1.0, -0.5]})
    proba = ensemble.predict_proba(X)
    assert proba.shape == (2, 2)
    assert np.allclose(proba.sum(axis=1), 1.0)


def test_soft_voting_ensemble_predict_shape(
    models_dict: dict[ModelBackend, ModelResult],
) -> None:
    cfg = en.EnsembleConfig(
        strategy=en.EnsembleStrategy.SOFT_VOTING,
        model_backends=[ModelBackend.LIGHTGBM, ModelBackend.XGBOOST],
    )
    ensemble = en.build_voting_ensemble(models_dict, cfg)
    X = pd.DataFrame({"f1": [0.5, -0.3], "f2": [1.0, -0.5]})
    preds = ensemble.predict(X)
    assert preds.shape == (2,)
    assert set(preds).issubset({0, 1})


# --------------------------------------------------------------------------- #
# build_voting_ensemble — hard voting
# --------------------------------------------------------------------------- #


def test_hard_voting_ensemble_predict_proba_shape(
    models_dict: dict[ModelBackend, ModelResult],
) -> None:
    cfg = en.EnsembleConfig(
        strategy=en.EnsembleStrategy.HARD_VOTING,
        model_backends=[ModelBackend.LIGHTGBM, ModelBackend.XGBOOST],
    )
    ensemble = en.build_voting_ensemble(models_dict, cfg)
    X = pd.DataFrame({"f1": [0.5], "f2": [1.0]})
    proba = ensemble.predict_proba(X)
    assert proba.shape == (1, 2)
    assert np.allclose(proba.sum(axis=1), 1.0)


# --------------------------------------------------------------------------- #
# build_voting_ensemble — errors
# --------------------------------------------------------------------------- #


def test_voting_ensemble_rejects_stacking(models_dict: dict) -> None:
    cfg = en.EnsembleConfig(
        strategy=en.EnsembleStrategy.STACKING,
        model_backends=[ModelBackend.LIGHTGBM],
    )
    with pytest.raises(ValueError, match="Use build_stacking_ensemble"):
        en.build_voting_ensemble(models_dict, cfg)


def test_voting_ensemble_missing_backend(models_dict: dict) -> None:
    cfg = en.EnsembleConfig(
        strategy=en.EnsembleStrategy.SOFT_VOTING,
        model_backends=[ModelBackend.CATBOOST],
    )
    with pytest.raises(ValueError, match="Missing backend"):
        en.build_voting_ensemble(models_dict, cfg)


# --------------------------------------------------------------------------- #
# build_stacking_ensemble
# --------------------------------------------------------------------------- #


def test_stacking_ensemble_predict_proba_shape(
    models_dict: dict[ModelBackend, ModelResult],
    sample_data: tuple[pd.DataFrame, pd.Series],
) -> None:
    X, y = sample_data
    cfg = en.EnsembleConfig(
        strategy=en.EnsembleStrategy.STACKING,
        model_backends=[ModelBackend.LIGHTGBM, ModelBackend.XGBOOST],
    )
    ensemble = en.build_stacking_ensemble(models_dict, cfg, X, y, X, y)
    proba = ensemble.predict_proba(X)
    assert proba.shape == (100, 2)
    assert np.allclose(proba.sum(axis=1), 1.0)


def test_stacking_ensemble_predict_shape(
    models_dict: dict[ModelBackend, ModelResult],
    sample_data: tuple[pd.DataFrame, pd.Series],
) -> None:
    X, y = sample_data
    cfg = en.EnsembleConfig(
        strategy=en.EnsembleStrategy.STACKING,
        model_backends=[ModelBackend.LIGHTGBM, ModelBackend.XGBOOST],
    )
    ensemble = en.build_stacking_ensemble(models_dict, cfg, X, y, X, y)
    preds = ensemble.predict(X)
    assert preds.shape == (100,)
    assert set(preds).issubset({0, 1})


# --------------------------------------------------------------------------- #
# evaluate_ensemble
# --------------------------------------------------------------------------- #


def test_evaluate_ensemble_returns_metrics(
    models_dict: dict[ModelBackend, ModelResult],
    sample_data: tuple[pd.DataFrame, pd.Series],
) -> None:
    X, y = sample_data
    cfg = en.EnsembleConfig(
        strategy=en.EnsembleStrategy.SOFT_VOTING,
        model_backends=[ModelBackend.LIGHTGBM, ModelBackend.XGBOOST],
    )
    ensemble = en.build_voting_ensemble(models_dict, cfg)
    metrics = en.evaluate_ensemble(ensemble, X, y)
    expected_keys = {"auc", "accuracy", "precision", "recall", "f1"}
    assert expected_keys.issubset(metrics.keys())
    for v in metrics.values():
        assert 0.0 <= v <= 1.0
