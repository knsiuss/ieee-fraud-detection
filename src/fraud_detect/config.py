"""Project-wide configuration constants.

Centralising paths, column groups and hyperparameters here keeps notebooks
and scripts free of magic numbers and makes the pipeline reproducible across
machines via the ``FRAUD_DETECT_DATA_ROOT`` environment variable.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Final

# Paths
#: Override the data root via env var when running on a different machine.
DATA_ROOT: Final[Path] = Path(
    os.getenv("FRAUD_DETECT_DATA_ROOT", Path(__file__).resolve().parents[2] / "data")
)

RAW_DIR: Final[Path] = DATA_ROOT / "raw"
INTERIM_DIR: Final[Path] = DATA_ROOT / "interim"
PROCESSED_DIR: Final[Path] = DATA_ROOT / "processed"
METADATA_DIR: Final[Path] = DATA_ROOT / "metadata"

#: Canonical merged training table produced by notebook 01.
MERGED_TRAIN_PATH: Final[Path] = INTERIM_DIR / "train_merged.parquet"

#: Enriched training table produced by notebook 07 (feature engineering).
PROCESSED_TRAIN_PATH: Final[Path] = PROCESSED_DIR / "train_features.parquet"

#: Metadata artefacts written by the EDA notebooks.
MISSING_VALUE_REPORT_PATH: Final[Path] = METADATA_DIR / "missing_value_report.csv"
REDUNDANT_FEATURE_PATH: Final[Path] = METADATA_DIR / "redundant_feature.csv"
FEATURE_IMPORTANCE_PATH: Final[Path] = METADATA_DIR / "feature_importance.csv"

#: Directory for trained model artefacts (pickle / joblib).
MODEL_DIR: Final[Path] = DATA_ROOT / "models"

# Schema

TARGET_COLUMN: Final[str] = "isFraud"
TRANSACTION_ID_COLUMN: Final[str] = "TransactionID"
TRANSACTION_DT_COLUMN: Final[str] = "TransactionDT"

#: Columns that must never be used as model inputs.
EXCLUDE_COLUMNS: Final[tuple[str, ...]] = (
    TRANSACTION_ID_COLUMN,
    TARGET_COLUMN,
    TRANSACTION_DT_COLUMN,
)

#: Logical groupings of raw IEEE-CIS columns. Used by EDA and reporting.
COLUMN_GROUPS: Final[dict[str, tuple[str, ...]]] = {
    "Transaction": ("TransactionID", "TransactionDT", "TransactionAmt", "ProductCD"),
    "Target": ("isFraud",),
    "Card": tuple(f"card{i}" for i in range(1, 7)),
    "Address": ("addr1", "addr2", "dist1", "dist2"),
    "Email": ("P_emaildomain", "R_emaildomain"),
    "Count": tuple(f"C{i}" for i in range(1, 15)),
    "TimeDelta": tuple(f"D{i}" for i in range(1, 16)),
    "Match": tuple(f"M{i}" for i in range(1, 10)),
    "Vesta": tuple(f"V{i}" for i in range(1, 340)),
    "Identity": tuple(f"id_{str(i).zfill(2)}" for i in range(1, 39)),
    "Device": ("DeviceType", "DeviceInfo"),
}

# Feature engineering

#: Reference start date used to convert ``TransactionDT`` (seconds) to a
#: calendar date. Derived from the IEEE-CIS competition's known anchor.
TRANSACTION_DT_START: Final[str] = "2017-11-30"

#: Free / consumer email domains used to build the ``is_free_email`` feature.
FREE_EMAIL_DOMAINS: Final[tuple[str, ...]] = (
    "gmail.com",
    "yahoo.com",
    "hotmail.com",
    "outlook.com",
    "aol.com",
    "icloud.com",
)

# Modelling

RANDOM_STATE: Final[int] = 42
VALIDATION_SIZE: Final[float] = 0.2

#: Default LightGBM parameters used for fast feature-importance estimation.
LGBM_BASE_PARAMS: Final[dict[str, float | int | str]] = {
    "objective": "binary",
    "metric": "auc",
    "num_leaves": 31,
    "learning_rate": 0.1,
    "feature_fraction": 0.8,
    "bagging_fraction": 0.8,
    "bagging_freq": 5,
    "verbose": -1,
}
LGBM_NUM_BOOST_ROUND: Final[int] = 200
LGBM_EARLY_STOPPING_ROUNDS: Final[int] = 30

# Modelling — cross-validation & training

CV_FOLDS: Final[int] = 5
N_TRIALS: Final[int] = 100  # default Optuna trials

# Optuna tuning — search spaces

OPTUNA_STORAGE_PATH: Final[Path] = METADATA_DIR / "optuna_study.db"
OPTUNA_N_TRIALS: Final[int] = N_TRIALS

LGBM_TUNING_SPACE: Final[dict[str, dict[str, float | int | bool]]] = {
    "num_leaves": {"low": 16, "high": 256},
    "learning_rate": {"low": 0.01, "high": 0.3, "log": True},
    "min_child_samples": {"low": 5, "high": 100},
    "subsample": {"low": 0.5, "high": 1.0},
    "colsample_bytree": {"low": 0.5, "high": 1.0},
    "reg_alpha": {"low": 1e-8, "high": 10.0, "log": True},
    "reg_lambda": {"low": 1e-8, "high": 10.0, "log": True},
}

XGB_TUNING_SPACE: Final[dict[str, dict[str, float | int | bool]]] = {
    "max_depth": {"low": 3, "high": 12},
    "learning_rate": {"low": 0.01, "high": 0.3, "log": True},
    "subsample": {"low": 0.5, "high": 1.0},
    "colsample_bytree": {"low": 0.5, "high": 1.0},
    "min_child_weight": {"low": 1, "high": 50, "log": True},
    "reg_alpha": {"low": 1e-8, "high": 10.0, "log": True},
    "reg_lambda": {"low": 1e-8, "high": 10.0, "log": True},
    "gamma": {"low": 0.0, "high": 5.0},
}

CB_TUNING_SPACE: Final[dict[str, dict[str, float | int | bool]]] = {
    "depth": {"low": 4, "high": 10},
    "learning_rate": {"low": 0.01, "high": 0.3, "log": True},
    "l2_leaf_reg": {"low": 1.0, "high": 10.0, "log": True},
    "min_data_in_leaf": {"low": 1, "high": 50},
    "random_strength": {"low": 0.0, "high": 10.0},
    "bagging_temperature": {"low": 0.0, "high": 10.0},
}

BACKEND_TUNING_SPACE_MAP: Final[dict[str, str]] = {
    "lightgbm": "LGBM_TUNING_SPACE",
    "xgboost": "XGB_TUNING_SPACE",
    "catboost": "CB_TUNING_SPACE",
}

# LightGBM base parameters

LGBM_PARAMS: Final[dict[str, float | int | str]] = {
    "objective": "binary",
    "metric": "auc",
    "num_leaves": 31,
    "learning_rate": 0.1,
    "feature_fraction": 0.8,
    "bagging_fraction": 0.8,
    "bagging_freq": 5,
    "min_child_samples": 20,
    "reg_alpha": 0.0,
    "reg_lambda": 0.0,
    "verbose": -1,
    "random_state": RANDOM_STATE,
}
LGBM_NUM_BOOST_ROUND: Final[int] = 500
LGBM_EARLY_STOPPING_ROUNDS: Final[int] = 50

# XGBoost base parameters

XGB_PARAMS: Final[dict[str, float | int | str]] = {
    "objective": "binary:logistic",
    "eval_metric": "auc",
    "max_depth": 6,
    "learning_rate": 0.1,
    "subsample": 0.8,
    "colsample_bytree": 0.8,
    "min_child_weight": 1,
    "reg_alpha": 0.0,
    "reg_lambda": 1.0,
    "verbosity": 0,
    "random_state": RANDOM_STATE,
}
XGB_NUM_BOOST_ROUND: Final[int] = 500
XGB_EARLY_STOPPING_ROUNDS: Final[int] = 50

# CatBoost base parameters

CB_PARAMS: Final[dict[str, float | int | str]] = {
    "loss_function": "Logloss",
    "eval_metric": "AUC",
    "iterations": 500,
    "learning_rate": 0.1,
    "depth": 6,
    "l2_leaf_reg": 3.0,
    "random_seed": RANDOM_STATE,
    "verbose": False,
    "allow_writing_files": False,
}
CB_EARLY_STOPPING_ROUNDS: Final[int] = 50

# Missing-value strategy thresholds

DROP_THRESHOLD: Final[float] = 0.95
INDICATOR_ONLY_THRESHOLD: Final[float] = 0.75
MODERATE_THRESHOLD: Final[float] = 0.10
