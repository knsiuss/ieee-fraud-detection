"""Convert raw IEEE-CIS CSV files to memory-optimised parquet.

Usage::

    python scripts/prepare_data.py [--verbose]

Reads CSVs from ``data/raw/``, applies :func:`fraud_detect.data.reduce_mem_usage`
to every table except ``sample_submission`` (where dtypes are irrelevant),
and writes snappy-compressed parquet next to each source file. A summary
table of CSV/parquet sizes and compression ratios is printed at the end.

The raw CSVs are intentionally *not* tracked in git (see ``.gitignore``);
download them from the Kaggle competition page first.
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path

import pandas as pd

# Allow running this script directly (``python scripts/prepare_data.py``) before
# the package is installed in editable mode.
_SRC = Path(__file__).resolve().parents[1] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from fraud_detect import config
from fraud_detect.data import reduce_mem_usage  # noqa: E402

logger = logging.getLogger("data_prep")

# Base directory for raw CSV files (uses config so FRAUD_DETECT_DATA_ROOT is honoured).
_RAW_DIR = config.RAW_DIR

#: Mapping of logical name -> CSV path under ``data/raw/``.
CSV_TO_PARQUET: dict[str, Path] = {
    "train_transaction": _RAW_DIR / "train_transaction.csv",
    "train_identity": _RAW_DIR / "train_identity.csv",
    "test_transaction": _RAW_DIR / "test_transaction.csv",
    "test_identity": _RAW_DIR / "test_identity.csv",
    "sample_submission": _RAW_DIR / "sample_submission.csv",
}

#: Tables for which dtype downcasting is skipped (no modelling benefit).
SKIP_MEMORY_REDUCTION: frozenset[str] = frozenset({"sample_submission"})


def convert_one(name: str, csv_path: Path) -> dict[str, float | int | str]:
    """Convert a single CSV to parquet, returning a summary record."""
    logger.info("loading %s", csv_path)
    start = time.time()
    df = pd.read_csv(csv_path)
    load_time = time.time() - start
    csv_size_mb = csv_path.stat().st_size / 1024**2
    logger.info(
        "loaded in %.1fs | %s rows x %d cols | CSV %.1fMB",
        load_time,
        f"{df.shape[0]:,}",
        df.shape[1],
        csv_size_mb,
    )

    if name not in SKIP_MEMORY_REDUCTION:
        df = reduce_mem_usage(df, verbose=True)

    parquet_path = csv_path.with_suffix(".parquet")
    start = time.time()
    df.to_parquet(parquet_path, engine="pyarrow", compression="snappy")
    save_time = time.time() - start
    parquet_size_mb = parquet_path.stat().st_size / 1024**2
    saved_mb = csv_size_mb - parquet_size_mb
    logger.info(
        "saved in %.1fs | parquet %.1fMB | saved %.1fMB (%.0f%%)",
        save_time,
        parquet_size_mb,
        saved_mb,
        (1 - parquet_size_mb / csv_size_mb) * 100,
    )

    return {
        "File": name,
        "Rows": df.shape[0],
        "Cols": df.shape[1],
        "CSV_MB": round(csv_size_mb, 1),
        "Parquet_MB": round(parquet_size_mb, 1),
        "Saved_MB": round(saved_mb, 1),
        "Compression_%": round((1 - parquet_size_mb / csv_size_mb) * 100, 1),
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert raw IEEE-CIS CSV files to memory-optimised parquet."
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable debug-level logging",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Run the full CSV -> parquet conversion and print a summary."""
    args = parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)-8s | %(message)s",
    )

    if not _RAW_DIR.exists():
        logger.error("'%s/' directory not found. Download the CSVs from Kaggle first.", _RAW_DIR)
        return 1

    records: list[dict[str, float | int | str]] = []
    total_start = time.time()
    for name, csv_path in CSV_TO_PARQUET.items():
        if not csv_path.exists():
            logger.warning("CSV not found, skipping: %s", csv_path)
            continue
        try:
            records.append(convert_one(name, csv_path))
        except Exception as exc:  # noqa: BLE001 — surface every failure without aborting
            logger.error("conversion failed for %s: %s", name, exc)

    if records:
        summary = pd.DataFrame(records)
        logger.info("=== Conversion summary ===\n%s", summary.to_string(index=False))

    logger.info("Total elapsed: %.1fs", time.time() - total_start)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
