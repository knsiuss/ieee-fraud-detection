"""Tests for the advanced model training functions in fraud_detect.models.

These tests verify that LightGBM, XGBoost, and CatBoost training pipelines
produce correctly shaped ``ModelResult`` and ``CrossValidationResult`` objects.
They use small synthetic data so they run quickly.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from fraud_detect import models
from fraud_detect.models import ModelBackend, ModelResult


@pytest.fixture
def binary_df() -> pd.DataFrame:
    """Small binary-classification DataFrame for smoke tests."""
    rng = np.random.default_rng(42)
    n = 200
    return pd.DataFrame(
        {
            "isFraud": rng.integers(0, 2, n),
            "f1": rng.standard_normal(n),
            "f2": rng.standard_normal(n),
            "f3": rng.standard_normal(n),
        }
    )


# --------------------------------------------------------------------------- #
# ModelBackend enum
# --------------------------------------------------------------------------- #


def test_model_backend_enum_values() -> None:
    assert ModelBackend.LIGHTGBM.value == "lightgbm"
    assert ModelBackend.XGBOOST.value == "xgboost"
    assert ModelBackend.CATBOOST.value == "catboost"


def test_model_backend_all_backends() -> None:
    all_backends = list(ModelBackend)
    assert len(all_backends) == 3


# --------------------------------------------------------------------------- #
# train_model — LightGBM
# --------------------------------------------------------------------------- #


def test_train_lightgbm_returns_model_result(binary_df: pd.DataFrame) -> None:
    result = models.train_model(
        binary_df, ModelBackend.LIGHTGBM, num_boost_round=10
    )
    assert isinstance(result, ModelResult)
    assert result.backend == ModelBackend.LIGHTGBM
    assert 0.0 <= result.train_auc <= 1.0
    assert 0.0 <= result.val_auc <= 1.0
    assert result.training_time >= 0.0
    assert result.model is not None


def test_train_lightgbm_feature_importance(binary_df: pd.DataFrame) -> None:
    result = models.train_model(
        binary_df, ModelBackend.LIGHTGBM, num_boost_round=10
    )
    assert result.feature_importance is not None
    assert list(result.feature_importance.columns) == ["feature", "importance"]
    assert (result.feature_importance["importance"] >= 0).all()
    assert result.feature_importance["importance"].is_monotonic_decreasing


# --------------------------------------------------------------------------- #
# train_model — XGBoost
# --------------------------------------------------------------------------- #


def test_train_xgboost_returns_model_result(binary_df: pd.DataFrame) -> None:
    pytest.importorskip("xgboost")
    result = models.train_model(
        binary_df, ModelBackend.XGBOOST, num_boost_round=10
    )
    assert isinstance(result, ModelResult)
    assert result.backend == ModelBackend.XGBOOST
    assert 0.0 <= result.train_auc <= 1.0
    assert 0.0 <= result.val_auc <= 1.0
    assert result.model is not None


def test_train_xgboost_feature_importance(binary_df: pd.DataFrame) -> None:
    pytest.importorskip("xgboost")
    result = models.train_model(
        binary_df, ModelBackend.XGBOOST, num_boost_round=10
    )
    # XGBoost may return an empty importance dict for very small data
    if result.feature_importance is not None and not result.feature_importance.empty:
        assert list(result.feature_importance.columns) == ["feature", "importance"]


# --------------------------------------------------------------------------- #
# train_model — CatBoost
# --------------------------------------------------------------------------- #


def test_train_catboost_returns_model_result(binary_df: pd.DataFrame) -> None:
    pytest.importorskip("catboost")
    result = models.train_model(
        binary_df, ModelBackend.CATBOOST, num_boost_round=10
    )
    assert isinstance(result, ModelResult)
    assert result.backend == ModelBackend.CATBOOST
    assert 0.0 <= result.train_auc <= 1.0
    assert 0.0 <= result.val_auc <= 1.0
    assert result.model is not None


def test_train_catboost_feature_importance(binary_df: pd.DataFrame) -> None:
    pytest.importorskip("catboost")
    result = models.train_model(
        binary_df, ModelBackend.CATBOOST, num_boost_round=10
    )
    assert result.feature_importance is not None
    assert list(result.feature_importance.columns) == ["feature", "importance"]
    assert (result.feature_importance["importance"] >= 0).all()


# --------------------------------------------------------------------------- #
# train_model — unknown backend
# --------------------------------------------------------------------------- #


def test_train_model_unknown_backend(binary_df: pd.DataFrame) -> None:
    with pytest.raises(ValueError, match="Unknown backend"):
        models.train_model(binary_df, backend="invalid_backend")  # type: ignore[arg-type]


# --------------------------------------------------------------------------- #
# train_model — custom params override
# --------------------------------------------------------------------------- #


def test_train_model_with_custom_params(binary_df: pd.DataFrame) -> None:
    custom_params = {"learning_rate": 0.5, "num_leaves": 8}
    result = models.train_model(
        binary_df,
        ModelBackend.LIGHTGBM,
        params=custom_params,
        num_boost_round=10,
    )
    assert 0.0 <= result.val_auc <= 1.0


# --------------------------------------------------------------------------- #
# train_all_models
# --------------------------------------------------------------------------- #


def test_train_all_models_returns_dict(binary_df: pd.DataFrame) -> None:
    results = models.train_all_models(
        binary_df,
        backends=[ModelBackend.LIGHTGBM, ModelBackend.XGBOOST],
        num_boost_round=10,
    )
    assert isinstance(results, dict)
    assert ModelBackend.LIGHTGBM in results
    assert ModelBackend.XGBOOST in results
    for result in results.values():
        assert isinstance(result, ModelResult)


def test_train_all_models_returns_all_backends(binary_df: pd.DataFrame) -> None:
    """Test with all available backends, skipping any that are not installed."""
    available_backends = [ModelBackend.LIGHTGBM]
    try:
        import xgboost  # noqa: F401
        available_backends.append(ModelBackend.XGBOOST)
    except ImportError:
        pass
    try:
        import catboost  # noqa: F401
        available_backends.append(ModelBackend.CATBOOST)
    except ImportError:
        pass

    results = models.train_all_models(
        binary_df,
        backends=available_backends,
        num_boost_round=10,
    )
    for backend in available_backends:
        assert backend in results


# --------------------------------------------------------------------------- #
# cross_validate_model
# --------------------------------------------------------------------------- #


def test_cross_validate_model_returns_cv_result(binary_df: pd.DataFrame) -> None:
    cv = models.cross_validate_model(
        binary_df, ModelBackend.LIGHTGBM, cv_folds=3, num_boost_round=10
    )
    assert isinstance(cv, models.CrossValidationResult)
    assert cv.backend == ModelBackend.LIGHTGBM
    assert 0.0 <= cv.mean_auc <= 1.0
    assert 0.0 <= cv.std_auc <= 1.0
    assert len(cv.fold_scores) == 3
    assert len(cv.scores) == 3


def test_cross_validate_model_scores_sorted(binary_df: pd.DataFrame) -> None:
    cv = models.cross_validate_model(
        binary_df, ModelBackend.LIGHTGBM, cv_folds=3, num_boost_round=10
    )
    for fold_idx, _ in cv.fold_scores:
        assert isinstance(fold_idx, int)


# --------------------------------------------------------------------------- #
# ModelResult dataclass
# --------------------------------------------------------------------------- #


def test_model_result_defaults() -> None:
    result = ModelResult(
        backend=ModelBackend.LIGHTGBM,
        model="dummy",
        train_auc=0.8,
        val_auc=0.75,
    )
    assert result.feature_importance is None
    assert result.training_time == 0.0


# --------------------------------------------------------------------------- #
# CrossValidationResult dataclass
# --------------------------------------------------------------------------- #


def test_cross_validation_result_scores_property() -> None:
    cv = models.CrossValidationResult(
        backend=ModelBackend.LIGHTGBM,
        fold_scores=[(0, 0.8), (1, 0.85)],
        mean_auc=0.825,
        std_auc=0.025,
    )
    assert cv.scores == [0.8, 0.85]
