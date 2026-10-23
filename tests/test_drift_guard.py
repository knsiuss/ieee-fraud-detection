"""Tests for src/fraud_detect/drift_guard.py policy."""

from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT / "src"))

from fraud_detect import drift_guard  # noqa: E402

NOW = datetime(2026, 1, 15, 12, 0, tzinfo=timezone.utc)


def _report(*, psi: float = 0.02, drifted: int = 0, age_days: int = 1, feature: str = "card1"):
    return {
        "generated_at": (NOW - timedelta(days=age_days)).isoformat(),
        "drifted_features": drifted,
        "top_drift": [{"feature": feature, "psi": psi, "status": "ok"}],
    }


class TestEvaluate:
    def test_clean_report_is_ok(self):
        alert = drift_guard.evaluate(_report(), now=NOW)
        assert alert.status == "ok"
        assert alert.action.startswith("none")
        assert alert.as_dict()["status"] == "ok"

    def test_missing_artefact_is_alert(self):
        alert = drift_guard.evaluate(None, now=NOW)
        assert alert.status == "alert"
        assert "no drift artefact" in alert.reasons[0]

    def test_critical_psi_is_alert(self):
        alert = drift_guard.evaluate(_report(psi=0.9, feature="C5"), now=NOW)
        assert alert.status == "alert"
        assert any("C5" in reason for reason in alert.reasons)

    def test_many_drifted_features_is_alert(self):
        alert = drift_guard.evaluate(_report(drifted=12), now=NOW)
        assert alert.status == "alert"
        assert any("12 features drifted" in reason for reason in alert.reasons)

    def test_stale_report_is_warn(self):
        alert = drift_guard.evaluate(_report(age_days=30), now=NOW)
        assert alert.status == "warn"
        assert alert.age_days == 30

    def test_thresholds_are_configurable(self):
        alert = drift_guard.evaluate(
            _report(drifted=3, psi=0.1), now=NOW, max_drift_count=10, critical_psi=0.5
        )
        assert alert.status == "ok"

    def test_bad_timestamp_does_not_crash(self):
        report = _report()
        report["generated_at"] = "not-a-date"
        alert = drift_guard.evaluate(report, now=NOW)
        assert alert.age_days is None

    def test_naive_timestamp_is_treated_as_utc(self):
        report = _report()
        report["generated_at"] = "2026-01-14T12:00:00"
        alert = drift_guard.evaluate(report, now=NOW)
        assert alert.age_days == 1
