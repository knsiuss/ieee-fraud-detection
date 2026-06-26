"""Plotting helpers shared across EDA notebooks.

All functions are lazy about matplotlib state: they create their own
``Figure``/``Axes`` and return them so callers can further customise or
save. Call :func:`configure_style` once at the top of a notebook to apply
the project's visual defaults.
"""

from __future__ import annotations

import logging
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

from . import config

_APPLIED_STYLE = False
_logger = logging.getLogger(__name__)

def configure_style() -> None:
    """Apply the project's matplotlib/seaborn defaults (idempotent)."""
    global _APPLIED_STYLE  # noqa: PLW0603
    if _APPLIED_STYLE:
        return
    plt.style.use("seaborn-v0_8-whitegrid")
    sns.set_palette("husl")
    pd.set_option("display.max_columns", 100)
    _APPLIED_STYLE = True

def plot_target_distribution(
    y: pd.Series,
    ax: plt.Axes | None = None,
) -> tuple[plt.Figure, plt.Axes]:
    """Bar chart of the binary target distribution with counts on bars."""
    configure_style()
    counts = y.value_counts().sort_index()
    fig, ax = plt.subplots(figsize=(6, 4)) if ax is None else (ax.figure, ax)
    bars = ax.bar(["Not Fraud (0)", "Fraud (1)"], counts.values, color=["#4c72b0", "#c44e52"])
    for bar, count in zip(bars, counts.values, strict=True):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height(),
            f"{count:,}\n({count / len(y) * 100:.1f}%)",
            ha="center",
            va="bottom",
            fontsize=9,
        )
    ax.set_ylabel("Number of transactions")
    ax.set_title("Target distribution")
    return fig, ax

def plot_fraud_rate_by_category(
    df: pd.DataFrame,
    cat_col: str,
    target: str = config.TARGET_COLUMN,
    top_n: int | None = None,
    ax: plt.Axes | None = None,
) -> tuple[plt.Figure, plt.Axes]:
    """Horizontal bar chart of fraud rate per category level."""
    configure_style()
    rate = df.groupby(cat_col)[target].mean().sort_values(ascending=False)
    if top_n is not None:
        rate = rate.head(top_n)
    fig, ax = plt.subplots(figsize=(8, max(4, len(rate) * 0.3))) if ax is None else (ax.figure, ax)
    ax.barh(rate.index.astype(str), rate.values, color="#c44e52")
    ax.set_xlabel("Fraud rate")
    ax.set_title(f"Fraud rate by {cat_col}")
    ax.invert_yaxis()
    return fig, ax

def plot_target_correlation(
    df: pd.DataFrame,
    target: str = config.TARGET_COLUMN,
    top_n: int = 20,
    ax: plt.Axes | None = None,
) -> tuple[plt.Figure, plt.Axes]:
    """Horizontal bar chart of the top-N numeric features by absolute correlation with target."""
    configure_style()
    numeric = df.select_dtypes(include=[np.number])
    if target not in numeric.columns:
        raise ValueError(f"Target column {target!r} is not numeric.")
    corrs = numeric.corr()[target].drop(target).abs().sort_values(ascending=False).head(top_n)
    fig, ax = plt.subplots(figsize=(8, max(4, len(corrs) * 0.3))) if ax is None else (ax.figure, ax)
    ax.barh(corrs.index.astype(str), corrs.values, color="#55a868")
    ax.set_xlabel("|Pearson correlation|")
    ax.set_title(f"Top {top_n} features by |corr| with {target}")
    ax.invert_yaxis()
    return fig, ax

