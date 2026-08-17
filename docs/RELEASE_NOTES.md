# Release notes (draft — v0.1.0)

> **Draft for the first public release.** Nothing here is published until the
> maintainer approves and runs the release command. This is a **portfolio /
> demo** project on public Kaggle data — not a production fraud system.

## Title

**IEEE-CIS Fraud Detection — a production-inspired fraud-risk decisioning
platform (portfolio demo)**

## Summary

A tuned LightGBM model served behind a FastAPI API with a React/TypeScript
review console: scenario scoring, batch CSV scoring, SHAP
explanations, reviewer feedback, and gated auto-retraining. Built and
documented with honest ML practice: leakage-aware evaluation, a model card,
drift monitoring, and reproducible scripts.

## Key numbers (honest, reproducible)

- **ROC-AUC 0.909 on a time-ordered validation split** (leakage-resistant).
  A random split scores 0.954 but is inflated by temporal leakage and is
  reported only for transparency.
- PR-AUC 0.562 · Brier 0.021 · precision @0.5 0.824 · recall @0.5 0.360.
- Precision at realistic review capacity: **0.899 @ top 1%**, **0.414 @ top 5%**.
- Full suite: 86.6% test coverage, ruff lint + format clean.

Reproduce with `scripts/evaluate_model.py` → `data/metadata/evaluation.json`.

## What's included

- FastAPI service (`/api/predict`, `/api/predict/batch`, `/api/explain`,
  `/api/feedback`, `/api/retrain`, `/api/health`, `/api/model`, `/api/stats`).
- React/TypeScript review console with ECharts and a demo-data disclaimer.
- Checkout-style input mapping + SHAP decision summaries.
- Gated auto-retraining (a candidate is only promoted if it beats the served
  model on a held-out split).
- Model card, deployment guide, external-data research, release checklist,
  CI, end-to-end smoke test.

## Known limitations

- Data is from a 2017–2018 Kaggle competition; model is a benchmark, not a
  live system.
- Probabilities are only roughly calibrated (under-predict at high risk).
- Real-time drift alerts and label-based performance monitoring are future
  work (no live labels).
- Free-tier hosting sleeps when idle (cold start).
- Rate limiting is per-process; the retrain guard needs `FRAUD_API_ADMIN_KEY`.

## Launch checklist

- [ ] Merge the feature branch and tag `v0.1.0`.
- [ ] Set `FRAUD_API_ADMIN_KEY` and confirm `/api/retrain` is guarded.
- [ ] Regenerate README screenshots against the final UI.
- [ ] Deploy via `render.yaml` (needs maintainer approval).
- [ ] Confirm `/api/health` passes the Render health check after cold start.
- [ ] Publish this release (draft → release) after deployment is verified.

## Publish command (do not run without approval)

```bash
gh release create v0.1.0 --title "v0.1.0 — ..." --notes-file docs/RELEASE_NOTES.md
```
