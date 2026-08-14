"""Synthetic transaction simulator — trusted *synthetic* label source.

The platform has no live transaction stream and no live ground-truth
labels. For demo/observability purposes this module generates a continuous
synthetic stream that is statistically consistent with the IEEE-CIS
distribution, and — crucially — **each generated transaction carries a
known ground-truth label** (it was sampled from the labelled training
table). That gives Features 1 and 2 (bandit rewards, audit reports) and the
drift/monitoring scripts a label signal they can depend on.

> Honesty note: these are **synthetic** labels drawn from the training
> table, not real live outcomes. Nothing in this module should be mistaken
> for a real, forward-looking performance measurement. Consumers must
> surface the ``synthetic`` flag everywhere a performance number is shown.

Approach — bootstrap-plus-noise (recommended over SDV/CTGAN)
--------------------------------------------------------------
* **SDV/CTGAN**: generative models trained per-table. Highest fidelity, but
  heavy (torch dependency, GPU-less training takes significant CPU time,
  multi-GB footprint), and fidelity gain over resampling is marginal for a
  demo.
* **Bootstrap + noise (chosen)**: sample rows from the labelled training
  table (keeping the label), add per-column relative Gaussian noise, keep
  the model's ``-999`` missing sentinel intact. CPU-cheap, no new
  dependencies, fully reproducible via seed, and honest by construction
  (labels are the sampled truth).

The generated payloads flow through the *exact same path* as real ones
(``POST /api/predict`` → policy → SHAP → audit store) — see
``scripts/stream_transactions.py --synthetic`` for the orchestrator.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from . import config
from .serving import FILL_VALUE

#: Synthetic transaction ids are prefixed so they can be told apart from
#: real ones at a glance in the audit store / review queue.
SYNTHETIC_ID_PREFIX: str = "syn"

#: Per-column relative noise scale. Kept small so the synthetic stream stays
#: inside the training distribution (optionally widened with ``noise_scale``).
DEFAULT_NOISE_SCALE: float = 0.05


def _source_df() -> pd.DataFrame:
    """Resolve the labelled base table (same fallback chain as training)."""
    candidates = [
        config.PROCESSED_TRAIN_PATH,
        config.MERGED_TRAIN_PATH,
        Path(__file__).resolve().parents[2] / "dashboard" / "data" / "sample.parquet",
    ]
    for path in candidates:
        if path.exists():
            return pd.read_parquet(path)
    raise FileNotFoundError(
        "No training data found for the synthetic simulator. Run "
        "`python scripts/train_model.py` (which seeds the demo sample) "
        "or add data under data/."
    )


@dataclass
class SyntheticGenerator:
    """Generates numerically-consistent synthetic transactions with labels.

    Parameters
    ----------
    source:
        Optional pre-loaded labelled table (``isFraud`` column required).
        Defaults to the repo's resolved training table.
    noise_scale:
        Relative Gaussian noise (std fraction of the column's std). Higher
        values move the stream further from the training medians.
    """

    source: pd.DataFrame | None = None
    noise_scale: float = DEFAULT_NOISE_SCALE

    def __post_init__(self) -> None:
        df = self.source if self.source is not None else _source_df()
        if config.TARGET_COLUMN not in df.columns:
            raise ValueError("Synthetic source table must contain 'isFraud'.")
        # The model is numeric-only; categoricals are dropped at training
        # time and are never part of the serving contract.
        numeric = df.select_dtypes("number").columns.tolist()
        # The label is metadata (carried as _synthetic_label, never as a
        # payload feature) and the row id is not a feature either — both
        # must not leak into the generated feature values.
        numeric = [c for c in numeric if c != config.TARGET_COLUMN and c.lower() != "transactionid"]
        self._label = df[config.TARGET_COLUMN].astype(int).to_numpy()
        self._data = df[numeric].to_numpy(dtype="float64")
        self._columns = numeric
        self._stds = np.nanstd(self._data, axis=0)
        self._stds = np.where(np.isfinite(self._stds) & (self._stds > 0), self._stds, 1.0)

    @property
    def size(self) -> int:
        return len(self._data)

    def generate(
        self,
        n: int = 100,
        seed: int | None = None,
        fraud_oversample: bool = False,
    ) -> list[dict[str, Any]]:
        """Generate ``n`` synthetic transaction payloads with known labels.

        Each payload follows the shape ``POST /api/predict`` expects::

            {"transaction_id": "syn-<run>-<n>", "values": {<numeric features>}}

        and carries a ``_synthetic_label`` metadata key (0/1) so the
        orchestrator can persist the trusted synthetic ground truth.
        Transaction ids embed the run tag (the seed when given, a random
        nonce otherwise) so different runs never collide in the decision
        store, while same-seed replays stay idempotent.

        Parameters
        ----------
        n:
            Number of transactions to generate.
        seed:
            RNG seed for reproducibility.
        fraud_oversample:
            When True, fraud rows (label=1, ~3.5% of the source) are
            weighted ×5 during sampling so the synthetic stream contains a
            workable number of fraud examples for monitoring/bandit demos.
        """
        rng = np.random.default_rng(seed)
        run_tag = f"s{seed}" if seed is not None else f"r{int(rng.integers(0, 2**31 - 1))}"
        if fraud_oversample:
            weights = np.where(self._label == 1, 5.0, 1.0)
            weights = weights / weights.sum()
            idx = rng.choice(len(self._label), size=n, replace=True, p=weights)
        else:
            idx = rng.integers(0, len(self._label), size=n)

        payloads: list[dict[str, Any]] = []
        for position, source_index in enumerate(idx):
            row = self._data[source_index].copy()
            noise = rng.normal(0.0, self.noise_scale * self._stds, size=row.shape)
            row = np.where(row == FILL_VALUE, row, row + noise)
            values = dict(zip(self._columns, row, strict=False))
            transaction_id = f"{SYNTHETIC_ID_PREFIX}-{run_tag}-{position:06d}"
            payloads.append(
                {
                    "transaction_id": transaction_id,
                    "values": values,
                    "_synthetic_label": int(self._label[source_index]),
                }
            )
        return payloads


def write_labels_file(
    path: Path | str,
    records: list[dict[str, Any]],
) -> Path:
    """Append synthetic labelled records to a JSONL file.

    Each line: ``{"transaction_id", "is_fraud_synthetic", "score",
    "decision", "_source": "synthetic"}`` — the ``_source`` marker is what
    keeps synthetic labels distinct from real reviewer labels everywhere
    they are consumed.
    """
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("a", encoding="utf-8") as fh:
        for record in records:
            line = {
                "transaction_id": record.get("transaction_id"),
                "is_fraud_synthetic": record.get("_synthetic_label"),
                "score": _finite_or_none(record.get("score")),
                "decision": record.get("decision"),
                "_source": "synthetic",
            }
            fh.write(json.dumps(line) + "\n")
    return out


def _finite_or_none(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None
