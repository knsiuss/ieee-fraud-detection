"""Conftest: ensure the src/ package is importable when pytest runs before
an editable install (e.g. fresh CI checkout)."""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

SRC = Path(__file__).resolve().parent.parent / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


@pytest.fixture
def synthetic_df() -> pd.DataFrame:
    """A minimal DataFrame with representative dtypes for smoke testing."""
    rng = np.random.default_rng(42)
    n = 30
    return pd.DataFrame(
        {
            "TransactionID": np.arange(n),
            "isFraud": rng.integers(0, 2, n),
            "TransactionDT": rng.integers(0, 86400 * 7, n),
            "TransactionAmt": rng.uniform(1, 500, n),
            "ProductCD": rng.choice(["W", "H", "C"], n),
            "card1": rng.integers(1000, 9999, n),
            "card2": rng.choice([None, 100, 200, 300], n).astype(float),
            "P_emaildomain": rng.choice(["gmail.com", "yahoo.com", None], n),
            "R_emaildomain": rng.choice(["gmail.com", "hotmail.com", None], n),
            "id_01": rng.choice([0.0, -5.0, None], n).astype(float),
            "id_02": rng.choice([100.0, 500.0, None], n).astype(float),
            "id_03": rng.choice([0, 1, None], n).astype(float),
            "DeviceType": rng.choice(["desktop", "mobile", None], n),
            "DeviceInfo": rng.choice(["Windows", "iOS", "Linux", None], n),
        }
    )
