# Deployment

This is a **portfolio / demonstration** service — a production-inspired
fraud-risk console, not a real fraud system. Keep that framing when you
deploy: no payment data, no production labels, public demo only.

The app is a single FastAPI process that also serves the web UI, so the
free-tier story is simple.

## Recommended: one service, free tier

| Component | Host | Why |
|---|---|---|
| FastAPI + React Web UI (Single Image) | **Hugging Face Spaces** (Docker SDK) | Free 2 vCPU + 16GB RAM, one process, HTTPS, multi-stage build |
| FastAPI + React Web UI (Alternative) | **Render** (Free Web Service) | One process, HTTPS, blueprint (`render.yaml`) included |

### Hugging Face Spaces (Recommended — 16GB RAM Free Tier)

Hugging Face Spaces provides a free **CPU Basic (2 vCPU, 16 GB RAM)** container environment that runs the root multi-stage Docker image directly:

1. Create a new Space at [huggingface.co/new-space](https://huggingface.co/new-space).
2. Configuration:
   - **Space SDK**: `Docker` (Blank template).
   - **Hardware**: `CPU Basic • 2 vCPU • 16 GB • FREE`.
   - **Visibility**: `Public`.
3. Add the Hugging Face git remote and push:
   ```bash
   git remote add space https://huggingface.co/spaces/<YOUR_USERNAME>/<SPACE_NAME>
   git push space main
   ```
4. Set `FRAUD_API_ADMIN_KEY` under Space **Settings → Variables and secrets** for administrative endpoint protection.
5. The container builds the Vite React frontend in Stage 1, bootstraps the model, and serves both the SPA and API on port `7860`.

### Running Locally with Docker

You can also run the self-contained container locally:

```bash
docker build -t fraud-detection .
docker run -p 7860:7860 -e FRAUD_API_ADMIN_KEY="demo-secret" fraud-detection
```

Then visit `http://localhost:7860` for the analyst console or `http://localhost:7860/docs` for Swagger API documentation.

### Render (Alternative — Blueprint Included)

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
2. Settings:
   - **Root directory**: `ieee-fraud-detection` (if the repo is nested) or the repo root.
   - **Build command**: `pip install -r requirements.txt`
   - **Start command**: `uvicorn api.main:app --host 0.0.0.0 --port 10000`
   - **Environment**: `PYTHONPATH=src` (and `FRAUD_DETECT_DATA_ROOT` if data is elsewhere).
3. Free tier note: the service **sleeps after ~15 minutes idle**; the first request after a sleep can take a while (cold start). Expected for a portfolio demo.

> The committed `web/sample_transactions.csv` lets the batch tab work, and the
> demo "checkout" simulator works without the full Kaggle data. To serve a
> *real* trained model, either build it during the Render build
> (`python scripts/train_model.py` after `pip install -r requirements.txt`)
> or mount a volume with `data/models/`.

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
