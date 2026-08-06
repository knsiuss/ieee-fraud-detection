"""Run the gated auto-retrain loop.

Folds reviewer feedback (from the API's /api/feedback) into the training set,
trains a LightGBM candidate, and swaps it into ``data/models/current`` **only
if it beats the served model on a held-out validation split**. A candidate
that fails the gate never touches the served model, so running this on a
schedule cannot silently degrade production.

Run
---
    python scripts/retrain.py [--data PATH]

    # cron: every day at 04:07 local time once you have trained the baseline
    7 4 * * *  cd /path/to/repo && python scripts/retrain.py >> retrain.log 2>&1
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import pandas as pd  # noqa: E402

from api import store  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--data",
        default=None,
        help="Optional training table override (default: processed -> merged -> sample).",
    )
    args = parser.parse_args()

    data_df: pd.DataFrame | None = None
    if args.data:
        path = Path(args.data)
        data_df = pd.read_parquet(path) if path.suffix == ".parquet" else pd.read_csv(path)

    result = store.retrain_and_swap(data_df=data_df)
    print(
        f"[retrain] swapped={result['swapped']} "
        f"old_auc={result['old_auc']:.5f} new_auc={result['new_auc']:.5f} "
        f"feedback_rows={result['feedback_rows']} — {result['reason']}"
    )


if __name__ == "__main__":
    main()