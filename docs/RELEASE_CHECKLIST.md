# Release-Readiness Checklist

Truthful launch checklist for the **public-data portfolio/demo** positioning.
Each item records the verified status and how it was checked. This is a demo,
not a production fraud system — that framing is deliberate and non-negotiable.

Legend: ✅ verified now · ⚠️ needs action · 🚫 blocked / not applicable

## Security & secrets

- ✅ No secrets or credentials in git. Scanned with `git grep` for token/API-key
  patterns; matches were benign (GitHub `id-token` permission, prose).
- ✅ No `.env`, `.pem`, `.key`, or credential files tracked.
- ✅ Model artefact (`data/models/`) is gitignored — not committed.
- ✅ Full dataset (`data/raw|interim|processed`) is gitignored — not committed.
- ⚠️ Set `FRAUD_API_ADMIN_KEY` before any public deploy (guard `/api/retrain`).
- ✅ Absent-model handling returns a safe generic 503 (no filesystem path).

## Licensing

- ✅ `LICENSE` is MIT with the author's name; `pyproject.toml` declares MIT.
- ✅ README/headers state it is a portfolio demo on public data.

## Dependency health

- ✅ `pip install -e ".[lgbm,dev]"` works in this environment.
- ✅ `requirements.txt` matches the deployed runtime; pinned minimums.
- ⚠️ Not yet tested: a fresh `pip install -r requirements.txt` on a clean
  machine (no pip cache) — expected to work; add to CI if desired.

## Docs accuracy

- ✅ README metrics match `data/metadata/evaluation.json` (time-ordered
  ROC-AUC 0.909; random 0.954 marked as inflated).
- ✅ All README links resolve: CONTRIBUTING, CHANGELOG, SECURITY, MODEL_CARD,
  DEPLOYMENT, EXTERNAL_DATA, screenshots (verified paths exist).
- ✅ Architecture diagram (Mermaid) present.
- ⚠️ README screenshots are current captures; regenerate with
  `scripts/capture_screenshots.py` if the UI changes.

## Demo safety & resilience

- ✅ Clear "demo/portfolio, not a real fraud system" disclaimer in API docs and
  web footer.
- ✅ Graceful 503 when the model is absent; health reports `model_present=false`.
- ✅ Input validation: CSV upload capped at 50 MB; unparseable CSV → 400.
- ✅ No internal paths/errors exposed to clients.
- ⚠️ Frontend shows an alert on API error (functional, not polished) — not a
  launch blocker.

## Accessibility

- ⚠️ Basic semantic HTML and keyboard-focusable buttons only; no formal WCAG
  audit. Not a launch blocker for a demo, but worth noting.

## Performance

- ✅ Scoring is fast (LightGBM `num_threads=1`, in-process artefact cache).
- ✅ Per-IP rate limit (default 300 req/min) protects a public demo.
- ⚠️ Free-tier hosting sleeps when idle (cold start) — documented.

## API reliability

- ✅ `/api/health` liveness + `model_present`.
- ✅ End-to-end smoke test (`tests/test_smoke.py`) drives the full workflow.
- ✅ 400/413/429/503 handled; 500 is generic (no detail leak).

## Reproducibility

- ✅ `scripts/train_model.py`, `scripts/evaluate_model.py`,
  `scripts/drift_report.py` reproduce every reported number (fixed seeds in
  `fraud_detect/config.py`).
- ✅ Full test suite: 86.6% coverage, lint + format clean.

## CI

- ✅ `.github/workflows/ci.yml`: ruff check + format, pytest (coverage gate 75%)
  on 3.10/3.11/3.12.

## Go / No-go

See the final report in the repository root PR. Current verdict: **GO to
prepare for launch; deployment itself requires your approval** (no pushing,
publishing, or cloud spend without it).