def save_figure(fig: plt.Figure, path: Path, dpi: int = 150) -> None:
    """Save a figure to disk, creating parent directories as needed.

    Parameters
    ----------
    fig:
        Matplotlib figure to save.
    path:
        Destination path (parent dirs are created automatically).
    dpi:
        Resolution in dots per inch. Default 150 is suitable for reports.

    Examples
    --------
    >>> import matplotlib.pyplot as plt
    >>> fig, ax = plt.subplots()
    >>> _ = ax.plot([1, 2], [3, 4])
    >>> save_figure(fig, Path("/tmp/my_figure.png"))  # doctest: +SKIP
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=dpi, bbox_inches="tight")
    _logger.info("Figure saved to %s (dpi=%d)", path, dpi)

# Phase 4 — Model Evaluation Plots

def plot_roc_curves(
    y_true_dict: dict[str, pd.Series | np.ndarray],
    y_pred_dict: dict[str, np.ndarray],
    figsize: tuple[int, int] = (8, 7),
    ax: plt.Axes | None = None,
) -> tuple[plt.Figure, plt.Axes]:
    """Plot ROC curves for multiple models on a single axes.

    Parameters
    ----------
    y_true_dict:
        Mapping of model name → ground-truth labels.
    y_pred_dict:
        Mapping of model name → predicted probabilities.
    figsize:
        Figure dimensions.
    ax:
        Optional existing axes to plot on.

    Returns
    -------
    tuple[Figure, Axes]

    Examples
    --------
    >>> import numpy as np, pandas as pd
    >>> rng = np.random.default_rng(42)
    >>> y = pd.Series(rng.integers(0, 2, 100))
    >>> p = rng.uniform(0, 1, 100)
    >>> fig, ax = plot_roc_curves({"A": y}, {"A": p})
    >>> isinstance(fig, plt.Figure)
    True
    """
    from sklearn.metrics import roc_auc_score, roc_curve

    configure_style()
    fig, ax = plt.subplots(figsize=figsize) if ax is None else (ax.figure, ax)

    colors = ["#4c72b0", "#dd8452", "#55a868", "#c44e52", "#8172b3", "#937860"]
    for idx, (name, y_true) in enumerate(sorted(y_true_dict.items())):
        y_pred = y_pred_dict[name]
        fpr, tpr, _ = roc_curve(y_true, y_pred)
        auc = roc_auc_score(y_true, y_pred)
        color = colors[idx % len(colors)]
        ax.plot(fpr, tpr, label=f"{name} (AUC = {auc:.4f})", color=color, linewidth=1.5)

    ax.plot([0, 1], [0, 1], "k--", alpha=0.4, label="Random (AUC = 0.5)")
    ax.set_xlabel("False Positive Rate")
    ax.set_ylabel("True Positive Rate")
    ax.set_title("ROC Curves — Comparison")
    ax.legend(loc="lower right")
    ax.set_xlim(-0.02, 1.02)
    ax.set_ylim(-0.02, 1.02)
    return fig, ax

def plot_pr_curves(
    y_true_dict: dict[str, pd.Series | np.ndarray],
    y_pred_dict: dict[str, np.ndarray],
    figsize: tuple[int, int] = (8, 7),
    ax: plt.Axes | None = None,
) -> tuple[plt.Figure, plt.Axes]:
    """Plot Precision-Recall curves for multiple models on a single axes.

    Especially useful for imbalanced datasets where ROC curves can be
    overly optimistic.

    Parameters
    ----------
    y_true_dict:
        Mapping of model name → ground-truth labels.
    y_pred_dict:
        Mapping of model name → predicted probabilities.
    figsize:
        Figure dimensions.
    ax:
        Optional existing axes to plot on.

    Returns
    -------
    tuple[Figure, Axes]
    """
    from sklearn.metrics import average_precision_score, precision_recall_curve

    configure_style()
    fig, ax = plt.subplots(figsize=figsize) if ax is None else (ax.figure, ax)

    colors = ["#4c72b0", "#dd8452", "#55a868", "#c44e52", "#8172b3", "#937860"]
    for idx, (name, y_true) in enumerate(sorted(y_true_dict.items())):
        y_pred = y_pred_dict[name]
        precision, recall, _ = precision_recall_curve(y_true, y_pred)
        ap = average_precision_score(y_true, y_pred)
        color = colors[idx % len(colors)]
        ax.plot(recall, precision, label=f"{name} (AP = {ap:.4f})", color=color, linewidth=1.5)

    # No-skill line: positive ratio
    pos_ratio = sum(y_true_dict.values()).sum() / sum(len(v) for v in y_true_dict.values())
    ax.axhline(y=pos_ratio, color="gray", linestyle="--", alpha=0.4, label=f"No-skill ({pos_ratio:.3f})")
    ax.set_xlabel("Recall")
    ax.set_ylabel("Precision")
    ax.set_title("Precision-Recall Curves — Comparison")
    ax.legend(loc="lower left")
    ax.set_xlim(-0.02, 1.02)
    ax.set_ylim(-0.02, 1.02)
    return fig, ax

def plot_confusion_matrix(
    y_true: pd.Series | np.ndarray,
    y_pred: np.ndarray,
    labels: tuple[str, str] = ("Not Fraud", "Fraud"),
    normalize: bool = True,
    figsize: tuple[int, int] = (5, 4),
    ax: plt.Axes | None = None,
) -> tuple[plt.Figure, plt.Axes]:
    """Plot a (normalised) confusion matrix as a heatmap.

    Parameters
    ----------
    y_true:
        Ground-truth binary labels.
    y_pred:
        Binary predictions.
    labels:
        Display labels for classes 0 and 1.
    normalize:
        If True, show percentages instead of raw counts.
    figsize:
        Figure dimensions.
    ax:
        Optional existing axes to plot on.

    Returns
    -------
    tuple[Figure, Axes]
    """
    from sklearn.metrics import ConfusionMatrixDisplay

    configure_style()
    fig, ax = plt.subplots(figsize=figsize) if ax is None else (ax.figure, ax)

    disp = ConfusionMatrixDisplay.from_predictions(
        y_true,
        y_pred,
        display_labels=labels,
        normalize="true" if normalize else None,
        cmap="Blues",
        ax=ax,
        colorbar=False,
        values_format=".2f" if normalize else "d",
    )
    ax.set_title("Confusion Matrix" + (" (normalised)" if normalize else ""))
    return fig, ax

def plot_metrics_comparison(
    comparison_df: pd.DataFrame,
    metric_cols: list[str] | None = None,
    figsize: tuple[int, int] = (10, 6),
    ax: plt.Axes | None = None,
) -> tuple[plt.Figure, plt.Axes]:
    """Grouped bar chart comparing multiple models across metrics.

    Parameters
    ----------
    comparison_df:
        DataFrame with a ``model`` column and metric columns. Typically the
        output of :func:`fraud_detect.evaluation.compare_models`.
    metric_cols:
        Columns to plot. Defaults to ``auc, f1, precision, recall``.
    figsize:
        Figure dimensions.
    ax:
        Optional existing axes to plot on.

    Returns
    -------
    tuple[Figure, Axes]
    """
    configure_style()
    metric_cols = metric_cols or ["auc", "f1", "precision", "recall"]
    fig, ax = plt.subplots(figsize=figsize) if ax is None else (ax.figure, ax)

    x_pos = np.arange(len(comparison_df))
    n_metrics = len(metric_cols)
    width = 0.8 / n_metrics
    colors = ["#4c72b0", "#dd8452", "#55a868", "#c44e52"]

    for i, metric in enumerate(metric_cols):
        if metric in comparison_df.columns:
            offset = (i - n_metrics / 2 + 0.5) * width
            ax.bar(
                x_pos + offset,
                comparison_df[metric].values,
                width,
                label=metric.upper(),
                color=colors[i % len(colors)],
                alpha=0.85,
            )

    ax.set_xticks(x_pos)
    ax.set_xticklabels(comparison_df["model"].values, rotation=25, ha="right")
    ax.set_ylabel("Score")
    ax.set_title("Model Comparison — Metrics Overview")
    ax.legend(loc="lower right")
    ax.set_ylim(0, 1.05)
    plt.tight_layout()
    return fig, ax

def plot_threshold_analysis(
    y_true: pd.Series | np.ndarray,
    y_pred_proba: np.ndarray,
    n_thresholds: int = 200,
    figsize: tuple[int, int] = (10, 5),
    ax: plt.Axes | None = None,
) -> tuple[plt.Figure, plt.Axes]:
    """Plot precision, recall, F1, and Youden's J across decision thresholds.

    Parameters
    ----------
    y_true:
        Ground-truth binary labels.
    y_pred_proba:
        Predicted probabilities for the positive class.
    n_thresholds:
        Number of candidate thresholds.
    figsize:
        Figure dimensions.
    ax:
        Optional existing axes to plot on.

    Returns
    -------
    tuple[Figure, Axes]
    """
    from sklearn.metrics import f1_score, precision_score, recall_score

    configure_style()
    fig, ax = plt.subplots(figsize=figsize) if ax is None else (ax.figure, ax)

    thresholds = np.linspace(0.01, 0.99, n_thresholds)
    precisions, recalls, f1s, youdens = [], [], [], []

    for thresh in thresholds:
        y_pred = (y_pred_proba >= thresh).astype(int)
        precisions.append(precision_score(y_true, y_pred, zero_division=0))
        recalls.append(recall_score(y_true, y_pred, zero_division=0))
        f1s.append(f1_score(y_true, y_pred, zero_division=0))
        # Youden's J
        tn = np.sum((y_true == 0) & (y_pred == 0))
        fp = np.sum((y_true == 0) & (y_pred == 1))
        fn = np.sum((y_true == 1) & (y_pred == 0))
        tp = np.sum((y_true == 1) & (y_pred == 1))
        tpr = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        tnr = tn / (tn + fp) if (tn + fp) > 0 else 0.0
        youdens.append(tpr + tnr - 1)

    idx_best = int(np.argmax(youdens))

    ax.plot(thresholds, precisions, label="Precision", alpha=0.7)
    ax.plot(thresholds, recalls, label="Recall", alpha=0.7)
    ax.plot(thresholds, f1s, label="F1", linewidth=2)
    ax.plot(thresholds, youdens, label="Youden's J", linestyle="--", alpha=0.7)
    ax.axvline(x=thresholds[idx_best], color="red", linestyle=":", alpha=0.6,
               label=f"Best threshold = {thresholds[idx_best]:.3f}")

    ax.set_xlabel("Threshold")
    ax.set_ylabel("Score")
    ax.set_title("Threshold Analysis — Precision, Recall, F1, Youden's J")
    ax.legend(loc="best")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1.05)
    return fig, ax

def plot_cumulative_gain(
    y_true: pd.Series | np.ndarray,
    y_pred_proba: np.ndarray,
    figsize: tuple[int, int] = (8, 6),
    ax: plt.Axes | None = None,
) -> tuple[plt.Figure, plt.Axes]:
    """Plot a cumulative gain (lift) chart.

    Shows what fraction of positive cases are captured by labelling the top
    *x*% of predictions (sorted by predicted probability).

    Parameters
    ----------
    y_true:
        Ground-truth binary labels.
    y_pred_proba:
        Predicted probabilities for the positive class.
    figsize:
        Figure dimensions.
    ax:
        Optional existing axes to plot on.

    Returns
    -------
    tuple[Figure, Axes]
    """
    configure_style()
    fig, ax = plt.subplots(figsize=figsize) if ax is None else (ax.figure, ax)

    # Sort by predicted probability descending
    order = np.argsort(y_pred_proba)[::-1]
    y_sorted = np.asarray(y_true)[order]

    # Cumulative gains
    total_positives = y_sorted.sum()
    cum_positives = np.cumsum(y_sorted)
    gains = cum_positives / total_positives if total_positives > 0 else cum_positives
    population_pct = np.arange(1, len(y_sorted) + 1) / len(y_sorted)

    ax.plot(population_pct, gains, label="Model", linewidth=2, color="#4c72b0")
    ax.plot(population_pct, population_pct, "k--", alpha=0.4, label="Random")
    # Perfect model
    n_pos = int(total_positives)
    perfect = np.minimum(population_pct * len(y_sorted) / n_pos, 1.0) if n_pos > 0 else population_pct
    ax.plot(population_pct, perfect, "g--", alpha=0.3, label="Perfect")

    ax.set_xlabel("Population percentage")
    ax.set_ylabel("Percentage of positives captured")
    ax.set_title("Cumulative Gain Chart")
    ax.legend(loc="lower right")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1.05)
    return fig, ax

# Phase 5 — Error Analysis Plots

def plot_error_rate_by_category(
    profile: Any,
    cat_col: str,
    top_n: int = 15,
    min_samples: int = 10,
    figsize: tuple[int, int] = (8, 6),
    ax: plt.Axes | None = None,
) -> tuple[plt.Figure, plt.Axes]:
    """Horizontal bar chart of error rate per category level for a given column.

    Parameters
    ----------
    profile:
        ``ErrorProfile`` from :func:`fraud_detect.error_analysis.compute_error_profile`.
    cat_col:
        Column name to filter segments by.
    top_n:
        Maximum number of categories to show.
    min_samples:
        Minimum samples required to include a category.
    figsize:
        Figure dimensions.
    ax:
        Optional existing axes to plot on.

    Returns
    -------
    tuple[Figure, Axes]
    """
    configure_style()
    fig, ax = plt.subplots(figsize=figsize) if ax is None else (ax.figure, ax)

    seg = profile.by_segment
    if seg.empty:
        ax.text(0.5, 0.5, "No segmentation data", ha="center", va="center", transform=ax.transAxes)
        return fig, ax

    cat_seg = seg[seg["segment_col"] == cat_col].copy()
    cat_seg = cat_seg[cat_seg["n_samples"] >= min_samples]
    cat_seg = cat_seg.sort_values("error_rate", ascending=True).tail(top_n)

    if cat_seg.empty:
        ax.text(0.5, 0.5, f"No data for column '{cat_col}'", ha="center", va="center", transform=ax.transAxes)
        return fig, ax

    ax.barh(cat_seg["segment_value"], cat_seg["error_rate"], color="#c44e52")
    ax.set_xlabel("Error rate")
    ax.set_title(f"Error rate by {cat_col}")
    ax.invert_yaxis()
    plt.tight_layout()
    return fig, ax

def plot_feature_shift_comparison(
    shift_df: pd.DataFrame,
    top_n: int = 10,
    figsize: tuple[int, int] = (8, 5),
    ax: plt.Axes | None = None,
) -> tuple[plt.Figure, plt.Axes]:
    """Horizontal bar chart showing the largest mean differences between
    errors and correct predictions.

    Parameters
    ----------
    shift_df:
        DataFrame from :func:`fraud_detect.error_analysis.feature_distribution_shift`.
    top_n:
        Number of features to show.
    figsize:
        Figure dimensions.
    ax:
        Optional existing axes to plot on.

    Returns
    -------
    tuple[Figure, Axes]
    """
    configure_style()
    fig, ax = plt.subplots(figsize=figsize) if ax is None else (ax.figure, ax)

    if shift_df.empty:
        ax.text(0.5, 0.5, "No shift data", ha="center", va="center", transform=ax.transAxes)
        return fig, ax

    top = shift_df.head(top_n)
    colors = ["#c44e52" if d < 0 else "#55a868" for d in top["diff"]]
    ax.barh(top["feature"], top["diff"], color=colors)
    ax.axvline(x=0, color="black", linewidth=0.5)
    ax.set_xlabel("Mean difference (error − correct)")
    ax.set_title("Feature distribution shift — errors vs. correct")
    ax.invert_yaxis()
    plt.tight_layout()
    return fig, ax

def plot_confusion_by_amount(
    df: pd.DataFrame,
    y_true: pd.Series | np.ndarray,
    y_pred: np.ndarray,
    amt_col: str = "TransactionAmt",
    n_bins: int = 10,
    figsize: tuple[int, int] = (10, 5),
    ax: plt.Axes | None = None,
) -> tuple[plt.Figure, plt.Axes]:
    """Plot error rate, FP rate, and FN rate bucketed by transaction amount.

    Parameters
    ----------
    df:
        Feature DataFrame with amount column.
    y_true:
        Ground-truth labels.
    y_pred:
        Binary predictions.
    amt_col:
        Name of the amount column.
    n_bins:
        Number of amount bins.
    figsize:
        Figure dimensions.
    ax:
        Optional existing axes to plot on.

    Returns
    -------
    tuple[Figure, Axes]
    """
    from .error_analysis import confusion_by_amount_bins

    configure_style()
    fig, ax = plt.subplots(figsize=figsize) if ax is None else (ax.figure, ax)

    result = confusion_by_amount_bins(df, y_true, y_pred, amt_col=amt_col, n_bins=n_bins)
    if result.empty:
        ax.text(0.5, 0.5, "No data", ha="center", va="center", transform=ax.transAxes)
        return fig, ax

    x_pos = np.arange(len(result))
    bin_labels = [str(b) for b in result["amount_bin"].values]

    ax.plot(x_pos, result["error_rate"].values, "o-", label="Error rate", color="#c44e52", linewidth=2)
    ax.plot(x_pos, result["fp_rate"].values, "s--", label="FP rate", color="#4c72b0", alpha=0.7)
    ax.plot(x_pos, result["fn_rate"].values, "d--", label="FN rate", color="#dd8452", alpha=0.7)

    ax.set_xticks(x_pos)
    ax.set_xticklabels(bin_labels, rotation=45, ha="right", fontsize=8)
    ax.set_xlabel("Amount bracket")
    ax.set_ylabel("Rate")
    ax.set_title("Error rate by transaction amount")
    ax.legend()
    ax.set_ylim(0, max(result[["error_rate", "fp_rate", "fn_rate"]].max()) * 1.2 + 0.05)
    plt.tight_layout()
    return fig, ax

def plot_false_positive_examples(
    examples_df: pd.DataFrame,
    feature_cols: list[str] | None = None,
    figsize: tuple[int, int] = (10, 6),
    ax: plt.Axes | None = None,
) -> tuple[plt.Figure, plt.Axes]:
    """Heatmap of the most confident false positives, showing feature values.

    Parameters
    ----------
    examples_df:
        DataFrame from :func:`fraud_detect.error_analysis.top_false_positives`.
    feature_cols:
        Columns to display. Defaults to first 10 numeric columns + probability.
    figsize:
        Figure dimensions.
    ax:
        Optional existing axes to plot on.

    Returns
    -------
    tuple[Figure, Axes]
    """
    configure_style()
    fig, ax = plt.subplots(figsize=figsize) if ax is None else (ax.figure, ax)

    if examples_df.empty:
        ax.text(0.5, 0.5, "No false positives", ha="center", va="center", transform=ax.transAxes)
        return fig, ax

    feature_cols = feature_cols or (
        examples_df.select_dtypes(include=[np.number]).columns[:10].tolist()
        + (["predicted_probability"] if "predicted_probability" in examples_df.columns else [])
    )
    available = [c for c in feature_cols if c in examples_df.columns]
    if not available:
        ax.text(0.5, 0.5, "No numeric columns available", ha="center", va="center", transform=ax.transAxes)
        return fig, ax

    data = examples_df[available].copy()
    data_normalised = (data - data.min()) / (data.max() - data.min() + 1e-9)

    im = ax.imshow(data_normalised.values, aspect="auto", cmap="YlOrRd")
    ax.set_yticks(range(len(data)))
    ax.set_yticklabels([f"#{i}" for i in data.index], fontsize=8)
    ax.set_xticks(range(len(available)))
    ax.set_xticklabels(available, rotation=45, ha="right", fontsize=8)
    ax.set_title(f"Top {len(data)} false positives — feature heatmap")
    plt.colorbar(im, ax=ax, label="Normalised value")
    plt.tight_layout()
    return fig, ax
