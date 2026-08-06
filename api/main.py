"""IEEE-CIS Fraud Detection — FastAPI service.

Run locally:
    uvicorn api.main:app --reload

The service serves the trained LightGBM artefact for single / batch scoring,
explains individual predictions with SHAP, collects reviewer feedback, and
offers a gated auto-retrain endpoint.

Endpoints
    GET  /api/health
    GET  /api/model
    POST /api/predict          single-transaction score
    POST /api/predict/batch    score an uploaded CSV of transactions
    POST /api/explain          SHAP explanation for one transaction
    POST /api/feedback         persist a reviewer label into the retrain pool
    POST /api/retrain          train a candidate; swap if it beats the gate
"""

from __future__ import annotations

import io
import os
from functools import lru_cache

import pandas as pd
from fastapi import FastAPI, File, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from fraud_detect.serving import (
    align_features,
    explain_top_features,
    median_baseline,
    predict_proba,
    risk_tier,
)

from . import schemas, store

app = FastAPI(
    title="IEEE-CIS Fraud Detection API",
    description="Fraud probability scoring with SHAP explanations and gated retraining.",
    version="0.1.0",
)

# The vanilla-JS frontend is served from a different origin, so allow cross-origin.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_ADMIN_KEY = os.getenv("FRAUD_API_ADMIN_KEY")


@lru_cache()
def _current():
    """Cached handle to the served artefact; invalidated after a retrain."""
    return store.current_artefact()


def _clear_cache() -> None:
    _current.cache_clear()


def _build_row(values: dict[str, float], art) -> pd.DataFrame:
    """Start from the training median and overlay the analyst's inputs."""
    row = art.baseline.copy()
    for k, v in values.items():
        if k in art.features:
            row.loc[0, k] = float(v)
    return align_features(row, art.features)


def _score(values: dict[str, float]):
    """Return (probability, tier, action, version) for one transaction."""
    art = _current()
    X = _build_row(values, art)
    prob = float(predict_proba(art.model, X)[0])
    tier = risk_tier(prob)
    return prob, tier, store.version(art)


def _require_admin(admin_key: str | None) -> None:
    if _ADMIN_KEY and admin_key != _ADMIN_KEY:
        raise HTTPException(status_code=403, detail="Invalid admin key.")


@app.get("/api/health", response_model=schemas.HealthResponse)
def health() -> schemas.HealthResponse:
    try:
        art = _current()
        return schemas.HealthResponse(
            status="ok",
            model_present=True,
            model_version=store.version(art),
        )
    except Exception:
        return schemas.HealthResponse(status="ok", model_present=False)


@app.get("/api/model")
def model_info() -> dict:
    return store.model_info()


@app.post("/api/predict", response_model=schemas.PredictResponse)
def predict(req: schemas.PredictRequest) -> schemas.PredictResponse:
    prob, tier, version = _score(req.values)
    return schemas.PredictResponse(
        probability=prob, risk_tier=tier.label, action=tier.action, model_version=version
    )


@app.post("/api/predict/batch", response_model=schemas.BatchScoreResponse)
async def predict_batch(file: UploadFile = File(...)) -> schemas.BatchScoreResponse:
    raw = await file.read()
    if len(raw) > 50 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large (limit 50 MB).")
    try:
        df = pd.read_csv(io.BytesIO(raw))
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail="Could not parse CSV.") from exc

    art = _current()
    X = align_features(df, art.features)
    probs = predict_proba(art.model, X)

    id_col = "TransactionID" if "TransactionID" in df.columns else None
    rows: list[schemas.BatchScoreRow] = []
    for i in range(len(df)):
        tier = risk_tier(float(probs[i]))
        rows.append(
            schemas.BatchScoreRow(
                id=(df.iloc[i][id_col] if id_col is not None else i),
                probability=float(probs[i]),
                risk_tier=tier.label,
                action=tier.action,
                values={},
            )
        )
    return schemas.BatchScoreResponse(
        model_version=store.version(art),
        count=len(rows),
        rows=rows,
    )


@app.post("/api/explain", response_model=schemas.ExplainResponse)
def explain(req: schemas.PredictRequest) -> schemas.ExplainResponse:
    art = _current()
    X = _build_row(req.values, art)
    prob = float(predict_proba(art.model, X)[0])
    tier = risk_tier(prob)
    top = explain_top_features(art.model, X, art.features, top_n=10)
    features = [
        schemas.ShapFeature(
            feature=r.feature,
            contribution=float(r.contribution),
            direction=r.direction,
        )
        for r in top.itertuples()
    ]
    return schemas.ExplainResponse(
        probability=prob,
        risk_tier=tier.label,
        action=tier.action,
        model_version=store.version(art),
        features=features,
    )


@app.post("/api/feedback", response_model=schemas.FeedbackResponse)
def feedback(req: schemas.FeedbackRequest) -> schemas.FeedbackResponse:
    verdict = 1 if (req.verdict in ("fraud", 1)) else 0
    pool_size = store.record_feedback(req.values, verdict)
    return schemas.FeedbackResponse(accepted=True, pool_size=pool_size)


@app.post("/api/retrain", response_model=schemas.RetrainResponse)
def retrain(admin_key: str | None = Header(default=None)) -> schemas.RetrainResponse:
    _require_admin(admin_key)
    result = store.retrain_and_swap()
    _clear_cache()
    return schemas.RetrainResponse(**result)


# Serve the vanilla-JS frontend from the same process when the web/ dir exists,
# so a single `uvicorn api.main:app` runs the whole app locally.
_WEB_DIR = os.path.join(os.path.dirname(__file__), "..", "web")
if os.path.isdir(_WEB_DIR):
    app.mount("/", StaticFiles(directory=_WEB_DIR, html=True), name="web")