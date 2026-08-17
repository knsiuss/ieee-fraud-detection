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
    GET  /api/decisions/stream live SSE feed of decisions (no raw features)
"""

from __future__ import annotations

import asyncio
import collections
import io
import json
import os
import re
import time
import uuid
from functools import lru_cache
from typing import Annotated

import pandas as pd
from fastapi import (
    BackgroundTasks,
    FastAPI,
    File,
    Header,
    HTTPException,
    Query,
    Request,
    UploadFile,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from fraud_detect import bandit_policy
from fraud_detect import sim as simmod
from fraud_detect._exceptions import MissingArtefactError
from fraud_detect.bandit_policy import BANDIT_VERSION, BanditPolicy
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
        "demo: raw IEEE-CIS payloads are scored by a joblib LightGBM "
        "artefact, a versioned policy decides APPROVE / MANUAL_REVIEW / DECLINE, "
        "and every decision is audited. Public data only; not a real fraud system."
    ),
    version="0.1.0",
)

_CORS_ORIGINS = [
    o.strip()
    for o in os.getenv(
        "FRAUD_CORS_ORIGINS",
        "http://localhost:8000,http://127.0.0.1:8000,http://localhost:3000,http://127.0.0.1:3000,http://localhost:5173,http://127.0.0.1:5173",
    ).split(",")
    if o.strip()
]
_ALLOW_ALL_ORIGINS = os.getenv("FRAUD_ALLOW_ALL_ORIGINS", "0") == "1"

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if _ALLOW_ALL_ORIGINS else _CORS_ORIGINS,
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
_RETRAIN_LOCK = asyncio.Lock()
_TX_ID_REGEX = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")


def _validate_transaction_id(tx_id: str) -> None:
    if not _TX_ID_REGEX.match(tx_id):
        raise HTTPException(
            status_code=422,
            detail=(
                "Invalid transaction_id format. Allowed: 1-128 alphanumeric "
                "characters, '.', '_', ':', or '-'."
            ),
        )


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

# Adaptive decision layer (policy v2 — contextual bandit). Opt-in via env so
# policy v1 remains the default and both versions coexist auditably.
_BANDIT_ENABLED = os.getenv("FRAUD_BANDIT_ENABLED", "0") == "1"
_BANDIT_POLICY = BanditPolicy(
    version=BANDIT_VERSION,
    alpha=float(os.getenv("FRAUD_BANDIT_ALPHA", "1.0")),
    epsilon=float(os.getenv("FRAUD_BANDIT_EPSILON", "0.10")),
    auto_action_above=float(os.getenv("FRAUD_AUTO_ACTION_ABOVE", "0.95")),
    audit_sample_rate=float(os.getenv("FRAUD_AUDIT_SAMPLE_RATE", "0.05")),
)
_BANDIT_STATE = store.load_bandit_state()
_BANDIT_PROMOTE_LOCK = asyncio.Lock()

#: Cold-start threshold: the bandit only takes over decisioning once the live
#: checkpoint has collected this many rewarded outcomes. Before that it would
#: act on an empty state, where every arm ties and the greedy tie-break
#: (first action in ACTIONS) approves everything below the auto-action
#: cutoff — dangerous for a fraud system. Deferring to policy v1 keeps the
#: decline threshold active until the bandit has real signal.
_BANDIT_MIN_REWARDS = int(os.getenv("FRAUD_BANDIT_MIN_REWARDS", "20"))

#: Report generation is decoupled from the scoring path; a generous cap keeps
#: batch uploads from flooding the (optionally local) LLM.
MAX_REPORT_ROWS: int = 50


@lru_cache
def _current():
    """Cached handle to the served artefact; invalidated after a retrain."""
    return store.current_artefact()


def _clear_cache() -> None:
    _current.cache_clear()


def _align_row(values: dict[str, float], art) -> pd.DataFrame:
    """Align raw feature values to the model's exact feature list."""
    return align_features(pd.DataFrame([values]), art.features)


