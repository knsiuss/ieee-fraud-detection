"""Tests for fraud_detect.synthetic — trusted synthetic label source."""

from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest

from fraud_detect.synthetic import (
    DEFAULT_NOISE_SCALE,
    SYNTHETIC_ID_PREFIX,
    SyntheticGenerator,
    write_labels_file,
)


def _source() -> pd.DataFrame:
    rng = np.random.default_rng(7)
    n = 100
    return pd.DataFrame(
        {
            "TransactionID": np.arange(n),
            "isFraud": rng.integers(0, 2, n),
            "TransactionAmt": rng.uniform(1, 500, n),
            "card1": rng.integers(1000, 9999, n),
            "C1": rng.integers(0, 5, n),
            "D1": rng.integers(1, 100, n),
            "ProductCD": rng.choice(["W", "H", "C"], n),  # non-numeric: dropped
        }
    )


class TestGenerator:
    def test_payloads_are_numeric_and_labeled(self):
        gen = SyntheticGenerator(source=_source())
        payloads = gen.generate(n=10, seed=42)
        assert len(payloads) == 10
        for payload in payloads:
            assert payload["transaction_id"].startswith(SYNTHETIC_ID_PREFIX)
            assert all(isinstance(v, float) for v in payload["values"].values())
            assert set(payload["values"]) == {"TransactionAmt", "card1", "C1", "D1"}
            assert payload["_synthetic_label"] in (0, 1)

    def test_reproducible_with_seed(self):
        gen = SyntheticGenerator(source=_source())
        a = gen.generate(n=5, seed=123)
        b = gen.generate(n=5, seed=123)
        assert [p["transaction_id"] for p in a] == [p["transaction_id"] for p in b]
        assert a[0]["values"] == b[0]["values"]

    def test_fraud_oversample_changes_distribution(self):
        source = _source()
        base_fraud = float(source["isFraud"].mean())
        gen = SyntheticGenerator(source=source)
        oversample = [
            p["_synthetic_label"] for p in gen.generate(n=200, seed=5, fraud_oversample=True)
        ]
        assert sum(oversample) / len(oversample) > base_fraud

    def test_noise_preserves_missing_sentinel(self):
        source = _source()
        source.loc[0, "C1"] = -999.0
        gen = SyntheticGenerator(source=source)
        # Row 0 must be sampled somewhere in a long run; whenever the
        # sentinel is drawn it must survive the noise exactly.
        payloads = gen.generate(n=5000, seed=1)
        c1_values = [p["values"]["C1"] for p in payloads]
        assert -999.0 in c1_values
        assert all(v == -999.0 for v in c1_values if v == -999.0)

    def test_default_noise_scale(self):
        assert DEFAULT_NOISE_SCALE == 0.05

    def test_missing_target_raises(self):
        with pytest.raises(ValueError, match="isFraud"):
            SyntheticGenerator(source=pd.DataFrame({"A": [1.0]}))

    def test_size_matches_source(self):
        gen = SyntheticGenerator(source=_source())
        assert gen.size == 100


class TestLabelsFile:
    def test_writes_jsonl_with_source_marker(self, tmp_path):
        path = write_labels_file(
            tmp_path / "labels.jsonl",
            [
                {
                    "transaction_id": "syn-000000",
                    "_synthetic_label": 1,
                    "score": 0.883,
                    "decision": "DECLINE",
                }
            ],
        )
        lines = path.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 1
        row = json.loads(lines[0])
        assert row["_source"] == "synthetic"
        assert row["is_fraud_synthetic"] == 1
        assert row["transaction_id"] == "syn-000000"
        assert row["score"] == 0.883

    def test_append_mode(self, tmp_path):
        path = tmp_path / "labels.jsonl"
        write_labels_file(path, [{"transaction_id": "a", "_synthetic_label": 0}])
        write_labels_file(path, [{"transaction_id": "b", "_synthetic_label": 1}])
        assert len(path.read_text(encoding="utf-8").strip().splitlines()) == 2

    def test_non_finite_score_serialised_as_null(self, tmp_path):
        path = write_labels_file(
            tmp_path / "labels.jsonl", [{"transaction_id": "c", "score": float("nan")}]
        )
        row = json.loads(path.read_text(encoding="utf-8").strip().splitlines()[0])
        assert row["score"] is None
