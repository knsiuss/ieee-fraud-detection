"""Drift-to-retrain gate: turn an offline drift artefact into an action.

``scripts/drift_report.py`` measures PSI and data quality; this module decides
what that measurement *means* and whether the retrain loop should run:

* **ok** — nothing crossed a threshold; scheduled retraining can wait.
* **warn** — monitoring is stale or a few features drifted; refresh the
  report and let the next scheduled retrain absorb it.
* **alert** — many features or one feature drifted badly; run the gated
  retrain now (``make retrain``), which still refuses to swap a model that
  regresses on validation.

Pure functions so the policy is testable without a clock or a filesystem.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

RETRAIN_DRIFT_COUNT: int = 5
CRITICAL_PSI: float = 0.25
MAX_ARTEFACT_AGE_DAYS: int = 14
STATUSES = ("ok", "warn", "alert")


@dataclass(frozen=True)
class DriftAlert:
    status: str
    reasons: tuple[str, ...]
    max_psi: float | None
    drifted_features: int | None
    age_days: int | None
    action: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "reasons": list(self.reasons),
            "max_psi": self.max_psi,
            "drifted_features": self.drifted_features,
            "age_days": self.age_days,
            "action": self.action,
        }


def _age_days(generated_at: Any, now: datetime) -> int | None:
    if not generated_at:
        return None
    try:
        stamp = datetime.fromisoformat(str(generated_at).replace("Z", "+00:00"))
    except ValueError:
        return None
    if stamp.tzinfo is None:
        stamp = stamp.replace(tzinfo=timezone.utc)
    return max(0, (now - stamp).days)


def evaluate(
    report: dict[str, Any] | None,
    *,
    now: datetime | None = None,
    max_age_days: int = MAX_ARTEFACT_AGE_DAYS,
    max_drift_count: int = RETRAIN_DRIFT_COUNT,
    critical_psi: float = CRITICAL_PSI,
) -> DriftAlert:
    """Map a drift report to ``ok`` / ``warn`` / ``alert`` with reasons."""
    now = now or datetime.now(timezone.utc)
    if not report:
        return DriftAlert(
            status="alert",
            reasons=("no drift artefact found",),
            max_psi=None,
            drifted_features=None,
            age_days=None,
            action="run scripts/drift_report.py",
        )

    top = [row for row in (report.get("top_drift") or []) if isinstance(row, dict)]
    psis = []
    for row in top:
        try:
            value = row.get("psi")
            if value is None:
                continue
            fvalue = float(value)
        except (TypeError, ValueError):
            continue
        if fvalue != fvalue:
            continue
        psis.append(fvalue)
    max_psi = max(psis) if psis else None
    drifted = report.get("drifted_features")
    drifted = int(drifted) if drifted is not None else None
    age = _age_days(report.get("generated_at"), now)

    reasons: list[str] = []
    status = "ok"

    if max_psi is not None and max_psi >= critical_psi:
        try:
            top_feature = max(top, key=lambda row: float(row.get("psi") or 0.0)).get("feature")
        except (TypeError, ValueError):
            top_feature = None
        reasons.append(f"PSI {max_psi:.3f} >= {critical_psi:.2f} on {top_feature}")
        status = "alert"
    if drifted is not None and drifted >= max_drift_count:
        reasons.append(f"{drifted} features drifted >= {max_drift_count}")
        status = "alert"
    if age is not None and age > max_age_days:
        reasons.append(f"drift artefact is {age}d old (> {max_age_days}d)")
        if status == "ok":
            status = "warn"
    if drifted == 0 and max_psi is not None and max_psi < critical_psi and status == "ok":
        reasons.append(f"max PSI {max_psi:.3f} below alert threshold")

    action = {
        "ok": "none — wait for the scheduled retrain",
        "warn": "refresh drift_report.json; scheduled retrain will absorb it",
        "alert": "make retrain (candidate still must pass the validation gate)",
    }[status]
    return DriftAlert(
        status=status,
        reasons=tuple(reasons),
        max_psi=round(max_psi, 4) if max_psi is not None else None,
        drifted_features=drifted,
        age_days=age,
        action=action,
    )
