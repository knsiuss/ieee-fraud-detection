"""Distribution-drift and data-quality report for the served model.

Compares a "recent" stream of transactions (the reviewer's batch file) with a
training reference sample of the merged table and reports, per feature, the
Population Stability Index, plus a schema/missingness check. It is an
*offline* monitoring helper — real-time drift requires the service to keep
logging predictions, which is future work.

Usage
-----
    python scripts/drift_report.py [--recent PATH] [--reference PATH]

If ``--recent`` is omitted, ``web/sample_transactions.csv`` is used as a
stand-in so the script runs on a fresh clone. Writes
``data/metadata/drift_report.json``.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

_SRC = Path(__file__).resolve().parents[1] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

import pandas as pd  # noqa: E402

from fraud_detect import config  # noqa: E402
from fraud_detect.models import select_feature_columns  # noqa: E402
from fraud_detect.monitoring import data_quality_check, feature_drift  # noqa: E402

OUT_PATH = config.METADATA_DIR / "drift_report.json"
REFERENCE_SAMPLE = 50_000


def _load(path: Path) -> pd.DataFrame:
    if path.suffix == ".parquet":
        return pd.read_parquet(path)
    return pd.read_csv(path)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--recent", default=None, help="Recent transactions file to check.")
    parser.add_argument("--reference", default=None, help="Training table (default: merged).")
    args = parser.parse_args()

    reference_path = Path(args.reference) if args.reference else config.MERGED_TRAIN_PATH
    recent_path = (
        Path(args.recent)
        if args.recent
        else Path(__file__).resolve().parents[1] / "web" / "sample_transactions.csv"
    )

    print(f"Reference: {reference_path}")
    ref = _load(reference_path)
    if len(ref) > REFERENCE_SAMPLE:
        ref = ref.sample(n=REFERENCE_SAMPLE, random_state=config.RANDOM_STATE)
    features = select_feature_columns(ref)

    print(f"Recent stream: {recent_path}")
    recent = _load(recent_path)

    drift = feature_drift(features, ref, recent)
    quality = data_quality_check(recent, features)

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "reference": str(reference_path),
        "recent": str(recent_path),
        "n_features": len(features),
        "drifted_features": int((drift["status"] == "drifted").sum()),
        "top_drift": drift.head(15).to_dict(orient="records"),
        "data_quality": quality,
    }
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(f"\nFeatures checked: {len(features)} | drifted: {report['drifted_features']}")
    for row in drift.head(10).itertuples():
        print(f"  {row.feature:<22} PSI {row.psi:.4f}  {row.status}")
    print(f"\nReport written to {OUT_PATH}")


if __name__ == "__main__":
    main()
