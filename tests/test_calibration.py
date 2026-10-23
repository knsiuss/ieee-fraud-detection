"""Tests for src/fraud_detect/calibration.py."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT / "src"))

from fraud_detect import calibration  # noqa: E402


def _overconfident(n: int = 4000, seed: int = 0) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    truth = rng.uniform(0.01, 0.6, n)
    y = (rng.uniform(0, 1, n) < truth).astype(int)
    raw = np.clip(truth * 1.8, 0.0, 1.0)  # systematically too high
    return y, raw


class TestCalibrators:
    def test_isotonic_is_monotone_and_clips(self):
        y, p = _overconfident()
        cal = calibration.fit_calibrator(y, p, "isotonic")
        out = cal.apply([0.0, 0.02, 0.3, 0.6, 1.0])
        assert np.all(np.diff(out) >= -1e-9)
        assert out[0] >= 0.0 and out[-1] <= 1.0

    def test_platt_improves_brier_on_overconfident_scores(self):
        y, p = _overconfident()
        cal = calibration.fit_calibrator(y, p, "platt")
        assert calibration.brier_score(y, cal.apply(p)) < calibration.brier_score(y, p)

    def test_isotonic_improves_ece(self):
        y, p = _overconfident()
        cal = calibration.fit_calibrator(y, p, "isotonic")
        raw_ece = calibration.expected_calibration_error(y, p)
        cal_ece = calibration.expected_calibration_error(y, cal.apply(p))
        assert cal_ece < raw_ece

    def test_unknown_method_raises(self):
        with pytest.raises(ValueError, match="method must be"):
            calibration.fit_calibrator([0, 1], [0.2, 0.8], "spline")  # type: ignore[arg-type]

    def test_single_class_raises(self):
        with pytest.raises(ValueError, match="both classes"):
            calibration.fit_calibrator([0, 0, 0], [0.1, 0.2, 0.3])

    def test_shape_mismatch_raises(self):
        with pytest.raises(ValueError, match="shape mismatch"):
            calibration.fit_calibrator([0, 1], [0.2])


class TestDiagnostics:
    def test_ece_known_value(self):
        # 4 obs, all predicted 0.25, half positive -> ECE 0.25
        ece = calibration.expected_calibration_error([0, 0, 1, 1], [0.25] * 4)
        assert ece == pytest.approx(0.25)

    def test_reliability_bins_cover_all_rows(self):
        y, p = _overconfident(500)
        bins = calibration.reliability_bins(y, p, n_bins=5)
        assert sum(b["count"] for b in bins) == 500
        assert len(bins) == 5

    def test_brier_known_value(self):
        assert calibration.brier_score([0, 1], [0.25, 0.75]) == pytest.approx(0.0625)


class TestPersistence:
    @pytest.mark.parametrize("method", list(calibration.METHODS))
    def test_roundtrip(self, tmp_path, method):
        y, p = _overconfident(800)
        cal = calibration.fit_calibrator(y, p, method=method)
        path = calibration.save_calibrator(cal, tmp_path / "cal.json")
        loaded = calibration.load_calibrator(path)
        assert loaded.method == cal.method
        np.testing.assert_allclose(loaded.apply([0.1, 0.5, 0.9]), cal.apply([0.1, 0.5, 0.9]))

    def test_unknown_method_on_load_raises(self, tmp_path):
        path = tmp_path / "bad.json"
        path.write_text('{"method": "magic"}', encoding="utf-8")
        with pytest.raises(ValueError, match="unknown calibrator method"):
            calibration.load_calibrator(path)