def _batch_transaction_id(value: object, index: int) -> str:
    """Stable, human-friendly transaction id for one CSV row.

    pandas reads numeric TransactionID columns as floats, so a raw ``str()``
    turns 3152017 into '3152017.0'. Empty cells become NaN which ``str()``
    renders as 'nan' — collapsing every such row onto a single record in the
    idempotent decision store. Integers are kept exact, strings pass through
    unchanged, and missing values get a unique ``row-<index>`` fallback.
    """
    try:
        if value is None or pd.isna(value):
            return f"row-{index}"
    except (TypeError, ValueError):
        pass
    if isinstance(value, str):
        return value
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    return str(int(number)) if number.is_integer() else str(number)


def _decide(
    values: dict[str, float],
    transaction_id: str | None,
    background: BackgroundTasks | None = None,
) -> tuple[dict, object, str]:
    """Validate -> check idempotency -> score (joblib) -> apply policy -> persist.

    ``background`` is optional: when provided, DECLINE / MANUAL_REVIEW
    decisions schedule the LLM audit report (decoupled from the response).
    """
    art = _current()
    report = validate_payload(values, art.features)
    tx = transaction_id or uuid.uuid4().hex[:12]
    if transaction_id:
        _validate_transaction_id(tx)

    existing = store.get_decision(tx)
    if existing is not None:
        return existing, art, _action_for_record(existing)

    x = _align_row(values, art)
    prob = float(predict_proba(art.model, x)[0])

    input_features = {c: float(x.iloc[0][c]) for c in art.features}
    drivers = decision_drivers(art.model, x, art.features, art.baseline, top_n=3)
    decided = _decide_with_policy(prob, drivers, input_features)

    if decided["bandit_event"] is not None:
        store.record_bandit_event(transaction_id=tx, **decided["bandit_event"])
    store.record_decision(
        transaction_id=tx,
        model_version=store.version(art),
        contract_version=CONTRACT_VERSION,
        score=prob,
        decision=decided["decision"],
        action=decided["action"],
        policy_version=decided["policy_version"],
        thresholds=decided["thresholds"],
        reason_codes=drivers,
        feature_report=report.as_dict(),
        input_features=input_features,
    )
    if background is not None and decided["decision"] in ("DECLINE", "MANUAL_REVIEW"):
        _schedule_report(background, tx)
    return store.get_decision(tx), art, decided["action"]


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


def _action_for_record(record: dict) -> str:
    """Return the action originally persisted with a decision.

    The fallback supports rows created before the ``action`` column existed.
    New records always persist the original action so later policy changes
    cannot make a replayed response contradict its stored decision.
    """
    action = record.get("action")
    if action:
        return str(action)
    return _POLICY.actions[str(record["decision"])]


def _decide_with_policy(
    prob: float,
    drivers: list[dict],
    input_features: dict[str, float],
) -> dict:
    """Apply policy v1 (threshold) or v2 (bandit), returning decision fields.

    Policy v2 reuses exactly the signals v1 already receives — probability,
    SHAP drivers, input features — so explanation parity is free: drivers are
    computed once, by the caller, and used both for the SHAP reason codes and
    as the bandit context.
    """
    bandit_ready = _BANDIT_ENABLED and _BANDIT_STATE.n_rewards >= _BANDIT_MIN_REWARDS
    if not bandit_ready:
        decision, action = _POLICY.apply(prob)
        return {
            "decision": decision.value,
            "action": action,
            "policy_version": _POLICY.version,
            "thresholds": _POLICY.as_dict(),
            "bandit_event": None,
        }

    context = bandit_policy.build_context(prob, drivers, input_features)
    choice = _BANDIT_POLICY.decide(prob, context, _BANDIT_STATE)
    bandit_event = {
        "policy_version": _BANDIT_POLICY.version,
        "action": choice.decision.value,
        "score": float(prob),
        "propensity": choice.propensity,
        "explored": choice.explored,
        "auto_actioned": choice.auto_actioned,
        "audit_sampled": choice.audit_sampled,
        "context": context,
    }
    return {
        "decision": choice.decision.value,
        "action": choice.action,
        "policy_version": _BANDIT_POLICY.version,
        "thresholds": {
            **_BANDIT_POLICY.as_dict(),
            # The bandit has no review/decline thresholds of its own, but the
            # audit report and LLM prompt read them from the stored decision —
            # carry the v1 policy's so reports never fall back to fabricated
            # defaults (0.15 / 0.50) that disagree with the deployed config.
            "review_above": _POLICY.review_above,
            "decline_above": _POLICY.decline_above,
            "needs_review": choice.needs_review,
            "reason_code": choice.reason_code,
            "action_probs": choice.action_probs,
        },
        "bandit_event": bandit_event,
    }


