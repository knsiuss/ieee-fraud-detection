"""Tests for the hyperparameter-tuning module (fraud_detect.tuning).

Uses synthetic data so the suite runs without the real IEEE-CIS dataset.
Optuna is an optional dependency — tests that require it are skipped when
it is not installed.
"""

from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np
import pandas as pd
import pytest

from fraud_detect import tuning
from fraud_detect.models import ModelBackend


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
        }
    )


# --------------------------------------------------------------------------- #
# build_search_space
# --------------------------------------------------------------------------- #


def test_build_search_space_returns_dict() -> None:
    space = tuning.build_search_space(ModelBackend.LIGHTGBM)
    assert isinstance(space, dict)
    assert "num_leaves" in space
    assert "learning_rate" in space


def test_build_search_space_all_backends() -> None:
    for backend in ModelBackend:
        space = tuning.build_search_space(backend)
        assert isinstance(space, dict)
        assert len(space) > 0


def test_build_search_space_has_low_high_keys() -> None:
    space = tuning.build_search_space(ModelBackend.LIGHTGBM)
    for name, spec in space.items():
        assert "low" in spec, f"{name} missing 'low'"
        assert "high" in spec, f"{name} missing 'high'"


# --------------------------------------------------------------------------- #
# save_best_params / load_best_params
# --------------------------------------------------------------------------- #


def test_save_and_load_best_params_round_trip() -> None:
    backend = ModelBackend.LIGHTGBM
    params = {"num_leaves": 64, "learning_rate": 0.05, "subsample": 0.8}
    tuning.save_best_params(backend, params)
    loaded = tuning.load_best_params(backend, fallback_to_defaults=False)
    assert loaded == params


def test_load_best_params_fallback_defaults() -> None:
    """When no saved file exists, fallback should return default params."""
    backend = ModelBackend.LIGHTGBM
    loaded = tuning.load_best_params(backend, fallback_to_defaults=True)
    assert "num_leaves" in loaded
    assert "learning_rate" in loaded


def test_load_best_params_no_fallback_returns_empty() -> None:
    """When no saved file exists and fallback is off, return empty dict.

    Uses a non-existent backend to avoid collision with previous tests
    that may have written to the metadata directory.
    """
    from fraud_detect.tuning import _best_params_path

    # Use a backend that definitely has no saved params
    backend = ModelBackend.CATBOOST
    path = _best_params_path(backend)

    # Remove any leftover file from previous test runs
    if path.exists():
        path.unlink()

    loaded = tuning.load_best_params(backend, fallback_to_defaults=False)
    assert loaded == {}


# --------------------------------------------------------------------------- #
# tune_model (requires optuna)
# --------------------------------------------------------------------------- #


def test_tune_model_returns_study(binary_df: pd.DataFrame) -> None:
    pytest.importorskip("optuna")
    study = tuning.tune_model(
        binary_df,
        backend=ModelBackend.LIGHTGBM,
        n_trials=3,
    )
    assert study is not None
    assert study.best_value > 0.0
    assert study.best_params is not None
    assert len(study.best_params) > 0


def test_tune_model_best_value_in_range(binary_df: pd.DataFrame) -> None:
    pytest.importorskip("optuna")
    study = tuning.tune_model(
        binary_df,
        backend=ModelBackend.LIGHTGBM,
        n_trials=3,
    )
    assert 0.0 <= study.best_value <= 1.0


def test_tune_model_raises_without_optuna(binary_df: pd.DataFrame) -> None:
    """Simulate optuna not being available."""
    import fraud_detect.tuning as tuning_mod

    original = tuning_mod.optuna
    tuning_mod.optuna = None
    try:
        with pytest.raises(ValueError, match="Optuna is required"):
            tuning.tune_model(binary_df, n_trials=1)
    finally:
        tuning_mod.optuna = original
