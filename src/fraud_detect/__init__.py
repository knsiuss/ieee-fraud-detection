"""FraudDetection — IEEE-CIS fraud detection toolkit.

Utilities for data loading, feature engineering, visualisation and modelling
used across the project's
notebooks. Importing the top-level package gives access to the public API:

>>> from fraud_detect import config, data, features, viz, models, io, tuning

The modules are intentionally side-effect free at import time; matplotlib
styles and pandas display options are applied lazily through
:func:`viz.configure_style`.
"""

from importlib.metadata import PackageNotFoundError, version

from fraud_detect._exceptions import (
    FraudDetectError,
    InvalidDataError,
    MissingArtefactError,
)
from fraud_detect.config import (
    DATA_ROOT,
    RANDOM_STATE,
    TARGET_COLUMN,
    TRANSACTION_DT_COLUMN,
    TRANSACTION_ID_COLUMN,
    VALIDATION_SIZE,
)
from fraud_detect.data import (
    categorize_missing,
    compute_missing_report,
    get_imputation_strategy,
    load_merged_train,
    reduce_mem_usage,
)
from fraud_detect.error_analysis import (
    ErrorProfile,
    compute_error_profile,
    confusion_by_amount_bins,
    feature_distribution_shift,
    segment_errors,
    top_false_negatives,
    top_false_positives,
)
from fraud_detect.ensemble import (
    EnsembleConfig,
    EnsembleStrategy,
    build_stacking_ensemble,
    build_voting_ensemble,
    evaluate_ensemble,
)
from fraud_detect.evaluation import (
    EvaluationReport,
    compare_models,
    compute_evaluation,
    find_best_threshold,
    mcnemar_test,
)
from fraud_detect.features import (
    add_amount_features,
    add_card_aggregations,
    add_email_features,
    add_identity_features,
    add_time_features,
    build_all_features,
)
from fraud_detect.io import (
    load_train_features,
    read_csv,
    read_parquet,
    write_csv,
    write_parquet,
)
from fraud_detect.models import (
    CrossValidationResult,
    ModelBackend,
    ModelResult,
    SplitResult,
    build_logistic_pipeline,
    compute_lightgbm_importance,
    cross_validate_model,
    evaluate_classifier,
    make_train_val_split,
    select_feature_columns,
    train_all_models,
    train_model,
)
from fraud_detect.tuning import (
    build_search_space,
    load_best_params,
    save_best_params,
    tune_model,
)
from fraud_detect.viz import (
    configure_style,
    plot_fraud_rate_by_category,
    plot_target_correlation,
    plot_target_distribution,
    save_figure,
)

try:
    __version__ = version("fraud_detect")
except PackageNotFoundError:  # pragma: no cover - editable install fallback
    __version__ = "0.1.0"

__all__ = [
    "__version__",
    # Exceptions
    "FraudDetectError",
    "InvalidDataError",
    "MissingArtefactError",
    # Data
    "categorize_missing",
    "reduce_mem_usage",
    "get_imputation_strategy",
    "compute_missing_report",
    "load_merged_train",
    # Features
    "add_identity_features",
    "add_time_features",
    "add_amount_features",
    "add_email_features",
    "add_card_aggregations",
    "build_all_features",
    # I/O
    "load_train_features",
    "read_parquet",
    "write_parquet",
    "read_csv",
    "write_csv",
    # Models
    "SplitResult",
    "ModelBackend",
    "ModelResult",
    "CrossValidationResult",
    "select_feature_columns",
    "make_train_val_split",
    "build_logistic_pipeline",
    "evaluate_classifier",
    "compute_lightgbm_importance",
    "train_model",
    "train_all_models",
    "cross_validate_model",
    # Error Analysis
    "ErrorProfile",
    "compute_error_profile",
    "segment_errors",
    "feature_distribution_shift",
    "top_false_positives",
    "top_false_negatives",
    "confusion_by_amount_bins",
    # Ensemble
    "EnsembleStrategy",
    "EnsembleConfig",
    "build_voting_ensemble",
    "build_stacking_ensemble",
    "evaluate_ensemble",
    # Evaluation
    "EvaluationReport",
    "compute_evaluation",
    "find_best_threshold",
    "compare_models",
    "mcnemar_test",
    # Viz
    "configure_style",
    "plot_target_distribution",
    "plot_fraud_rate_by_category",
    "plot_target_correlation",
    "save_figure",
    "plot_roc_curves",
    "plot_pr_curves",
    "plot_confusion_matrix",
    "plot_metrics_comparison",
    "plot_threshold_analysis",
    "plot_cumulative_gain",
    "plot_error_rate_by_category",
    "plot_feature_shift_comparison",
    "plot_confusion_by_amount",
    "plot_false_positive_examples",
    # Tuning
    "build_search_space",
    "load_best_params",
    "save_best_params",
    "tune_model",
    # Config
    "DATA_ROOT",
    "TARGET_COLUMN",
    "TRANSACTION_ID_COLUMN",
    "TRANSACTION_DT_COLUMN",
    "RANDOM_STATE",
    "VALIDATION_SIZE",
]
