"""Stream transactions into the decisioning API (real CSV or synthetic).

Reads rows from a CSV and posts each to ``/api/predict`` one at a time with a
small delay — or, with ``--synthetic N``, generates ``N`` **synthetic**
transactions (bootstrap + noise over the labelled training table, see
``fraud_detect.synthetic``) and streams those instead. Each decision is
persisted, so an analyst watching the SSE feed
(``GET /api/decisions/stream``) or the Operations console sees them arrive
live. This is a **demo** transaction stream, not a real payment feed.

Synthetic transactions carry a known ``_synthetic_label`` (sampled from the
training table) and their API decisions are written to a JSONL labels file
(``--labels-out``) with a ``_source: "synthetic"`` marker — a **trusted
synthetic label source** for the bandit reward function and drift/performance
monitoring. Synthetic labels are never real performance; see
``fraud_detect.synthetic``.

Usage
-----
    python scripts/stream_transactions.py [--csv web/sample_transactions.csv] \\
        [--base http://localhost:8000] [--rate 1.0]
    python scripts/stream_transactions.py --synthetic 200 --rate 0.5 \\
        [--seed 42] [--labels-out data/feedback/synthetic_labels.jsonl]
"""

from __future__ import annotations

import argparse
import json
import math
import time
import urllib.error
import urllib.request
from pathlib import Path

import pandas as pd

from fraud_detect.synthetic import SyntheticGenerator, write_labels_file

#: The model's training-time "missing" fill value (fraud_detect.serving.FILL_VALUE).
#: Empty CSV cells load as NaN; sending NaN in JSON is invalid, so missing cells
#: are posted as -999 — exactly how the serving path treats absent features.
_FILL_VALUE: float = -999.0


def _json_safe(value: object) -> float | None:
    """Convert a CSV cell to a JSON-safe float, or ``None`` if not numeric.

    ``float()`` on an empty cell yields NaN, which ``json.dumps`` would
    serialise as a bare ``NaN`` token (invalid JSON, rejected by the API).
    Non-numeric cells return ``None`` so the caller can drop the feature and
    let the contract default it.
    """
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return _FILL_VALUE if math.isnan(number) else number


def _payload_from_synthetic(row: dict) -> tuple[str, dict[str, float]]:
    """Split one generated payload into (transaction_id, JSON-safe values)."""
    values: dict[str, float] = {}
    for name, value in row["values"].items():
        safe = _json_safe(value)
        if safe is not None:
            values[name] = safe
    return str(row["transaction_id"]), values


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--csv",
        default=str(Path(__file__).resolve().parents[1] / "web" / "sample_transactions.csv"),
        help="CSV source (ignored when --synthetic is set)",
    )
    parser.add_argument("--synthetic", type=int, default=0,
                        help="generate N synthetic transactions instead of reading a CSV")
    parser.add_argument("--seed", type=int, default=None, help="RNG seed for --synthetic")
    parser.add_argument("--fraud-oversample", action="store_true",
                        help="weight fraud rows x5 when sampling synthetic rows")
    parser.add_argument("--labels-out",
                        default=str(
                            Path(__file__).resolve().parents[1]
                            / "data" / "feedback" / "synthetic_labels.jsonl"
                        ),
                        help="JSONL file receiving {transaction_id, is_fraud_synthetic, score, decision}")
    parser.add_argument("--base", default="http://localhost:8000")
    parser.add_argument("--rate", type=float, default=1.0, help="transactions per second")
    args = parser.parse_args()

    if args.synthetic > 0:
        generator = SyntheticGenerator()
        generated = generator.generate(args.synthetic, seed=args.seed,
                                        fraud_oversample=args.fraud_oversample)
        rows = [{"tx": tx, "values": values, "label": row["_synthetic_label"]}
                for row in generated
                for tx, values in [_payload_from_synthetic(row)]]
    else:
        df = pd.read_csv(args.csv)
        feats = [c for c in df.columns if c != "TransactionID"]
        rows = []
        for i, df_row in df.iterrows():
            tx = str(df_row.get("TransactionID", i))
            values: dict[str, float] = {}
            for c in feats:
                value = _json_safe(df_row[c])
                if value is not None:
                    values[c] = value
            rows.append({"tx": tx, "values": values, "label": None})

    interval = 1.0 / max(args.rate, 0.01)

    sent = 0
    labels: list[dict] = []
    for row in rows:
        payload = {"transaction_id": row["tx"], "values": row["values"]}
        request = urllib.request.Request(
            args.base + "/api/predict",
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(request) as response:
                decision = json.loads(response.read())
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            print(f"[{row['tx']}] rejected ({exc.code}): {detail}")
            time.sleep(interval)
            continue
        score = decision.get("probability")
        print(f"[{row['tx']}] score={decision['probability']:.3f} -> {decision['decision']}")
        sent += 1
        if row["label"] is not None and score is not None:
            labels.append(
                {
                    "transaction_id": row["tx"],
                    "_synthetic_label": row["label"],
                    "score": score,
                    "decision": decision.get("decision"),
                }
            )
        time.sleep(interval)

    if labels:
        write_labels_file(args.labels_out, labels)
        print(f"Wrote {len(labels)} synthetic labels to {args.labels_out}")

    print(f"Streamed {sent}/{len(rows)} transactions.")


if __name__ == "__main__":
    main()
