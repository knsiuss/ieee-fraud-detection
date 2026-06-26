"""Model training and evaluation helpers.

Wraps the train/val split, baseline logistic-regression pipeline, and
LightGBM feature-importance estimation that notebooks 08 and 09 previously
inlined. Hyperparameters live in :mod:`fraud_detect.config`.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from enum import Enum
from typing import Any

import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from . import config

@dataclass(frozen=True)
class SplitResult:
    """Container for a stratified train/validation split."""

    X_train: pd.DataFrame
    X_val: pd.DataFrame
    y_train: pd.Series
    y_val: pd.Series

def select_feature_columns(df: pd.DataFrame) -> list[str]:
    """Return numeric feature columns, excluding IDs / target / timestamps."""
    excluded = set(config.EXCLUDE_COLUMNS)
    numeric = df.select_dtypes(include="number").columns
    return [c for c in numeric if c not in excluded]

def make_train_val_split(
    df: pd.DataFrame,
    target: str = config.TARGET_COLUMN,
    test_size: float = config.VALIDATION_SIZE,
    random_state: int = config.RANDOM_STATE,
) -> SplitResult:
    """Stratified train/val split on ``df`` using the configured feature set."""
    feature_cols = select_feature_columns(df)
    X = df[feature_cols]  # noqa: N806
    y = df[target]
    X_train, X_val, y_train, y_val = train_test_split(  # noqa: N806
        X,
        y,
        test_size=test_size,
        stratify=y,
        random_state=random_state,
    )
    return SplitResult(X_train=X_train, X_val=X_val, y_train=y_train, y_val=y_val)

def build_logistic_pipeline(random_state: int = config.RANDOM_STATE) -> Pipeline:
    """Median-impute → standardise → balanced logistic regression.

    ``n_jobs`` is intentionally not passed: ``LogisticRegression`` with the
    default ``lbfgs`` solver is single-threaded and recent sklearn versions
    reject the parameter.
    """
    return Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
            (
                "model",
                LogisticRegression(
                    class_weight="balanced",
                    max_iter=1000,
                    random_state=random_state,
                ),
            ),
        ]
    )

def evaluate_classifier(
    pipeline: Pipeline,
    split: SplitResult,
) -> dict[str, float]:
    """Fit ``pipeline`` and return train/val ROC-AUC plus the gap.

    Parameters
    ----------
    pipeline:
        A scikit-learn pipeline (not yet fitted).
    split:
        Train/validation split container.

    Returns
    -------
    dict[str, float]
        Dictionary with keys ``train_auc``, ``val_auc``, ``overfitting_gap``.

    Raises
    ------
    ValueError
        If the fitted model produces fewer than two distinct classes — the
        ROC-AUC is undefined in that case.

    Examples
    --------
    >>> from sklearn.linear_model import LogisticRegression
    >>> from sklearn.pipeline import Pipeline
    >>> import pandas as pd, numpy as np
    >>> rng = np.random.default_rng(42)
    >>> X = pd.DataFrame({"f1": rng.standard_normal(100)})
    >>> y = pd.Series(rng.integers(0, 2, 100))
    >>> split = SplitResult(X, X, y, y)  # dummy — same split for demo
    >>> pipe = Pipeline([("model", LogisticRegression(max_iter=100, random_state=42))])
    >>> result = evaluate_classifier(pipe, split)
    >>> sorted(result.keys())
    ['overfitting_gap', 'train_auc', 'val_auc']
    """
    pipeline.fit(split.X_train, split.y_train)
    y_train_proba = pipeline.predict_proba(split.X_train)[:, 1]
    y_val_proba = pipeline.predict_proba(split.X_val)[:, 1]

    train_auc = roc_auc_score(split.y_train, y_train_proba)
    val_auc = roc_auc_score(split.y_val, y_val_proba)
    return {
        "train_auc": float(train_auc),
        "val_auc": float(val_auc),
        "overfitting_gap": float(train_auc - val_auc),
    }

def compute_lightgbm_importance(
    df: pd.DataFrame,
    params: dict[str, Any] | None = None,
    num_boost_round: int = config.LGBM_NUM_BOOST_ROUND,
    early_stopping_rounds: int = config.LGBM_EARLY_STOPPING_ROUNDS,
) -> pd.DataFrame:
    """Train a quick LightGBM model and return a feature-importance table.

    Returns a DataFrame with columns ``feature`` and ``importance`` sorted
    descending. Requires ``lightgbm`` to be installed.
    """
    import lightgbm as lgb  # imported lazily — lightgbm is optional for the package

    split = make_train_val_split(df)
    feature_cols = list(split.X_train.columns)

    train_set = lgb.Dataset(split.X_train, label=split.y_train)
    val_set = lgb.Dataset(split.X_val, label=split.y_val, reference=train_set)

    params = {**config.LGBM_BASE_PARAMS, **(params or {})}
    model = lgb.train(
        params,
        train_set,
        num_boost_round=num_boost_round,
        valid_sets=[train_set, val_set],
        valid_names=["train", "val"],
        callbacks=[
            lgb.early_stopping(early_stopping_rounds, verbose=False),
            lgb.log_evaluation(0),
        ],
    )

    importance = (
        pd.DataFrame(
            {
                "feature": feature_cols,
                "importance": model.feature_importance(importance_type="gain"),
            }
        )
        .sort_values("importance", ascending=False)
        .reset_index(drop=True)
    )
    return importance

# Phase 1 — Advanced Model Training (LightGBM, XGBoost, CatBoost)

class ModelBackend(str, Enum):
    """Supported gradient-boosting backends for model training."""

    LIGHTGBM = "lightgbm"
    XGBOOST = "xgboost"
    CATBOOST = "catboost"

@dataclass
class ModelResult:
    """Container for a trained model and its evaluation results.

    Attributes
    ----------
    backend:
        The model backend that produced this result.
    model:
        The trained model object (backendspecific type).
    train_auc:
        ROC-AUC on the training set.
    val_auc:
        ROC-AUC on the validation set.
    feature_importance:
        Feature importance DataFrame (columns ``feature``, ``importance``)
        or ``None`` if the backend does not provide importance.
    training_time:
        Wall-clock training time in seconds.
    """

    backend: ModelBackend
    model: Any
    train_auc: float
    val_auc: float
    feature_importance: pd.DataFrame | None = None
    training_time: float = 0.0

@dataclass
class CrossValidationResult:
    """Container for k-fold cross-validation results.

    Attributes
    ----------
    backend:
        The model backend that produced this result.
    fold_scores:
        List of (fold_index, auc) tuples.
    mean_auc:
        Mean AUC across folds.
    std_auc:
        Standard deviation of AUC across folds.
    training_time:
        Total wall-clock training time in seconds.
    """

    backend: ModelBackend
    fold_scores: list[tuple[int, float]]
    mean_auc: float
    std_auc: float
    training_time: float = 0.0

    @property
    def scores(self) -> list[float]:
        """Convenience: return just the AUC values."""
        return [score for _, score in self.fold_scores]

def _lgb_fit(
    X_train: pd.DataFrame,
    y_train: pd.Series,
    X_val: pd.DataFrame,
    y_val: pd.Series,
    params: dict[str, Any] | None = None,
    num_boost_round: int = config.LGBM_NUM_BOOST_ROUND,
    early_stopping_rounds: int = config.LGBM_EARLY_STOPPING_ROUNDS,
    **kwargs: Any,
) -> tuple[Any, float, float, pd.DataFrame | None]:
    """Fit a LightGBM model and return (model, train_auc, val_auc, importance)."""
    import lightgbm as lgb

    params = {**config.LGBM_PARAMS, **(params or {})}
    train_set = lgb.Dataset(X_train, label=y_train)
    val_set = lgb.Dataset(X_val, label=y_val, reference=train_set)

    model = lgb.train(
        params,
        train_set,
        num_boost_round=num_boost_round,
        valid_sets=[train_set, val_set],
        valid_names=["train", "val"],
        callbacks=[
            lgb.early_stopping(early_stopping_rounds, verbose=False),
            lgb.log_evaluation(0),
        ],
        **kwargs,
    )

    _y_train_proba = model.predict(X_train, num_iteration=model.best_iteration)
    _y_val_proba = model.predict(X_val, num_iteration=model.best_iteration)
    train_auc = float(roc_auc_score(y_train, _y_train_proba))
    val_auc = float(roc_auc_score(y_val, _y_val_proba))

    importance_df = (
        pd.DataFrame(
            {
                "feature": list(X_train.columns),
                "importance": model.feature_importance(importance_type="gain"),
            }
        )
        .sort_values("importance", ascending=False)
        .reset_index(drop=True)
    )
    return model, train_auc, val_auc, importance_df

def _xgb_fit(
    X_train: pd.DataFrame,
    y_train: pd.Series,
    X_val: pd.DataFrame,
    y_val: pd.Series,
    params: dict[str, Any] | None = None,
    num_boost_round: int = config.XGB_NUM_BOOST_ROUND,
    early_stopping_rounds: int = config.XGB_EARLY_STOPPING_ROUNDS,
    **kwargs: Any,
) -> tuple[Any, float, float, pd.DataFrame | None]:
    """Fit an XGBoost model and return (model, train_auc, val_auc, importance)."""
    import xgboost as xgb

    params = {**config.XGB_PARAMS, **(params or {})}
    early_stop = xgb.callback.EarlyStopping(
        rounds=early_stopping_rounds,
        save_best=True,
        metric_name="auc",
        data_name="eval",
    )

    model = xgb.train(
        params,
        xgb.DMatrix(X_train, label=y_train),
        num_boost_round=num_boost_round,
        evals=[(xgb.DMatrix(X_val, label=y_val), "eval")],
        callbacks=[early_stop],
        verbose_eval=False,
        **kwargs,
    )

    _y_train_proba = model.predict(xgb.DMatrix(X_train))
    _y_val_proba = model.predict(xgb.DMatrix(X_val))
    train_auc = float(roc_auc_score(y_train, _y_train_proba))
    val_auc = float(roc_auc_score(y_val, _y_val_proba))

    # XGBoost get_score returns a dict; map back to full feature list
    score_dict = model.get_score(importance_type="gain")
    importance_df = (
        pd.DataFrame(
            {
                "feature": list(X_train.columns),
                "importance": [score_dict.get(f, 0.0) for f in X_train.columns],
            }
        )
        .sort_values("importance", ascending=False)
        .reset_index(drop=True)
    )
    return model, train_auc, val_auc, importance_df

def _cb_fit(
    X_train: pd.DataFrame,
    y_train: pd.Series,
    X_val: pd.DataFrame,
    y_val: pd.Series,
    params: dict[str, Any] | None = None,
    early_stopping_rounds: int = config.CB_EARLY_STOPPING_ROUNDS,
    **kwargs: Any,
) -> tuple[Any, float, float, pd.DataFrame | None]:
    """Fit a CatBoost model and return (model, train_auc, val_auc, importance)."""
    from catboost import CatBoostClassifier, Pool

    params = {**config.CB_PARAMS, **(params or {})}

    # Identify categorical features for CatBoost natively
    _cat_features = list(
        X_train.select_dtypes(include=["category", "object"]).columns
    )

    train_pool = Pool(X_train, label=y_train, cat_features=_cat_features)
    val_pool = Pool(X_val, label=y_val, cat_features=_cat_features)

    model = CatBoostClassifier(**params)
    model.fit(
        train_pool,
        eval_set=val_pool,
        early_stopping_rounds=early_stopping_rounds,
        **kwargs,
    )

    _y_train_proba = model.predict_proba(X_train)[:, 1]
    _y_val_proba = model.predict_proba(X_val)[:, 1]
    train_auc = float(roc_auc_score(y_train, _y_train_proba))
    val_auc = float(roc_auc_score(y_val, _y_val_proba))

    importance_df = (
        pd.DataFrame(
            {
                "feature": list(X_train.columns),
                "importance": model.feature_importances_,
            }
        )
        .sort_values("importance", ascending=False)
        .reset_index(drop=True)
    )
    return model, train_auc, val_auc, importance_df

#: Mapping of ModelBackend -> internal fit function.
_BACKEND_FIT_MAP: dict[ModelBackend, Any] = {
    ModelBackend.LIGHTGBM: _lgb_fit,
    ModelBackend.XGBOOST: _xgb_fit,
    ModelBackend.CATBOOST: _cb_fit,
}

def train_model(
    df: pd.DataFrame,
    backend: ModelBackend = ModelBackend.LIGHTGBM,
    params: dict[str, Any] | None = None,
    num_boost_round: int | None = None,
    early_stopping_rounds: int | None = None,
    **kwargs: Any,
) -> ModelResult:
    """Train a single gradient-boosting model and return a ``ModelResult``.

    Parameters
    ----------
    df:
        Input DataFrame with target column and feature columns.
    backend:
        Which model backend to use (LightGBM, XGBoost, or CatBoost).
    params:
        Optional parameter overrides merged on top of the backend's defaults
        from ``config.py``.
    num_boost_round:
        Max boosting iterations (defaults per backend in ``config.py``).
    early_stopping_rounds:
        Early-stopping patience (defaults per backend in ``config.py``).
    **kwargs:
        Additional keyword arguments forwarded to the backend's fit/train call.

    Returns
    -------
    ModelResult
        Container with trained model, evaluation metrics, and importance.

    Raises
    ------
    ValueError
        If ``backend`` is not a recognised ``ModelBackend``.

    Examples
    --------
    >>> import pandas as pd, numpy as np
    >>> rng = np.random.default_rng(42)
    >>> n = 200
    >>> df = pd.DataFrame({"isFraud": rng.integers(0, 2, n),
    ...                    "f1": rng.standard_normal(n)})
    >>> result = train_model(df, ModelBackend.LIGHTGBM, num_boost_round=10)
    >>> result.backend
    <ModelBackend.LIGHTGBM: 'lightgbm'>
    >>> isinstance(result.val_auc, float)
    True
    """
    if backend not in _BACKEND_FIT_MAP:
        msg = f"Unknown backend: {backend!r}. Choose from {list(_BACKEND_FIT_MAP)}"
        raise ValueError(msg)

    # Map per-backend defaults when caller omits optional arguments.
    _boost_map: dict[str, tuple[int, int]] = {
        "lightgbm": (config.LGBM_NUM_BOOST_ROUND, config.LGBM_EARLY_STOPPING_ROUNDS),
        "xgboost": (config.XGB_NUM_BOOST_ROUND, config.XGB_EARLY_STOPPING_ROUNDS),
        "catboost": (config.LGBM_NUM_BOOST_ROUND, config.CB_EARLY_STOPPING_ROUNDS),
    }
    _num_boost = num_boost_round or _boost_map[backend.value][0]
    _early_stop = early_stopping_rounds or _boost_map[backend.value][1]

    split = make_train_val_split(df)
    fit_fn = _BACKEND_FIT_MAP[backend]

    start = time.perf_counter()
    model, train_auc, val_auc, importance = fit_fn(
        split.X_train,
        split.y_train,
        split.X_val,
        split.y_val,
        params=params,
        num_boost_round=_num_boost,
        early_stopping_rounds=_early_stop,
        **kwargs,
    )
    elapsed = time.perf_counter() - start

    return ModelResult(
        backend=backend,
        model=model,
        train_auc=train_auc,
        val_auc=val_auc,
        feature_importance=importance,
        training_time=elapsed,
    )

def train_all_models(
    df: pd.DataFrame,
    backends: list[ModelBackend] | None = None,
    params: dict[ModelBackend, dict[str, Any]] | None = None,
    num_boost_round: int | None = None,
    early_stopping_rounds: int | None = None,
) -> dict[ModelBackend, ModelResult]:
    """Train multiple model backends and return a dictionary of results.

    Parameters
    ----------
    df:
        Input DataFrame with target column and feature columns.
    backends:
        List of backends to train. Defaults to all available backends.
    params:
        Optional per-backend parameter overrides keyed by ``ModelBackend``.
    num_boost_round:
        Shared max boosting iterations for all backends.
    early_stopping_rounds:
        Shared early-stopping patience for all backends.

    Returns
    -------
    dict[ModelBackend, ModelResult]
        Mapping from backend to its training result.

    Examples
    --------
    >>> import pandas as pd, numpy as np
    >>> rng = np.random.default_rng(42)
    >>> n = 200
    >>> df = pd.DataFrame({"isFraud": rng.integers(0, 2, n),
    ...                    "f1": rng.standard_normal(n)})
    >>> results = train_all_models(df, backends=[ModelBackend.LIGHTGBM],
    ...                            num_boost_round=10)
    >>> ModelBackend.LIGHTGBM in results
    True
    """
    backends = backends or list(ModelBackend)
    params = params or {}
    results: dict[ModelBackend, ModelResult] = {}
    for backend in backends:
        _params = params.get(backend)
        results[backend] = train_model(
            df,
            backend=backend,
            params=_params,
            num_boost_round=num_boost_round,
            early_stopping_rounds=early_stopping_rounds,
        )
    return results

def cross_validate_model(
    df: pd.DataFrame,
    backend: ModelBackend = ModelBackend.LIGHTGBM,
    cv_folds: int = config.CV_FOLDS,
    params: dict[str, Any] | None = None,
    random_state: int = config.RANDOM_STATE,
    **kwargs: Any,
) -> CrossValidationResult:
    """Perform k-fold cross-validation for a given model backend.

    Parameters
    ----------
    df:
        Input DataFrame with target column and feature columns.
    backend:
        Which model backend to use.
    cv_folds:
        Number of cross-validation folds.
    params:
        Optional parameter overrides.
    random_state:
        Seed for reproducible fold splitting.
    **kwargs:
        Additional keyword arguments forwarded to the backend's fit function.

    Returns
    -------
    CrossValidationResult
        Container with per-fold scores, mean, std, and training time.

    Examples
    --------
    >>> import pandas as pd, numpy as np
    >>> rng = np.random.default_rng(42)
    >>> n = 200
    >>> df = pd.DataFrame({"isFraud": rng.integers(0, 2, n),
    ...                    "f1": rng.standard_normal(n)})
    >>> cv = cross_validate_model(df, ModelBackend.LIGHTGBM, cv_folds=3,
    ...                           num_boost_round=10)
    >>> cv.mean_auc > 0.0
    True
    >>> len(cv.fold_scores) == 3
    True
    """
    from sklearn.model_selection import StratifiedKFold

    feature_cols = select_feature_columns(df)
    X = df[feature_cols]  # noqa: N806
    y = df[config.TARGET_COLUMN]

    skf = StratifiedKFold(n_splits=cv_folds, shuffle=True, random_state=random_state)
    fold_scores: list[tuple[int, float]] = []

    start = time.perf_counter()
    for fold_idx, (train_idx, val_idx) in enumerate(skf.split(X, y)):
        X_train, X_val = X.iloc[train_idx], X.iloc[val_idx]
        y_train, y_val = y.iloc[train_idx], y.iloc[val_idx]

        result = train_model(
            df.iloc[train_idx].assign(**{config.TARGET_COLUMN: y_train}),
            backend=backend,
            params=params,
            **kwargs,
        )
        fold_scores.append((fold_idx, result.val_auc))
    elapsed = time.perf_counter() - start

    auc_values = [score for _, score in fold_scores]
    return CrossValidationResult(
        backend=backend,
        fold_scores=fold_scores,
        mean_auc=float(pd.Series(auc_values).mean()),
        std_auc=float(pd.Series(auc_values).std()),
        training_time=elapsed,
    )
