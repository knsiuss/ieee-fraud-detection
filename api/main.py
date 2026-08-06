"""IEEE-CIS Fraud Detection — FastAPI decisioning service (portfolio demo).

Run locally:
    uvicorn api.main:app --reload

Every scoring path loads the **same joblib artefact** through
:func:`fraud_detect.serving.load_artefact` and runs
:func:`fraud_detect.serving.predict_proba`. A strict, versioned feature
contract (:mod:`fraud_detect.contract`) validates raw payloads, a versioned
decision policy (:mod:`fraud_detect.policy`) maps the probability to
APPROVE / MANUAL_REVIEW / DECLINE, and every decision is persisted to a local
SQLite audit store with model/policy/contract versions, reason codes, and
reviewer outcome.

This is a **portfolio demo on public data** — not a production fraud system.

Endpoints
    GET  /api/health
    GET  /api/model
    GET  /api/stats
    POST /api/predict          raw IEEE payload -> decision (idempotent, persisted)
    POST /api/predict/batch    upload a CSV of transactions -> per-row decisions
    POST /api/simulate         demo scenario builder (friendly inputs, labeled)
    POST /api/explain          SHAP explanation for one transaction
    GET  /api/sim/fields       schema for the demo scenario builder
    GET  /api/review/queue     analyst review queue (filterable)
    GET  /api/review/{id}      audit record for one decision
    POST /api/review/{id}/outcome   record reviewer verdict -> retrain pool
    GET  /api/monitor/summary  aggregates over decision history
    POST /api/feedback         legacy reviewer label endpoint
    POST /api/retrain          gated retraining (admin)
"""

from __future__ import annotations

import collections
import io
import os
import time
import uuid
from functools import lru_cache
from typing import Annotated

import pandas as pd
from fastapi import FastAPI, File, Header, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from fraud_detect import sim as simmod
from fraud_detect._exceptions import MissingArtefactError
from fraud_detect.contract import CONTRACT_VERSION, ContractError, validate_payload
from fraud_detect.policy import DecisionPolicy, policy_from_env
from fraud_detect.serving import (
    align_features,
    decision_drivers,
    decision_summary,
    explain_top_features,
    predict_proba,
    risk_tier,
)

from . import schemas, store

app = FastAPI(
    title="IEEE-CIS Fraud Decisioning API (demo)",
    description=(
        "Portfolio demo: raw IEEE-CIS payloads are scored by a joblib LightGBM "
        "artefact, a versioned policy decides APPROVE / MANUAL_REVIEW / DECLINE, "
        "and every decision is audited. Public data only; not a real fraud system."
    ),
    version="0.1.0",
)

# The vanilla-JS frontend may be hosted on a different origin, so allow cross-origin.
# Acceptable for a public demo; restrict in real production.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(MissingArtefactError)
async def _missing_artefact(request: Request, exc: MissingArtefactError):  # noqa: ARG001
    # Return a safe, generic message — never echo the artefact path.
    return JSONResponse(
        {"detail": "Model artefact not found. Run `python scripts/train_model.py` first."},
        status_code=503,
    )


_ADMIN_KEY = os.getenv("FRAUD_API_ADMIN_KEY")

# Simple per-process, per-IP fixed-window rate limit. Documented as in-process
# (not distributed) — enough to keep a public demo from being hammered.
_RATE_LIMIT_PER_MIN = int(os.getenv("FRAUD_API_RATE_LIMIT", "300"))
_RATE_WINDOW: collections.defaultdict[str, collections.deque] = collections.defaultdict(
    collections.deque
)


@app.middleware("http")
async def rate_limit(request: Request, call_next):
    ip = request.client.host if request.client else "unknown"
    now = time.monotonic()
    window = _RATE_WINDOW[ip]
    while window and window[0] < now - 60:
        window.popleft()
    if len(window) >= _RATE_LIMIT_PER_MIN:
        return JSONResponse({"detail": "Rate limit exceeded. Try again shortly."}, status_code=429)
    window.append(now)
    return await call_next(request)


def _env_float(name: str) -> float | None:
    value = os.getenv(name)
    return float(value) if value else None


# Versioned decision policy, configurable without retraining. Override via env.
_POLICY: DecisionPolicy = policy_from_env(
    review_above=_env_float("DECISION_REVIEW_ABOVE"),
    decline_above=_env_float("DECISION_DECLINE_ABOVE"),
)


@lru_cache
def _current():
    """Cached handle to the served artefact; invalidated after a retrain."""
    return store.current_artefact()


def _clear_cache() -> None:
    _current.cache_clear()


def _align_row(values: dict[str, float], art) -> pd.DataFrame:
    """Align raw feature values to the model's exact feature list."""
    return align_features(pd.DataFrame([values]), art.features)


