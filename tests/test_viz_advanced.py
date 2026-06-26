"""Smoke tests for the advanced visualisation functions in fraud_detect.viz.

These tests verify that each plot function returns a (Figure, Axes) tuple
without crashing. They use synthetic data so they run without the real
IEEE-CIS dataset.
"""

from __future__ import annotations

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytest

from fraud_detect import viz

matplotlib.use("Agg")


@pytest.fixture
def binary_data() -> tuple[dict[str, pd.Series], dict[str, np.ndarray]]:
    rng = np.random.default_rng(42)
    n = 200
    y_true = pd.Series(rng.integers(0, 2, n))
    y_pred = rng.uniform(0, 1, n)

    y_true_2 = pd.Series(rng.integers(0, 2, n))
    y_pred_2 = rng.uniform(0, 1, n)

    return (
        {"Model A": y_true, "Model B": y_true_2},
        {"Model A": y_pred, "Model B": y_pred_2},
    )


# --------------------------------------------------------------------------- #
# plot_roc_curves
# --------------------------------------------------------------------------- #


def test_plot_roc_curves_returns_figure(binary_data):
    y_true_dict, y_pred_dict = binary_data
    fig, ax = viz.plot_roc_curves(y_true_dict, y_pred_dict)
    assert isinstance(fig, plt.Figure)
    assert isinstance(ax, plt.Axes)
    plt.close(fig)


def test_plot_roc_single_model(binary_data):
    y_true_dict, y_pred_dict = binary_data
    fig, ax = viz.plot_roc_curves(
        {"A": y_true_dict["Model A"]},
        {"A": y_pred_dict["Model A"]},
    )
    assert isinstance(fig, plt.Figure)
    plt.close(fig)


# --------------------------------------------------------------------------- #
# plot_pr_curves
# --------------------------------------------------------------------------- #


def test_plot_pr_curves_returns_figure(binary_data):
    y_true_dict, y_pred_dict = binary_data
    fig, ax = viz.plot_pr_curves(y_true_dict, y_pred_dict)
    assert isinstance(fig, plt.Figure)
    assert isinstance(ax, plt.Axes)
    plt.close(fig)


# --------------------------------------------------------------------------- #
# plot_confusion_matrix
# --------------------------------------------------------------------------- #


def test_plot_confusion_matrix_returns_figure():
    y_true = pd.Series([0, 0, 1, 1, 0, 1, 0, 1])
    y_pred = np.array([0, 1, 1, 1, 0, 0, 0, 1])
    fig, ax = viz.plot_confusion_matrix(y_true, y_pred)
    assert isinstance(fig, plt.Figure)
    plt.close(fig)


def test_plot_confusion_matrix_normalised():
    y_true = pd.Series([0, 0, 1, 1, 0])
    y_pred = np.array([0, 0, 1, 0, 0])
    fig, ax = viz.plot_confusion_matrix(y_true, y_pred, normalize=True)
    assert isinstance(fig, plt.Figure)
    plt.close(fig)


# --------------------------------------------------------------------------- #
# plot_metrics_comparison
# --------------------------------------------------------------------------- #


def test_plot_metrics_comparison_returns_figure():
    df = pd.DataFrame({
        "model": ["A", "B", "C"],
        "auc": [0.95, 0.93, 0.91],
        "f1": [0.80, 0.78, 0.75],
        "precision": [0.85, 0.82, 0.80],
        "recall": [0.76, 0.74, 0.71],
    })
    fig, ax = viz.plot_metrics_comparison(df)
    assert isinstance(fig, plt.Figure)
    plt.close(fig)


# --------------------------------------------------------------------------- #
# plot_threshold_analysis
# --------------------------------------------------------------------------- #


def test_plot_threshold_analysis_returns_figure():
    rng = np.random.default_rng(42)
    y_true = pd.Series(rng.integers(0, 2, 200))
    y_pred = np.clip(y_true.astype(float) + rng.normal(0, 0.3, 200), 0, 1)
    fig, ax = viz.plot_threshold_analysis(y_true, y_pred, n_thresholds=50)
    assert isinstance(fig, plt.Figure)
    plt.close(fig)


# --------------------------------------------------------------------------- #
# plot_cumulative_gain
# --------------------------------------------------------------------------- #


def test_plot_cumulative_gain_returns_figure():
    rng = np.random.default_rng(42)
    y_true = pd.Series(rng.integers(0, 2, 200))
    y_pred = rng.uniform(0, 1, 200)
    fig, ax = viz.plot_cumulative_gain(y_true, y_pred)
    assert isinstance(fig, plt.Figure)
    plt.close(fig)
