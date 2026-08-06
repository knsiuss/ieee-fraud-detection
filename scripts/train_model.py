"""Train the production LightGBM model and serialise it for serving.

Writes a model version into ``data/models/current/`` so the FastAPI service
can load it without retraining. The artefact bundle (``model.joblib`` +
``features.json`` + ``baseline.json`` + ``meta.json``) is produced by
:func:`fraud_detect.serving.save_artefact`.

Usage
-----
    python scripts/train_model.py [--data PATH] [--out DIR] [--backend lightgbm]

Data resolution order
---------------------
1. ``--data`` if given
2. ``data/processed/train_features.parquet`` (engineered table, notebooks 07+)
3. ``data/interim/train_merged.parquet`` (merged table, notebook 01)
4. ``dashboard/data/sample.parquet`` (committed demo sample — lets the
   service bootstrap on a fresh checkout without the Kaggle download)

The model is trained on numeric columns only (see
:func:`fraud_detect.models.select_feature_columns`); object columns are
dropped, matching the serving paths.
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

_SRC = Path(__file__).resolve().parents[1] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

import pandas as pd  # noqa: E402

from fraud_detect import config, tuning  # noqa: E402
from fraud_detect.models import ModelBackend, select_feature_columns, train_model  # noqa: E402
from fraud_detect.serving import median_baseline, save_artefact  # noqa: E402


def resolve_data(path: str | None) -> Path:
    """Pick the first available training table."""
    candidates = [
        Path(path) if path else None,
        config.PROCESSED_TRAIN_PATH,
        config.MERGED_TRAIN_PATH,
        Path(__file__).resolve().parents[1] / "dashboard" / "data" / "sample.parquet",
    ]
    for c in candidates:
        if c is not None and c.exists():
            return c
    raise FileNotFoundError(
        "No training data found. Pass --data or download the Kaggle dataset and "
        "run notebook 01 (and 07 for engineered features)."
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", default=None, help="Path to a training parquet/CSV.")
    parser.add_argument(
        "--out",
        default=str(config.MODEL_DIR / "current"),
        help="Directory to write the model artefact into.",
    )
    parser.add_argument(
        "--backend",
        default="lightgbm",
        choices=[b.value for b in ModelBackend],
        help="Model backend to train (default: lightgbm).",
    )
    args = parser.parse_args()

    data_path = resolve_data(args.data)
    print(f"Loading training table: {data_path}")
    df = pd.read_parquet(data_path) if data_path.suffix == ".parquet" else pd.read_csv(data_path)

    backend = ModelBackend(args.backend)

    # Merge tuned hyperparameters (if any are saved) onto the base defaults so
    # the model keeps the full objective/metric/verbosity configuration.
    tuned = tuning.load_best_params(backend, fallback_to_defaults=True)
    params = {**config.LGBM_PARAMS, **tuned} if backend is ModelBackend.LIGHTGBM else tuned

    print(f"Training {backend.value} on {len(df):,} rows …")
    result = train_model(df, backend=backend, params=params)

    features = select_feature_columns(df)
    baseline = median_baseline(features, df)
    meta = {
        "backend": backend.value,
        "roc_auc": result.val_auc,
        "train_auc": result.train_auc,
        "n_rows": int(len(df)),
        "n_features": len(features),
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "data_source": str(data_path),
    }

    out = save_artefact(
        args.out,
        result.model,
        features,
        baseline,
        meta,
    )
    print(f"Artefact written to {out}")
    print(f"  features: {len(features)} | ROC-AUC (val): {result.val_auc:.5f}")


if __name__ == "__main__":
    main()