async def _generate_report_async(transaction_id: str) -> None:
    """Run report generation on a worker thread (never blocks scoring)."""
    await asyncio.to_thread(store.generate_audit_report, transaction_id)


def _schedule_report(background: BackgroundTasks, transaction_id: str) -> None:
    """Queue LLM report generation for DECLINE / MANUAL_REVIEW decisions."""
    background.add_task(_generate_report_async, transaction_id)


def _require_admin(admin_key: str | None, operation: str) -> None:
    if not _ADMIN_KEY:
        raise HTTPException(
            status_code=503,
            detail=f"{operation} is disabled: FRAUD_API_ADMIN_KEY is not configured.",
        )
    if admin_key != _ADMIN_KEY:
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
def predict(
    req: schemas.PredictRequest,
    background: BackgroundTasks,
) -> schemas.PredictResponse:
    try:
        record, art, action = _decide(req.values, req.transaction_id, background)
    except ContractError as exc:
        raise HTTPException(status_code=422, detail=exc.messages) from exc
    tier = risk_tier(float(record["score"]))
    return _decision_response(record, tier, action)


@app.get("/api/sim/fields")
def sim_fields() -> dict:
    return {"fields": simmod.FRIENDLY_FIELDS, "profiles": simmod.PROFILES}


@app.post("/api/simulate", response_model=schemas.SimulateResponse)
def simulate(
    req: schemas.SimulateRequest,
    background: BackgroundTasks,
) -> schemas.SimulateResponse:
    """Score a **demo scenario** from friendly, checkout-style inputs.

    Friendly fields are mapped onto the model's feature space over a scenario
    profile; the model still sees the full 400-feature schema. The response
    reports exactly which features came from the form vs the profile median.
    """
    art = _current()
    data = req.model_dump()
    tx = req.transaction_id or uuid.uuid4().hex[:12]
    if req.transaction_id:
        _validate_transaction_id(tx)

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

    existing = store.get_decision(tx)
    if existing is not None:
        record = existing
        prob = float(record["score"])
    else:
        row = simmod.build_row(data, art.features, art.baseline, art.profiles)
        prob = float(predict_proba(art.model, row)[0])
        input_features = {c: float(row.iloc[0][c]) for c in art.features}
        drivers = decision_drivers(art.model, row, art.features, art.baseline, top_n=3)
        decided = _decide_with_policy(prob, drivers, input_features)
        if decided["bandit_event"] is not None:
            store.record_bandit_event(transaction_id=tx, **decided["bandit_event"])
        store.record_decision(
            transaction_id=tx,
            model_version=store.version(art),
            contract_version=CONTRACT_VERSION,
            score=prob,
            decision=decided["decision"],
            action=decided["action"],
            policy_version=decided["policy_version"],
            thresholds=decided["thresholds"],
            reason_codes=drivers,
            feature_report=feature_report,
            input_features=input_features,
        )
        if decided["decision"] in ("DECLINE", "MANUAL_REVIEW"):
            _schedule_report(background, tx)
        record = store.get_decision(tx)

    action = _action_for_record(record)
    tier = risk_tier(float(record["score"]))
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
async def predict_batch(  # noqa: PLR0915 - row loop carries the full decision pipeline
    file: Annotated[UploadFile, File()],
    background: BackgroundTasks,
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
        tier = risk_tier(prob)
        raw_id = df.iloc[i][id_col] if id_col is not None else None
        try:
            has_id = not pd.isna(raw_id)
        except (TypeError, ValueError):
            has_id = True
        tx = _batch_transaction_id(raw_id, i) if id_col is not None else f"row-{i}"
        try:
            _validate_transaction_id(tx)
        except HTTPException as exc:
            errors.append({"row": str(i), "errors": str(exc.detail)})
            continue
        existing = store.get_decision(tx)
        if existing is None:
            drivers = (
                decision_drivers(art.model, x.iloc[[i]], art.features, art.baseline, top_n=3)
                if compute_reasons
                else None
            )
            input_features = {c: float(x.iloc[i][c]) for c in art.features}
            decided = (
                _decide_with_policy(prob, drivers or [], input_features)
                if drivers is not None
                else None
            )
            if decided is None:
                decision, action = _POLICY.apply(prob)
                decided = {
                    "decision": decision.value,
                    "action": action,
                    "policy_version": _POLICY.version,
                    "thresholds": _POLICY.as_dict(),
                    "bandit_event": None,
                }
            if decided["bandit_event"] is not None:
                store.record_bandit_event(transaction_id=tx, **decided["bandit_event"])
            store.record_decision(
                transaction_id=tx,
                model_version=store.version(art),
                contract_version=CONTRACT_VERSION,
                score=prob,
                decision=decided["decision"],
                action=decided["action"],
                policy_version=decided["policy_version"],
                thresholds=decided["thresholds"],
                reason_codes=drivers,
                feature_report=report.as_dict(),
                input_features=input_features,
            )
            if (
                drivers is not None
                and decided["decision"]
                in (
                    "DECLINE",
                    "MANUAL_REVIEW",
                )
                and len(rows) < MAX_REPORT_ROWS
            ):
                _schedule_report(background, tx)
            record = store.get_decision(tx)
        else:
            record = existing
            prob = float(record["score"])
            tier = risk_tier(prob)

        action = _action_for_record(record)
        rows.append(
            schemas.BatchScoreRow(
                id=raw_id if (id_col is not None and has_id) else tx,
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
    limit: int = Query(default=100, ge=1, le=200),
) -> list[dict]:
    records = store.list_decisions(decision=decision, status=status, limit=limit)
    return [{k: v for k, v in r.items() if k != "input_features"} for r in records]


@app.get("/api/review/{transaction_id}")
def review_detail(
    transaction_id: str,
    admin_key: str | None = Header(default=None, alias="X-Admin-Key"),
) -> dict:
    _validate_transaction_id(transaction_id)
    record = store.get_decision(transaction_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Decision not found.")
    if not _ADMIN_KEY or admin_key != _ADMIN_KEY:
        record = {k: v for k, v in record.items() if k != "input_features"}
    return record


def _verify_admin_if_configured(admin_key: str | None) -> None:
    if _ADMIN_KEY and admin_key != _ADMIN_KEY:
        raise HTTPException(
            status_code=403,
            detail="Forbidden: invalid or missing admin key.",
        )


@app.post("/api/review/{transaction_id}/outcome")
def review_outcome(
    transaction_id: str,
    req: schemas.ReviewOutcomeRequest,
    admin_key: str | None = Header(default=None, alias="X-Admin-Key"),
) -> dict:
    _verify_admin_if_configured(admin_key)
    _validate_transaction_id(transaction_id)
    updated = store.update_outcome(transaction_id, req.verdict, req.note)
    if updated is None:
        raise HTTPException(status_code=404, detail="Decision not found.")
    return {k: v for k, v in updated.items() if k != "input_features"}


@app.get("/api/monitor/summary")
def monitor_summary() -> dict:
    return store.decision_stats()


@app.get("/api/metrics/summary")
def metrics_summary() -> dict:
    """Live computed summary of decision volume, splits, latency, and loss prevention."""
    return store.metrics_summary()


@app.get("/api/metrics/timeseries")
def metrics_timeseries(
    w: int = Query(default=60, description="Window in minutes", ge=1, le=1440),
    bucket: int = Query(default=60, description="Bucket size in seconds", ge=5, le=3600),
) -> list[dict]:
    """Time-bucketed metrics for transaction velocity, volume, and score trends."""
    return store.metrics_timeseries(window_minutes=w, bucket_seconds=bucket)


@app.get("/api/metrics/dispositions")
def metrics_dispositions() -> dict:
    """Decision outcomes joined with human review ground truth."""
    return store.metrics_dispositions()


@app.get("/api/metrics/loss")
def metrics_loss() -> dict:
    """Financial loss prevention, review exposure, and cleared volume."""
    return store.metrics_loss()


@app.get("/api/metrics/rules")
def metrics_rules() -> list[dict]:
    """Top SHAP risk drivers rolled up into a rule-performance table."""
    return store.metrics_rules()


def _sse_frames(records: list[dict], seen: set[str]) -> list[str]:
    """Build SSE ``decision`` frames for the records not yet in ``seen``.

    A transaction is only emitted once per connection (``seen`` is the
    connection's own de-dupe set). Raw input features are never put on the
    wire — only the decision metadata. Extracted from the stream endpoint so
    the framing contract is unit-testable (tests/test_api.py).
    """
    frames = []
    for record in records:
        tx_id = record["transaction_id"]
        if tx_id in seen:
            continue
        seen.add(tx_id)
        frame = {k: v for k, v in record.items() if k != "input_features"}
        frames.append(f"id: {tx_id}\nevent: decision\ndata: {json.dumps(frame)}\n\n")
    return frames


@app.get("/api/decisions/stream")
async def decisions_stream():
    """Server-Sent-Events stream of decisions as they are recorded.

    Emits an initial burst of the current queue, then new decisions as
    transactions stream in (ingested via /api/predict, batch, or simulate).
    Frames omit the raw input features (no sensitive-feature exposure by
    default). Consume with `new EventSource("/api/decisions/stream")`.

    Note: every new connection starts with a fresh ``seen`` set, so an
    EventSource reconnect (which happens automatically after any drop)
    replays the current queue. The client is therefore responsible for
    de-duplicating by ``transaction_id`` — handled in the React frontend by
    ``web/src/stores/useLiveStore.ts`` (``addDecisions`` ring buffer). Each
    frame also carries an SSE ``id:`` field so a client could resume via
    Last-Event-ID instead.
    """

    async def gen():
        seen: set[str] = set()
        while True:
            for frame in _sse_frames(store.list_decisions(limit=200), seen):
                yield frame
            await asyncio.sleep(1.0)

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@app.post("/api/feedback", response_model=schemas.FeedbackResponse)
def feedback(
    req: schemas.FeedbackRequest,
) -> schemas.FeedbackResponse:
    verdict = 1 if (req.verdict in ("fraud", 1)) else 0
    pool_size = store.record_feedback(req.values, verdict)
    return schemas.FeedbackResponse(accepted=True, pool_size=pool_size)


@app.post("/api/retrain", response_model=schemas.RetrainResponse)
async def retrain(
    admin_key: str | None = Header(default=None, alias="X-Admin-Key"),
) -> schemas.RetrainResponse:
    _require_admin(admin_key, "Retraining endpoint")
    if _RETRAIN_LOCK.locked():
        raise HTTPException(
            status_code=429,
            detail="Retraining is already in progress. Please wait for completion.",
        )
    async with _RETRAIN_LOCK:
        try:
            result = await asyncio.to_thread(store.retrain_and_swap)
        except RuntimeError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        _clear_cache()
        return schemas.RetrainResponse(**result)


@app.get("/api/bandit/status")
def bandit_status() -> dict:
    """Status of the adaptive decision layer (policy v2), enabled or not."""
    return {
        "enabled": _BANDIT_ENABLED,
        "policy": _BANDIT_POLICY.as_dict() if _BANDIT_ENABLED else None,
        "checkpoint_version": _BANDIT_STATE.version if _BANDIT_ENABLED else None,
        "summary": store.bandit_summary(),
    }


@app.post("/api/bandit/promote")
async def bandit_promote(
    admin_key: str | None = Header(default=None, alias="X-Admin-Key"),
) -> dict:
    """Off-policy promotion gate for the bandit policy (mirrors the retrain gate).

    Fits a candidate state on the rewarded event log and promotes it only if
    its IPS-estimated expected reward ≥ the live policy's. A losing candidate
    is archived under ``data/models/bandit/bandit_archive_<ts>.json``.
    """
    _require_admin(admin_key, "Bandit promotion endpoint")
    if not _BANDIT_ENABLED:
        raise HTTPException(
            status_code=503,
            detail="Adaptive decision layer disabled; set FRAUD_BANDIT_ENABLED=1.",
        )
    if _BANDIT_PROMOTE_LOCK.locked():
        raise HTTPException(
            status_code=429,
            detail="Bandit promotion is already in progress.",
        )
    global _BANDIT_STATE  # noqa: PLW0603 - single writer: the promote gate
    async with _BANDIT_PROMOTE_LOCK:
        result = await asyncio.to_thread(store.promote_bandit_state)
        if result.get("promoted"):
            _BANDIT_STATE = store.load_bandit_state()
        return result


@app.get("/api/review/{transaction_id}/report")
def audit_report(
    transaction_id: str,
) -> dict:
    """Fetch the stored LLM/template audit report for one decision."""
    _validate_transaction_id(transaction_id)
    report = store.get_audit_report(transaction_id)
    if report is None:
        raise HTTPException(
            status_code=404,
            detail="No audit report for this decision (only DECLINE / MANUAL_REVIEW "
            "get reports, and generation runs asynchronously).",
        )
    return report


@app.post("/api/review/{transaction_id}/appeal")
def audit_appeal(
    transaction_id: str,
    req: schemas.AppealRequest | None = None,
    admin_key: str | None = Header(default=None, alias="X-Admin-Key"),
) -> dict:
    """Lightweight reversal path: overturn a decision to 'safe' with one click.

    Guards the mass-false-positive failure mode: a fast, human-reviewable
    explanation (the audit report) plus a fast reversal path. The overturn is
    recorded as a normal reviewer outcome, so it audits and feeds the retrain
    pool like any other verdict.
    """
    _verify_admin_if_configured(admin_key)
    _validate_transaction_id(transaction_id)
    record = store.get_decision(transaction_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Decision not found.")
    if record.get("reviewer_outcome") == "fraud":
        raise HTTPException(
            status_code=422,
            detail="Cannot appeal a decision already confirmed as fraud.",
        )
    note = req.note if req is not None else None
    updated = store.update_outcome(transaction_id, "safe", note or "Appealed (overturned).")
    return {k: v for k, v in updated.items() if k != "input_features"}


# Serve the React SPA from the production build (web/dist/). Run `npm run build`
# in web/ before starting the server; during development use `npm run dev`
# (Vite proxies /api to the backend on :5173).
_DIST_DIR = os.path.join(os.path.dirname(__file__), "..", "web", "dist")
_INDEX_FILE = os.path.join(_DIST_DIR, "index.html")

if os.path.isdir(_DIST_DIR) and os.path.isfile(_INDEX_FILE):
    _ASSETS_DIR = os.path.join(_DIST_DIR, "assets")
    if os.path.isdir(_ASSETS_DIR):
        app.mount("/assets", StaticFiles(directory=_ASSETS_DIR), name="assets")

    _EXCLUDED_SPA_PREFIXES = (
        "api",
        "gradio",
        "docs",
        "redoc",
        "openapi.json",
        "config",
        "info",
        "theme.css",
        "custom.css",
        "heartbeat",
        "queue",
    )

    @app.get("/{full_path:path}", include_in_schema=False)
    async def _spa_catchall(full_path: str):
        path_clean = full_path.strip("/")
        if any(path_clean == prefix or path_clean.startswith(f"{prefix}/") for prefix in _EXCLUDED_SPA_PREFIXES):
            raise HTTPException(status_code=404, detail="Not Found")
        file_path = os.path.join(_DIST_DIR, full_path)
        if full_path and os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(_INDEX_FILE)
