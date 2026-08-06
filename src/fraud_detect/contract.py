"""Versioned feature contract for raw IEEE-compatible payloads.

The model is trained on an exact, ordered list of 400 numeric features. A raw
"production-style" payload must satisfy that contract: **unknown feature
names are rejected** (never silently dropped) and **critical fields must be
present** (never silently defaulted). Optional fields that are absent are
filled with the model's training-time fill value (-999) — but that is always
reported so the caller knows exactly what the model saw.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

#: Business-critical fields that must always be supplied by a raw payload.
#: Deliberately a small, documented subset of the 400 features.
REQUIRED_FIELDS: tuple[str, ...] = ("TransactionAmt", "card1", "C1", "D1")

#: Contract version tag; bumped only when the schema rules change.
CONTRACT_VERSION: str = "v1"


class ContractError(ValueError):
    """Raised when a payload violates the feature contract.

    ``messages`` carries the actionable, per-field errors.
    """

    def __init__(self, messages: list[str]):
        super().__init__("; ".join(messages))
        self.messages = messages


@dataclass
class FieldStatus:
    """Per-field validation outcome for one feature."""

    field: str
    status: str  # supplied | defaulted | missing | rejected
    reason: str = ""

    def as_dict(self) -> dict[str, str]:
        return {"field": self.field, "status": self.status, "reason": self.reason}


@dataclass
class ContractReport:
    """Result of validating a payload against the model's feature list."""

    features: list[str]
    report: dict[str, FieldStatus] = field(default_factory=dict)

    def counts(self) -> dict[str, int]:
        out = {"supplied": 0, "defaulted": 0, "missing": 0, "rejected": 0}
        for status in self.report.values():
            if status.status in out:
                out[status.status] += 1
        return out

    def as_dict(self) -> dict[str, Any]:
        return {
            "counts": self.counts(),
            "fields": {k: v.as_dict() for k, v in self.report.items()},
        }


def _is_numeric(value: Any) -> bool:
    try:
        float(value)
        return True
    except (TypeError, ValueError):
        return False


def validate_payload(payload: dict[str, Any], features: list[str]) -> ContractReport:
    """Validate ``payload`` against ``features`` and return a contract report.

    Raises
    ------
    ContractError
        If a payload contains unknown features or is missing a required field.
    """
    known = set(features)
    report: dict[str, FieldStatus] = {}
    errors: list[str] = []

    for name, value in payload.items():
        if name not in known:
            report[name] = FieldStatus(name, "rejected", reason="unknown feature")
            errors.append(f"Unknown feature '{name}' is not part of the model contract.")
        elif not _is_numeric(value):
            report[name] = FieldStatus(name, "rejected", reason="non-numeric value")
            errors.append(f"Feature '{name}' must be numeric, got {type(value).__name__}.")

    for name in features:
        if name in payload:
            if name not in report:
                report[name] = FieldStatus(name, "supplied")
        elif name in REQUIRED_FIELDS:
            report[name] = FieldStatus(name, "missing", reason="required field")
            errors.append(
                f"Missing required feature '{name}'. "
                f"Raw payloads must supply at least: {', '.join(REQUIRED_FIELDS)}."
            )
        else:
            report[name] = FieldStatus(name, "defaulted", reason="filled with training fill value")

    if errors:
        raise ContractError(errors)
    return ContractReport(features=list(features), report=report)
