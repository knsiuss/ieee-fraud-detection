"""Decide whether the drift artefact should trigger a retrain, and alert.

Evaluates ``data/metadata/drift_report.json`` with the pure policy in
``fraud_detect.drift_guard`` and writes a machine-readable alert document.
Exit codes are cron/CI friendly: ``0`` ok, ``2`` warn, ``3`` alert.

Usage::

    python scripts/drift_guard.py
    python scripts/drift_guard.py --max-age-days 7 --json

Wire it next to ``scripts/retrain.py`` in cron and route the exit code (or the
written alert) to your paging system.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "src"))

from fraud_detect import config  # noqa: E402
from fraud_detect.drift_guard import (  # noqa: E402
    CRITICAL_PSI,
    MAX_ARTEFACT_AGE_DAYS,
    RETRAIN_DRIFT_COUNT,
    evaluate,
)

EXIT = {"ok": 0, "warn": 2, "alert": 3}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--report",
        type=Path,
        default=config.METADATA_DIR / "drift_report.json",
        help="drift artefact to evaluate",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=config.METADATA_DIR / "drift_alert.json",
        help="where to write the alert document",
    )
    parser.add_argument("--max-age-days", type=int, default=MAX_ARTEFACT_AGE_DAYS)
    parser.add_argument("--max-drift-count", type=int, default=RETRAIN_DRIFT_COUNT)
    parser.add_argument("--critical-psi", type=float, default=CRITICAL_PSI)
    parser.add_argument("--json", action="store_true", help="print the alert document")
    args = parser.parse_args(argv)

    report = None
    if args.report.exists():
        report = json.loads(args.report.read_text(encoding="utf-8"))

    alert = evaluate(
        report,
        now=datetime.now(timezone.utc),
        max_age_days=args.max_age_days,
        max_drift_count=args.max_drift_count,
        critical_psi=args.critical_psi,
    )
    document = {
        "evaluated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "report": str(args.report),
        **alert.as_dict(),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(document, indent=2), encoding="utf-8")

    if args.json:
        print(json.dumps(document, indent=2))
    else:
        print(f"drift status: {alert.status.upper()} -> {alert.action}")
        for reason in alert.reasons:
            print(f"  - {reason}")
    return EXIT[alert.status]


if __name__ == "__main__":
    raise SystemExit(main())
