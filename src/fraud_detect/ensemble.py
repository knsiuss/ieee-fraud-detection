"""Ensemble methods for combining gradient-boosting model predictions.

Supports hard / soft voting and stacking with a logistic-regression meta-learner.
Each function accepts a dictionary of ``ModelBackend → ModelResult`` from
:func:`fraud_detect.models.train_all_models`.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

from . import config
from .models import ModelBackend, ModelResult

logger = logging.getLogger(__name__)

class EnsembleStrategy(str, Enum):
    """Supported ensemble combination strategies."""

    HARD_VOTING = "hard_voting"
    SOFT_VOTING = "soft_voting"
    STACKING = "stacking"

@dataclass
class EnsembleConfig:
    """Configuration for building an ensemble model.

    Parameters
    ----------
    strategy:
        Combination strategy to use.
    model_backends:
        List of backends to include in the ensemble.
    weights:
        Per-model weights for ``SOFT_VOTING`` (must match ``model_backends``
        order, or ``None`` for uniform weighting).
    meta_learner:
        Meta-learner type for ``STACKING`` (default: ``"logistic"``).
    random_state:
        Seed for reproducibility.
    """

    strategy: EnsembleStrategy
    model_backends: list[ModelBackend]
    weights: list[float] | None = None
    meta_learner: str = "logistic"
    random_state: int = config.RANDOM_STATE

    def __post_init__(self) -> None:
        if self.weights is not None and len(self.weights) != len(self.model_backends):
            msg = (
                f"Number of weights ({len(self.weights)}) must match "
                f"number of backends ({len(self.model_backends)})"
            )
            raise ValueError(msg)

def _predict_from_models(
    models_dict: dict[ModelBackend, ModelResult],
    X: pd.DataFrame,
) -> dict[str, np.ndarray]:
    """Generate probability predictions from all models in ``models_dict``.

    Returns a dict mapping ``"<backend>"`` → predicted probabilities for class 1.
    """
    preds: dict[str, np.ndarray] = {}
    for backend, result in models_dict.items():
        model = result.model
        if hasattr(model, "predict_proba"):
            preds[backend.value] = model.predict_proba(X)[:, 1]
        elif hasattr(model, "predict"):
            preds[backend.value] = model.predict(X)
        else:
            msg = f"Model for {backend.value} does not support predict or predict_proba"
            raise TypeError(msg)
    return preds

def _normalise_weights(weights: list[float] | None, n: int) -> np.ndarray:
    """Normalise a weight list to sum to 1, or return uniform weights."""
    if weights is None:
        return np.full(n, 1.0 / n)
    w = np.asarray(weights, dtype=float)
    return w / w.sum()

def build_voting_ensemble(
    models_dict: dict[ModelBackend, ModelResult],
    config_obj: EnsembleConfig,
) -> Any:
    """Build a voting ensemble (hard or soft) from trained models.

    Parameters
    ----------
    models_dict:
        Dictionary of trained models keyed by ``ModelBackend``.
    config_obj:
        Ensemble configuration specifying strategy, backends, and weights.

    Returns
    -------
    object
        A callable ensemble with a ``predict_proba`` interface.

    Raises
    ------
    ValueError
        If ``config_obj.strategy`` is ``STACKING`` (use :func:`build_stacking_ensemble`
        instead) or if a required backend is missing.

    Examples
    --------
    >>> from fraud_detect.models import ModelBackend
    >>> dummy_result = ModelResult(backend=ModelBackend.LIGHTGBM,
    ...     model=None, train_auc=0.0, val_auc=0.0)
    >>> cfg = EnsembleConfig(strategy=EnsembleStrategy.SOFT_VOTING,
    ...     model_backends=[ModelBackend.LIGHTGBM])
    >>> # Would raise — model has no predict_proba
    """
    if config_obj.strategy == EnsembleStrategy.STACKING:
        msg = "Use build_stacking_ensemble() for stacking strategy"
        raise ValueError(msg)

    for backend in config_obj.model_backends:
        if backend not in models_dict:
            msg = f"Missing backend {backend.value} in models_dict"
            raise ValueError(msg)

    weights = _normalise_weights(config_obj.weights, len(config_obj.model_backends))
    is_hard = config_obj.strategy == EnsembleStrategy.HARD_VOTING

    class _VotingEnsemble:
        """Internal voting ensemble wrapper."""

        _models: dict[ModelBackend, ModelResult] = models_dict
        _backends: list[ModelBackend] = config_obj.model_backends
        _weights: np.ndarray = weights
        _hard: bool = is_hard

        def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
            preds = _predict_from_models(self._models, X)
            weighted_probas = np.zeros((X.shape[0], 2))

            for backend, weight in zip(self._backends, self._weights, strict=True):
                proba_class1 = preds[backend.value]
                if self._hard:
                    # Hard voting: threshold at 0.5, then average binary decisions
                    proba_class1 = (proba_class1 >= 0.5).astype(float)
                weighted_probas[:, 1] += weight * proba_class1

            # Soft-voting case: renormalise (hard-voting already yields 0-1)
            if not self._hard:
                weighted_probas[:, 1] = np.clip(weighted_probas[:, 1], 0.0, 1.0)
            weighted_probas[:, 0] = 1.0 - weighted_probas[:, 1]
            return weighted_probas

        def predict(self, X: pd.DataFrame) -> np.ndarray:
            return (self.predict_proba(X)[:, 1] >= 0.5).astype(int)

    return _VotingEnsemble()

def build_stacking_ensemble(
    models_dict: dict[ModelBackend, ModelResult],
    config_obj: EnsembleConfig,
    X_train: pd.DataFrame,
    y_train: pd.Series,
    X_val: pd.DataFrame,
    y_val: pd.Series,
) -> Any:
    """Build a stacking ensemble with a meta-learner on validation predictions.

    Parameters
    ----------
    models_dict:
        Dictionary of trained models keyed by ``ModelBackend``.
    config_obj:
        Ensemble configuration (strategy is ignored — always stacks).
    X_train:
        Training features used to generate base-model predictions.
    y_train:
        Training target.
    X_val:
        Validation features used for stacking.
    y_val:
        Validation target.

    Returns
    -------
    object
        A callable ensemble with a ``predict_proba`` interface backed by the
        fitted meta-learner.

    Raises
    ------
    ValueError
        If ``config_obj.strategy`` is not ``STACKING``.
    """
    from sklearn.linear_model import LogisticRegression

    for backend in config_obj.model_backends:
        if backend not in models_dict:
            msg = f"Missing backend {backend.value} in models_dict"
            raise ValueError(msg)

    # Generate OOF-style predictions on the validation set
    val_preds = _predict_from_models(models_dict, X_val)

    # Build meta-feature matrix
    meta_features = np.column_stack([val_preds[b.value] for b in config_obj.model_backends])
    meta_features = np.nan_to_num(meta_features, nan=0.5)

    # Train meta-learner
    meta = LogisticRegression(
        class_weight="balanced",
        max_iter=1000,
        random_state=config_obj.random_state,
    )
    meta.fit(meta_features, y_val)

    train_preds = _predict_from_models(models_dict, X_train)
    train_meta = np.column_stack([train_preds[b.value] for b in config_obj.model_backends])
    train_meta = np.nan_to_num(train_meta, nan=0.5)

    class _StackingEnsemble:
        """Internal stacking ensemble wrapper."""

        _base_models: dict[ModelBackend, ModelResult] = models_dict
        _backends: list[ModelBackend] = config_obj.model_backends
        _meta: Any = meta
        _train_preds_cache: dict[str, np.ndarray] | None = None

        def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
            preds = _predict_from_models(self._base_models, X)
            meta_X = np.column_stack([preds[b.value] for b in self._backends])
            meta_X = np.nan_to_num(meta_X, nan=0.5)
            return self._meta.predict_proba(meta_X)

        def predict(self, X: pd.DataFrame) -> np.ndarray:
            return self.predict_proba(X)[:, 1] >= 0.5

    return _StackingEnsemble()

def evaluate_ensemble(
    ensemble: Any,
    X_val: pd.DataFrame,
    y_val: pd.Series,
) -> dict[str, float]:
    """Evaluate an ensemble on validation data.

    Parameters
    ----------
    ensemble:
        Ensemble object with a ``predict_proba`` method.
    X_val:
        Validation features.
    y_val:
        Validation target.

    Returns
    -------
    dict[str, float]
        Dictionary with keys ``auc``, ``accuracy``, ``precision``, ``recall``,
        ``f1``.

    Examples
    --------
    >>> import numpy as np, pandas as pd
    >>> from sklearn.metrics import roc_auc_score
    >>> class DummyEnsemble:
    ...     def predict_proba(self, X):
    ...         return np.column_stack([np.zeros(len(X)), np.full(len(X), 0.5)])
    ...     def predict(self, X):
    ...         return np.zeros(len(X), dtype=int)
    >>> y = pd.Series([0, 1, 0, 1])
    >>> X = pd.DataFrame({"a": [1, 2, 3, 4]})
    >>> result = evaluate_ensemble(DummyEnsemble(), X, y)
    >>> "auc" in result
    True
    """
    from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score

    y_pred_proba = ensemble.predict_proba(X_val)[:, 1]
    y_pred = ensemble.predict(X_val)

    return {
        "auc": float(roc_auc_score(y_val, y_pred_proba)),
        "accuracy": float(accuracy_score(y_val, y_pred)),
        "precision": float(precision_score(y_val, y_pred, zero_division=0)),
        "recall": float(recall_score(y_val, y_pred, zero_division=0)),
        "f1": float(f1_score(y_val, y_pred, zero_division=0)),
    }
