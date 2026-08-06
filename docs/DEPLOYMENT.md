# Deployment

This is a **portfolio / demonstration** service — a production-inspired
fraud-risk console, not a real fraud system. Keep that framing when you
deploy: no payment data, no production labels, public demo only.

The app is a single FastAPI process that also serves the web UI, so the
free-tier story is simple.

## Recommended: one service, free tier

| Component | Host | Why |
|---|---|---|
| FastAPI + web UI (single service) | **Render** (free web service) or **Hugging Face Spaces** | One process, HTTPS, public URL, free |

### Render (recommended — simplest, blueprint included)

A [Render Blueprint](render.yaml) is committed: `render.yaml` defines the
service, build, start command, health check, and env vars.

1. Push the repo to GitHub.
2. Render → **New → Blueprint** → connect the repo (uses `render.yaml`).
3. Set `FRAUD_API_ADMIN_KEY` in the service Environment.
4. Deploy. The build runs `pip install -r requirements.txt && python
   scripts/train_model.py` — the second command trains on the committed demo
   sample so the service responds immediately.

Alternatively, manual setup via **New → Web Service**:
1. Connect the repo.
3. Settings:
   - **Root directory**: `ieee-fraud-detection` (if the repo is nested) or the repo root.
   - **Build command**: `pip install -r requirements.txt`
   - **Start command**: `uvicorn api.main:app --host 0.0.0.0 --port 10000`
   - **Environment**: `PYTHONPATH=src` (and `FRAUD_DETECT_DATA_ROOT` if data is elsewhere).
4. Free tier note: the service **sleeps after ~15 minutes idle**; the first request after a sleep can take a while (cold start). Expected for a portfolio demo.

> The committed `web/sample_transactions.csv` lets the batch tab work, and the
> demo "checkout" simulator works without the full Kaggle data. To serve a
> *real* trained model, either build it during the Render build
> (`python scripts/train_model.py` after `pip install -r requirements.txt`)
> or mount a volume with `data/models/`.

### Hugging Face Spaces (alternative)

- Create a **Docker** Space pointing at this repo.
- The included `Dockerfile` builds a self-contained image: it installs deps,
  copies the app, and bootstraps a serving model from the committed sample.
- Space settings → CPU Basic (free) → deploy. Cold start is usually faster
  than Render's free tier.

## Splitting the frontend (optional)

If you prefer a static frontend on GitHub Pages / Netlify:

- Host `web/` as static files (the app reads `window.API_BASE`).
- Point `window.API_BASE` at the deployed FastAPI URL.
- CORS is already open (`allow_origins=["*"]`) — acceptable for a public demo
  but not for real production (documented as a limitation).

## Keeping the model up to date

- `scripts/retrain.py` folds reviewer feedback into a candidate and **only
  swaps it when it beats the served model on a held-out split**.
- Schedule it on the host (cron) or a GitHub Actions `schedule` workflow.
- `data/models/` and `data/feedback/` are runtime state — mount them as a
  volume so retrained artefacts survive restarts.

## Security notes (do this before exposing publicly)

- The `X-Admin-Key` retrain guard only protects `/api/retrain` when
  `FRAUD_API_ADMIN_KEY` is set — set it in production.
- Rate limiting, request-size caps, and auth are **not** implemented beyond
  the retrain key. See the model card / README limitations.
- Never serve real card or identity data through this demo.

## Rollback

- **Render**: Deploy → "Deploy a previous commit" (redeploy the last
  known-good commit). The served model is rebuilt on deploy and the free tier
  has no persistent disk, so a rollback also resets the model — redeploy,
  then optionally re-run the retrain.
- **Docker**: keep previous image tags (`docker build -t fraud-detection:<sha>`)
  and start the last known-good tag.
- **Model-level**: the gated retrain already protects the *served model* — a
  candidate that fails the validation gate is never swapped, so the model only
  changes on a deliberate, passing retrain.

## Not published

No live URL is published from this repo at the time of writing. Deployment
is left as an explicit step requiring your approval before any public
publish (per project policy — no publishing without asking).