def _decide(values: dict[str, float], transaction_id: str | None) -> tuple[dict, object, str]:
    """Validate -> score (joblib) -> apply policy -> persist. Idempotent."""
    art = _current()
    report = validate_payload(values, art.features)
    x = _align_row(values, art)
    prob = float(predict_proba(art.model, x)[0])
    decision, action = _POLICY.apply(prob)
    tx = transaction_id or uuid.uuid4().hex[:12]

    existing = store.get_decision(tx)
    if existing is not None:
        return existing, art, action

    drivers = decision_drivers(art.model, x, art.features, art.baseline, top_n=3)
    store.record_decision(
        transaction_id=tx,
        model_version=store.version(art),
        contract_version=CONTRACT_VERSION,
        score=prob,
        decision=decision.value,
        policy_version=_POLICY.version,
        thresholds=_POLICY.as_dict(),
        reason_codes=drivers,
        feature_report=report.as_dict(),
        input_features={c: float(x.iloc[0][c]) for c in art.features},
    )
    return store.get_decision(tx), art, action


def _decision_response(record: dict, tier, action: str) -> schemas.PredictResponse:
    return schemas.PredictResponse(
        probability=float(record["score"]),
        risk_tier=tier.label,
        action=action,
        model_version=record["model_version"],
        transaction_id=record["transaction_id"],
        decision=record["decision"],
        policy_version=record["policy_version"],
        contract_version=record["contract_version"],
        feature_report=record["feature_report"],
    )


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


@app.get("/api/stats")
def stats() -> dict:
    return store.public_stats()


@app.post("/api/predict", response_model=schemas.PredictResponse)
def predict(req: schemas.PredictRequest) -> schemas.PredictResponse:
    try:
        record, art, action = _decide(req.values, req.transaction_id)
    except ContractError as exc:
        raise HTTPException(status_code=422, detail=exc.messages) from exc
    tier = risk_tier(float(record["score"]))
    return _decision_response(record, tier, action)


@app.get("/api/sim/fields")
def sim_fields() -> dict:
    return {"fields": simmod.FRIENDLY_FIELDS, "profiles": simmod.PROFILES}


@app.post("/api/simulate", response_model=schemas.SimulateResponse)
def simulate(req: schemas.SimulateRequest) -> schemas.SimulateResponse:
    """Score a **demo scenario** from friendly, checkout-style inputs.

    Friendly fields are mapped onto the model's feature space over a scenario
    profile; the model still sees the full 400-feature schema. The response
    reports exactly which features came from the form vs the profile median.
    """
    art = _current()
    data = req.model_dump()
    row = simmod.build_row(data, art.features, art.baseline, art.profiles)
    prob = float(predict_proba(art.model, row)[0])
    decision, action = _POLICY.apply(prob)
    tier = risk_tier(prob)

    mapped = simmod.map_friendly(data)
    supplied = set(mapped)
    defaulted = [f for f in art.features if f not in supplied]
    feature_report = {
        "counts": {
            "supplied": len(supplied),
            "defaulted": len(defaulted),
            "missing": 0,
            "rejected": 0,
        },
        "fields": {
            f: {
                "status": "supplied" if f in supplied else "defaulted",
                "reason": "scenario profile median",
            }
            for f in art.features
        },
    }
    feature_usage = {
        "profile": req.profile,
        "supplied_features": sorted(supplied),
        "defaulted_count": len(defaulted),
        "note": (
            "Demo scenario builder: only the listed fields were set by the form; "
            "the rest used the scenario profile median."
        ),
    }

    tx = req.transaction_id or uuid.uuid4().hex[:12]
    if store.get_decision(tx) is None:
        drivers = decision_drivers(art.model, row, art.features, art.baseline, top_n=3)
        store.record_decision(
            transaction_id=tx,
            model_version=store.version(art),
            contract_version=CONTRACT_VERSION,
            score=prob,
            decision=decision.value,
            policy_version=_POLICY.version,
            thresholds=_POLICY.as_dict(),
            reason_codes=drivers,
            feature_report=feature_report,
            input_features={c: float(row.iloc[0][c]) for c in art.features},
        )
    record = store.get_decision(tx)

    return schemas.SimulateResponse(
        probability=float(record["score"]),
        risk_tier=tier.label,
        action=action,
        model_version=store.version(art),
        transaction_id=tx,
        decision=record["decision"],
        policy_version=record["policy_version"],
        contract_version=record["contract_version"],
        feature_report=record["feature_report"],
        profile=req.profile,
        mapped_values=mapped,
        feature_usage=feature_usage,
    )


