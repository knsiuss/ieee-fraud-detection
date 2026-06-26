"""Hyperparameter tuning with Optuna for gradient-boosting models.

Each model backend (LightGBM, XGBoost, CatBoost) has a search space defined in
:mod:`fraud_detect.config`. The :func:`tune_model` function runs an Optuna study
and saves the best parameters; :func:`load_best_params` loads them back, falling
through to the config defaults when no saved study exists.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from . import config
from .models import ModelBackend, make_train_val_split

logger = logging.getLogger(__name__)

try:
    import optuna
except ImportError:  # pragma: no cover
    optuna = None  # type: ignore[assignment]

def _get_space(backend: ModelBackend) -> dict[str, dict[str, Any]]:
    """Return the tuning search space dict for ``backend`` from ``config``."""
    name = config.BACKEND_TUNING_SPACE_MAP[backend.value]
    return dict(getattr(config, name, {}))

def build_search_space(backend: ModelBackend) -> dict[str, dict[str, Any]]:
    """Return the Optuna search-space definition for the given backend.

    Parameters
    ----------
    backend:
        Model backend to look up the search space for.

    Returns
    -------
    dict[str, dict[str, Any]]
        Mapping of hyperparameter name → ``{"low": ..., "high": ..., "log": ...}``.

    Examples
    --------
    >>> space = build_search_space(ModelBackend.LIGHTGBM)
    >>> "num_leaves" in space
    True
    >>> "learning_rate" in space
    True
    """
    return _get_space(backend)

def _suggest_from_space(trial: Any, space: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Suggest a set of hyperparameters from a search-space dict."""
    params: dict[str, Any] = {}
    for name, spec in space.items():
        low = spec["low"]
        high = spec["high"]
        is_log = spec.get("log", False)
        if isinstance(low, int) and isinstance(high, int):
            params[name] = trial.suggest_int(name, low, high, log=is_log)
        else:
            params[name] = trial.suggest_float(name, low, high, log=is_log)
    return params

def _objective_wrapper(
    trial: Any,
    backend: ModelBackend,
    X_train: pd.DataFrame,
    y_train: pd.Series,
    X_val: pd.DataFrame,
    y_val: pd.Series,
    base_params: dict[str, Any] | None = None,
) -> float:
    """Optuna objective: train a model and return validation AUC."""
    from sklearn.metrics import roc_auc_score

    from .models import _BACKEND_FIT_MAP

    space = _get_space(backend)
    sampled_params = _suggest_from_space(trial, space)
    merged_params = {**(base_params or {}), **sampled_params}

    fit_fn = _BACKEND_FIT_MAP[backend]
    _, _, val_auc, _ = fit_fn(
        X_train,
        y_train,
        X_val,
        y_val,
        params=merged_params,
        num_boost_round=config.LGBM_NUM_BOOST_ROUND
        if backend == ModelBackend.LIGHTGBM
        else config.XGB_NUM_BOOST_ROUND,
        early_stopping_rounds=config.LGBM_EARLY_STOPPING_ROUNDS,
    )
    return float(val_auc)

def tune_model(
    df: pd.DataFrame,
    backend: ModelBackend = ModelBackend.LIGHTGBM,
    n_trials: int = config.OPTUNA_N_TRIALS,
    study_name: str | None = None,
    direction: str = "maximize",
    base_params: dict[str, Any] | None = None,
    random_state: int = config.RANDOM_STATE,
) -> Any | None:
    """Run Optuna hyperparameter optimisation for a model backend.

    Parameters
    ----------
    df:
        Input DataFrame with target column and feature columns.
    backend:
        Which model backend to tune.
    n_trials:
        Number of Optuna trials.
    study_name:
        Optional study name (used for persistence).
    direction:
        Optimisation direction (``"maximize"`` for AUC).
    base_params:
        Fixed parameters to merge on top of sampled ones.
    random_state:
        Seed for the Optuna sampler.

    Returns
    -------
    optuna.Study | None
        The completed Optuna study, or ``None`` if Optuna is not installed.

    Raises
    ------
    ValueError
        If Optuna is not installed.
    """
    if optuna is None:
        msg = "Optuna is required for hyperparameter tuning. Install with: pip install optuna"
        raise ValueError(msg)

    split = make_train_val_split(df, random_state=random_state)

    study = optuna.create_study(
        study_name=study_name or f"{backend.value}_tuning",
        direction=direction,
        sampler=optuna.samplers.TPESampler(seed=random_state),
    )

    logger.info("Starting %s tuning (%d trials)…", backend.value, n_trials)
    study.optimize(
        lambda trial: _objective_wrapper(
            trial,
            backend,
            split.X_train,
            split.y_train,
            split.X_val,
            split.y_val,
            base_params=base_params,
        ),
        n_trials=n_trials,
        show_progress_bar=True,
    )

    logger.info(
        "Best trial: #%d | AUC = %.5f | Params: %s",
        study.best_trial.number,
        study.best_value,
        study.best_params,
    )
    return study

def _best_params_path(backend: ModelBackend) -> Path:
    """Return the metadata path for saved best parameters."""
    return config.METADATA_DIR / f"{backend.value}_best_params.json"

def save_best_params(backend: ModelBackend, params: dict[str, Any]) -> None:
    """Save best hyperparameters to a JSON file in the metadata directory.

    Parameters
    ----------
    backend:
        Model backend these parameters belong to.
    params:
        Hyperparameter dictionary to save.

    Examples
    --------
    >>> save_best_params(ModelBackend.LIGHTGBM, {"num_leaves": 64})
    """
    path = _best_params_path(backend)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(params, indent=2, default=str))
    logger.info("Best params for %s saved to %s", backend.value, path)

def load_best_params(
    backend: ModelBackend,
    fallback_to_defaults: bool = True,
) -> dict[str, Any]:
    """Load saved best hyperparameters from the metadata directory.

    Parameters
    ----------
    backend:
        Model backend to load parameters for.
    fallback_to_defaults:
        If ``True`` and no saved file exists, return the base default parameters
        from ``config.py``.

    Returns
    -------
    dict[str, Any]
        Loaded best parameters, or default parameters if not found.

    Examples
    --------
    >>> params = load_best_params(ModelBackend.LIGHTGBM)
    >>> "num_leaves" in params
    True
    """
    path = _best_params_path(backend)
    if path.exists():
        data = json.loads(path.read_text())
        logger.info("Loaded best params for %s from %s", backend.value, path)
        return dict(data)

    if fallback_to_defaults:
        _map: dict[str, str] = {
            "lightgbm": "LGBM_PARAMS",
            "xgboost": "XGB_PARAMS",
            "catboost": "CB_PARAMS",
        }
        key = _map.get(backend.value)
        if key:
            defaults = getattr(config, key, {})
            logger.info("No saved params found for %s; using defaults", backend.value)
            return dict(defaults)

    return {}
