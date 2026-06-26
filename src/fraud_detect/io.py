"""I/O helpers for parquet / CSV artefacts.

These thin wrappers exist so notebooks and scripts never inline ``Path`` +
``read_parquet`` boilerplate, and so that the data-root can be reconfigured
in one place via :mod:`fraud_detect.config`.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from . import config
from ._exceptions import InvalidDataError, MissingArtefactError

def ensure_dir(path: Path) -> Path:
    """Create ``path`` (and parents) if it does not exist; return ``path``."""
    path.mkdir(parents=True, exist_ok=True)
    return path

def read_parquet(path: Path) -> pd.DataFrame:
    """Read a parquet file, raising a clear error when it is missing."""
    if not path.exists():
        raise MissingArtefactError(
            f"Expected parquet artefact not found: {path}. "
            "Run the upstream notebook or set FRAUD_DETECT_DATA_ROOT."
        )
    return pd.read_parquet(path)

def write_parquet(df: pd.DataFrame, path: Path) -> None:
    """Write ``df`` to ``path`` as snappy-compressed parquet (pyarrow)."""
    ensure_dir(path.parent)
    df.to_parquet(path, engine="pyarrow", compression="snappy")

def read_csv(path: Path, **kwargs) -> pd.DataFrame:
    """Read a CSV with a clear error when missing."""
    if not path.exists():
        raise MissingArtefactError(f"Expected CSV artefact not found: {path}.")
    return pd.read_csv(path, **kwargs)

def write_csv(df: pd.DataFrame, path: Path, **kwargs) -> None:
    """Write ``df`` to ``path`` as CSV, creating parent dirs as needed."""
    ensure_dir(path.parent)
    df.to_csv(path, **kwargs)

def load_train_features() -> pd.DataFrame:
    """Load the engineered training table.

    Falls back to the merged (pre-feature-engineering) table when the
    processed artefact has not been produced yet, mirroring the behaviour
    that notebooks 08 and 09 previously inlined.

    Examples
    --------
    >>> df = load_train_features()  # doctest: +SKIP
    >>> df.shape  # doctest: +SKIP
    (590540, 434)
    """
    path = (
        config.PROCESSED_TRAIN_PATH
        if config.PROCESSED_TRAIN_PATH.exists()
        else config.MERGED_TRAIN_PATH
    )
    df = read_parquet(path)
    if df.empty:
        raise InvalidDataError(f"Loaded DataFrame from {path} is empty.")
    if config.TARGET_COLUMN not in df.columns:
        raise InvalidDataError(
            f"Loaded DataFrame from {path} is missing target column "
            f"'{config.TARGET_COLUMN}'. Available columns: {list(df.columns)[:5]}..."
        )
    return df
