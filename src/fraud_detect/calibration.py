"""Probability calibration: turn risk rankings into usable likelihoods.

The served model's raw scores rank risk well but are not calibrated
probabilities (see ``README`` — Brier 0.021, top-decile over-prediction), and
every threshold or expected-cost decision implicitly assumes calibrated
probabilities. This module provides two monotone calibrators plus the
diagnostics needed to prove a calibration actually works:

* ``isotonic`` — non-parametric, monotone, needs a few thousand rows;
* ``platt`` — logistic fit on the logit, stable on small samples.

Diagnostics: expected calibration error (ECE) and reliability bins.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

import numpy as np

Method = Literal["isotonic", "platt"]
METHODS: tuple[Method, ...] = ("isotonic", "platt")
_EPS = 1e-6
DEFAULT_VERSION = "cal-v1"


@dataclass(frozen=True)
class Calibrator:
    """A fitted probability mapping.

    ``knots`` holds ``(raw_probability, calibrated_probability)`` pairs for the
    isotonic fit; ``coef``/``intercept`` hold the Platt sigmoid parameters.
    """

    method: Method
    version: str = DEFAULT_VERSION
    knots: list[tuple[float, float]] = field(default_factory=list)
    coef: float = 1.0
    intercept: float = 0.0
    n_fit: int = 0

    def as_dict(self) -> dict[str, Any]:
        return {
            "method": self.method,
            "version": self.version,
            "knots": [[x, y] for x, y in self.knots],
            "coef": self.coef,
            "intercept": self.intercept,
            "n_fit": self.n_fit,
        }

    def apply(self, probabilities: np.ndarray | list[float]) -> np.ndarray:
        return apply_calibrator(self, probabilities)


def _as_arrays(
    y_true: np.ndarray | list[int], probs: np.ndarray | list[float]
) -> tuple[np.ndarray, np.ndarray]:
    y = np.asarray(y_true, dtype="float64").reshape(-1)
    p = np.asarray(probs, dtype="float64").reshape(-1)
    if y.shape != p.shape:
        raise ValueError(f"shape mismatch: y={y.shape}, probs={p.shape}")
    if y.size == 0:
        raise ValueError("calibration needs at least one observation")
    return y, np.clip(p, _EPS, 1.0 - _EPS)


def _logit(p: np.ndarray) -> np.ndarray:
    return np.log(p / (1.0 - p))


def fit_calibrator(
    y_true: np.ndarray | list[int],
    probs: np.ndarray | list[float],
    method: Method = "isotonic",
    *,
    version: str = DEFAULT_VERSION,
) -> Calibrator:
    """Fit a monotone mapping ``raw probability -> calibrated probability``."""
    if method not in METHODS:
        raise ValueError(f"method must be one of {METHODS}, got {method!r}")
    y, p = _as_arrays(y_true, probs)
    if y.min() < 0 or y.max() > 1:
        raise ValueError("y_true must be 0/1")
    if len(np.unique(y)) < 2:
        raise ValueError("calibration needs both classes in the fit sample")

    if method == "isotonic":
        from sklearn.isotonic import IsotonicRegression

        iso = IsotonicRegression(y_min=0.0, y_max=1.0, out_of_bounds="clip")
        iso.fit(p, y)
        # Keep the step function as explicit knots so the calibrator is
        # portable (JSON) without pickling sklearn objects.
        xs = np.unique(p)
        ys = iso.predict(xs)
        return Calibrator(
            method="isotonic",
            version=version,
            knots=[(float(x), float(v)) for x, v in zip(xs, ys, strict=True)],
            n_fit=int(y.size),
        )

    from sklearn.linear_model import LogisticRegression

    lr = LogisticRegression(C=1e6, solver="lbfgs", max_iter=1000)
    lr.fit(_logit(p).reshape(-1, 1), y.astype(int))
    return Calibrator(
        method="platt",
        version=version,
        coef=float(lr.coef_[0][0]),
        intercept=float(lr.intercept_[0]),
        n_fit=int(y.size),
    )


def apply_calibrator(calibrator: Calibrator, probabilities: np.ndarray | list[float]) -> np.ndarray:
    """Map raw probabilities through a fitted calibrator."""
    p = np.clip(np.asarray(probabilities, dtype="float64").reshape(-1), _EPS, 1.0 - _EPS)
    if calibrator.method == "platt":
        z = calibrator.coef * _logit(p) + calibrator.intercept
        return 1.0 / (1.0 + np.exp(-z))
    if not calibrator.knots:
        return p
    xs = np.array([x for x, _ in calibrator.knots], dtype="float64")
    ys = np.array([y for _, y in calibrator.knots], dtype="float64")
    return np.interp(p, xs, ys, left=float(ys[0]), right=float(ys[-1]))


def reliability_bins(
    y_true: np.ndarray | list[int],
    probs: np.ndarray | list[float],
    n_bins: int = 10,
) -> list[dict[str, float]]:
    """Per-bin predicted vs observed fraud rate (the reliability diagram data)."""
    y, p = _as_arrays(y_true, probs)
    if n_bins < 2:
        raise ValueError("n_bins must be >= 2")
    edges = np.linspace(0.0, 1.0, n_bins + 1)
    bins: list[dict[str, float]] = []
    for i in range(n_bins):
        lo, hi = float(edges[i]), float(edges[i + 1])
        mask = (p >= lo) & (p < hi) if i < n_bins - 1 else (p >= lo) & (p <= hi)
        count = int(mask.sum())
        mean_pred = float(p[mask].mean()) if count else 0.0
        observed = float(y[mask].mean()) if count else 0.0
        bins.append(
            {
                "bin_lower": round(lo, 4),
                "bin_upper": round(hi, 4),
                "count": count,
                "mean_predicted": round(mean_pred, 6),
                "observed_rate": round(observed, 6),
            }
        )
    return bins


def expected_calibration_error(
    y_true: np.ndarray | list[int],
    probs: np.ndarray | list[float],
    n_bins: int = 10,
) -> float:
    """Weighted average gap between predicted and observed fraud rate."""
    y, p = _as_arrays(y_true, probs)
    bins = reliability_bins(y, p, n_bins=n_bins)
    total = int(y.size)
    return float(
        sum(b["count"] * abs(b["mean_predicted"] - b["observed_rate"]) for b in bins) / total
    )


def brier_score(y_true: np.ndarray | list[int], probs: np.ndarray | list[float]) -> float:
    y, p = _as_arrays(y_true, probs)
    return float(np.mean((p - y) ** 2))


def save_calibrator(calibrator: Calibrator, path: Path | str) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(calibrator.as_dict(), indent=2), encoding="utf-8")
    return target


def load_calibrator(path: Path | str) -> Calibrator:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    method = raw.get("method")
    if method not in METHODS:
        raise ValueError(f"unknown calibrator method {method!r}")
    return Calibrator(
        method=method,
        version=str(raw.get("version", DEFAULT_VERSION)),
        knots=[(float(x), float(y)) for x, y in raw.get("knots", [])],
        coef=float(raw.get("coef", 1.0)),
        intercept=float(raw.get("intercept", 0.0)),
        n_fit=int(raw.get("n_fit", 0)),
    )
