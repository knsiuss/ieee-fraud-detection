# Changelog

All notable changes are recorded here. Versions follow [Semantic
Versioning](https://semver.org/). The project is a portfolio demo on public
data — see the model card for honest scope.

## [Unreleased]

### Added
- **Honest evaluation** (`scripts/evaluate_model.py`): random vs
  **time-ordered** split metrics (ROC-AUC, PR-AUC, Brier, calibration,
  precision/recall at review capacity, segment-level AUC). Time-ordered
  ROC-AUC **0.909** is the leakage-resistant headline; the earlier
  random-split 0.95 was inflated by temporal leakage.
- **Model card** (`docs/MODEL_CARD.md`): intended / non-intended use, honest
  metrics, calibration caveat, risks, monitoring plan.
- **Monitoring scaffold** (`fraud_detect.monitoring`, `scripts/drift_report.py`):
  per-feature PSI drift + data-quality checks.
- **External-data research** (`docs/EXTERNAL_DATA.md`): comparability analysis;
  no dataset merged, no external validation run (blocked, documented).
- **Deployment guide** (`docs/DEPLOYMENT.md`): free-tier Render / HF Spaces.
- **Demo labeling + rate limiting**: API title/description and web footer
  mark the demo; per-IP rate limit middleware.
- **End-to-end smoke test** (`tests/test_smoke.py`).
- Serving, gated auto-retraining, checkout-style simulator, vanilla-JS web
  console (replacing the removed Streamlit dashboard), tests, Docker, CI
  lint/format fixes.

### Fixed
- Pre-existing lint debt (`ruff`) across `src/`, `api/`, `scripts/`, `tests/`;
  CI scope corrected to the real source dirs.
- Admin header alias so `X-Admin-Key` actually matches.
- Web console: checkout submit referenced an undefined `payload` (result
  panel never appeared); tab panels stayed invisible due to `hidden`
  (both found while capturing README screenshots).

### Removed
- Streamlit dashboard (`dashboard/app.py`, `dashboard/precompute.py`).

### Known limitations
- Model probabilities are only roughly calibrated (Brier 0.021 on the
  time-ordered split); the top-decile mean prediction (0.225) under-predicts
  the actual rate (0.251).
- Real-time drift and label-based performance monitoring are **future work**.
- No live deployment published; deployment requires explicit approval.
