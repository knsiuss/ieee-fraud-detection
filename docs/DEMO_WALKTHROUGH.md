# Demo walkthrough

An end-to-end pass through the **Fraud Decisioning API and Analyst
Operations Console**. Every number below is a real output from the running
service on the committed demo model. The model is a **joblib LightGBM
artefact** loaded via `fraud_detect.serving.load_artefact`; every scoring
path (single, batch, demo scenario) goes through it.

## 0. Start the service

```bash
pip install -e ".[lgbm,dev]"
python scripts/train_model.py      # builds data/models/current (or use the committed sample)
uvicorn api.main:app --reload      # http://localhost:8000
```

## 1. A client sends a transaction through the versioned API

Raw IEEE-compatible payload (400 numeric features) with an idempotency key:

```bash
curl -X POST http://localhost:8000/api/predict \
  -H "Content-Type: application/json" \
  -d '{"transaction_id":"w-1001","values":{ ...400 feature:value pairs... }}'
```

The service validates the exact **feature contract**: unknown fields and
missing critical fields (`TransactionAmt, card1, C1, D1`) are rejected with
actionable 422 errors — nothing is silently filled.

## 2. Joblib score response

```json
{
  "probability": 0.149,
  "risk_tier": "low",
  "action": "Approve. Probability below the review threshold.",
  "model_version": "2026-08-06T08:15",
  "transaction_id": "w-1001",
  "decision": "APPROVE",
  "policy_version": "v1",
  "contract_version": "v1",
  "feature_report": { "counts": { "supplied": 400, "defaulted": 0, "missing": 0, "rejected": 0 }, "fields": { ... } }
}
```

`probability` is produced by `serving.predict_proba` on the loaded joblib
artefact; the **versioned policy** (`fraud_detect.policy`, thresholds
`review ≥ 0.15`, `decline ≥ 0.50`) maps it to `APPROVE`. The response also
reports the per-field contract status.

## 3. The decision record (audit)

```bash
curl http://localhost:8000/api/review/w-1001
```

```json
{
  "transaction_id": "w-1001",
  "timestamp": "2026-08-07T00:22:06Z",
  "model_version": "2026-08-06T08:15",
  "contract_version": "v1",
  "policy_version": "v1",
  "score": 0.149,
  "decision": "APPROVE",
  "status": "NEW",
  "thresholds": { "review_above": 0.15, "decline_above": 0.5 },
  "reason_codes": [ { "feature": "D2", "label": "Days since last address change", "value": "2", "direction": "fraud" }, ... ],
  "feature_report": { "counts": { "supplied": 400, "defaulted": 0, "missing": 0, "rejected": 0 } },
  "reviewer_outcome": null
}
```

## 4. Analyst feedback flow

An analyst marks the flagged transaction as fraud via the Operations console
or the API:

```bash
curl -X POST http://localhost:8000/api/review/w-1002/outcome \
  -H "Content-Type: application/json" \
  -d '{"verdict":"fraud","note":"amount+C1 spike matches known pattern"}'
```

```json
{ "status": "REVIEWED", "reviewer_outcome": "fraud", "feedback_note": "amount+C1 spike matches known pattern", ... }
```

The verdict updates the audit record **and** appends to the retraining pool
(`data/feedback/`); a later `scripts/retrain.py` run folds it in under the
gated swap (candidate must beat the served model on a held-out split).

## 5. Monitoring over the decision history

```bash
curl http://localhost:8000/api/monitor/summary
```

```json
{ "n": 21, "avg_score": 0.433, "by_decision": { "APPROVE": 7, "DECLINE": 8, "MANUAL_REVIEW": 6 }, "reviewed": 2 }
```

Decision history feeds data-quality and score-drift monitoring
(`scripts/drift_report.py` also exists for feature drift). Label-based
performance monitoring is **future work** — it needs a trusted label source.

## 6. Demo scenario builder (not a payment gateway)

`POST /api/simulate` maps a few friendly inputs onto the model's feature
space over a scenario profile, and the response states exactly which fields
came from the form vs the profile median — it never pretends a handful of
fields equals the full IEEE schema.

## Stated limitations

- Portfolio demo on 2017–2018 public Kaggle data; not a production fraud
  system and not a payment-gateway integration.
- The model needs the full 400-feature schema; friendly inputs are a demo
  helper, and missing optional features are always reported (never silently
  hidden).
- Probabilities are only roughly calibrated (see the model card).
- Decision store is a local SQLite demo store; rate limiting is per-process.