@app.post("/api/predict/batch", response_model=schemas.BatchScoreResponse)
async def predict_batch(
    file: Annotated[UploadFile, File()],
) -> schemas.BatchScoreResponse:
    raw = await file.read()
    if len(raw) > 50 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large (limit 50 MB).")
    try:
        df = pd.read_csv(io.BytesIO(raw))
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail="Could not parse CSV.") from exc

    art = _current()
    id_col = "TransactionID" if "TransactionID" in df.columns else None
    numeric_cols = [c for c in art.features if c in df.columns]
    x = align_features(df, art.features)
    probs = predict_proba(art.model, x)

    compute_reasons = len(df) <= 50
    rows: list[schemas.BatchScoreRow] = []
    errors: list[dict[str, str]] = []
    for i in range(len(df)):
        row_values = {c: df.iloc[i][c] for c in numeric_cols}
        try:
            report = validate_payload(row_values, art.features)
        except ContractError as exc:
            errors.append({"row": str(i), "errors": "; ".join(exc.messages)})
            continue
        prob = float(probs[i])
        decision, action = _POLICY.apply(prob)
        tier = risk_tier(prob)
        tx = str(df.iloc[i][id_col]) if id_col is not None else f"row-{i}"
        if store.get_decision(tx) is None:
            drivers = (
                decision_drivers(art.model, x.iloc[[i]], art.features, art.baseline, top_n=3)
                if compute_reasons
                else None
            )
            store.record_decision(
                transaction_id=tx,
                model_version=store.version(art),
                contract_version=CONTRACT_VERSION,
                score=prob,
                decision=decision.value,
                policy_version=_POLICY.version,
                thresholds=_POLICY.as_dict(),
                reason_codes=drivers,
                feature_report=report.as_dict(),
                input_features={c: float(x.iloc[i][c]) for c in art.features},
            )
        record = store.get_decision(tx)
        rows.append(
            schemas.BatchScoreRow(
                id=(df.iloc[i][id_col] if id_col is not None else i),
                transaction_id=tx,
                probability=float(record["score"]),
                risk_tier=tier.label,
                action=action,
                decision=record["decision"],
                policy_version=record["policy_version"],
                contract_version=record["contract_version"],
            )
        )
    return schemas.BatchScoreResponse(
        model_version=store.version(art),
        count=len(rows),
        rows=rows,
        errors=errors,
    )


@app.post("/api/explain", response_model=schemas.ExplainResponse)
def explain(req: schemas.PredictRequest) -> schemas.ExplainResponse:
    art = _current()
    if req.profile:
        x = simmod.build_row(
            {**req.values, "profile": req.profile},
            art.features,
            art.baseline,
            art.profiles,
        )
    else:
        x = _align_row(req.values, art)
    prob = float(predict_proba(art.model, x)[0])
    tier = risk_tier(prob)

    top = explain_top_features(art.model, x, art.features, top_n=10)
    features = [
        schemas.ShapFeature(
            feature=r.feature,
            contribution=float(r.contribution),
            direction=r.direction,
        )
        for r in top.itertuples()
    ]
    drivers = decision_drivers(art.model, x, art.features, art.baseline, top_n=4)
    summary = decision_summary(prob, tier.label, drivers, tier.action)
    return schemas.ExplainResponse(
        probability=prob,
        risk_tier=tier.label,
        action=tier.action,
        model_version=store.version(art),
        summary=summary,
        drivers=drivers,
        features=features,
    )


@app.get("/api/review/queue")
def review_queue(
    decision: str | None = None,
    status: str | None = None,
    limit: int = 100,
) -> list[dict]:
    return store.list_decisions(decision=decision, status=status, limit=limit)


@app.get("/api/review/{transaction_id}")
def review_detail(transaction_id: str) -> dict:
    record = store.get_decision(transaction_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Decision not found.")
    return record


@app.post("/api/review/{transaction_id}/outcome")
def review_outcome(
    transaction_id: str,
    req: schemas.ReviewOutcomeRequest,
) -> dict:
    updated = store.update_outcome(transaction_id, req.verdict, req.note)
    if updated is None:
        raise HTTPException(status_code=404, detail="Decision not found.")
    return updated


@app.get("/api/monitor/summary")
def monitor_summary() -> dict:
    return store.decision_stats()


@app.post("/api/feedback", response_model=schemas.FeedbackResponse)
def feedback(req: schemas.FeedbackRequest) -> schemas.FeedbackResponse:
    verdict = 1 if (req.verdict in ("fraud", 1)) else 0
    pool_size = store.record_feedback(req.values, verdict)
    return schemas.FeedbackResponse(accepted=True, pool_size=pool_size)


@app.post("/api/retrain", response_model=schemas.RetrainResponse)
def retrain(
    admin_key: str | None = Header(default=None, alias="X-Admin-Key"),
) -> schemas.RetrainResponse:
    _require_admin(admin_key)
    try:
        result = store.retrain_and_swap()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    _clear_cache()
    return schemas.RetrainResponse(**result)


# Serve the vanilla-JS frontend from the same process when the web/ dir exists,
# so a single `uvicorn api.main:app` runs the whole app locally.
_WEB_DIR = os.path.join(os.path.dirname(__file__), "..", "web")
if os.path.isdir(_WEB_DIR):
    app.mount("/", StaticFiles(directory=_WEB_DIR, html=True), name="web")
