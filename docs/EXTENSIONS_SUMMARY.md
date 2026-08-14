# Adaptive policy, LLM audit reports & review extensions — summary

> **Status:** implemented and verified. Full suite green (0 failed), ruff clean,
> coverage 88.45% (gate 75%), frontend Node suite 5/5.
>
> Scope: `api/store.py`, `api/main.py`, `api/schemas.py`, `api/llm_provider.py`,
> `src/fraud_detect/config.py`, `src/fraud_detect/bandit_policy.py`,
> `src/fraud_detect/audit_report.py`, `src/fraud_detect/synthetic.py`,
> `web/live.js` + `tests/test_bandit_store.py`, `tests/test_audit_report.py`,
> `tests/test_synthetic.py`, `tests/test_extensions_api.py`,
> `tests/test_llm_provider.py`.

## 1. Contextual bandit (v2 adaptive policy)

- **`BanditPolicy`** (`src/fraud_detect/bandit_policy.py`) — UCB-1 with a
  context vector built from the model score, amount-derived log-ratio features
  and flag indicators. `Decision` = `APPROVE | MANUAL_REVIEW | DECLINE`.
- **Reward table** (per action × verdict): DECLINE/fraud **+1.0**,
  DECLINE/safe **−2.5**, APPROVE/safe **+0.5**, APPROVE/fraud **−3.0**,
  MANUAL_REVIEW/fraud **+0.8**, MANUAL_REVIEW/safe **+0.1**.
- **`UCB_BONUS_CAP` = `max(REWARD_TABLE.values())`** — without this, an empty
  arm with a wide context (e.g. `x·x ≥ 2`) scores `α·√(x·x) ≥ 1.414` and can
  permanently outrank a learned arm whose achievable mean is ≤ 1.0. Capping
  keeps exploration honest and is what made the greedy-preference tests pass.
- **Promotion** (`promote_bandit_state`): offline IPS evaluation of the
  candidate against the served policy over rewarded events; promoted only when
  the candidate wins with `min_improvement ≥ 0` (API gate: `0.0`). Both the
  superseded served policy and a rejected candidate are **archived to
  `bandit_archive_<ts>.json`** next to the state file (nothing is silently
  thrown away). Promotion requires at least one rewarded event
  (`reason="No rewarded bandit events logged yet"`).
- **Cold-start gate** (`api/main.py`): the bandit only takes over after
  `FRAUD_BANDIT_MIN_REWARDS` (default 20) rewarded events; below that the API
  serves the static v1 policy (`policy_version = _POLICY.version`, no bandit
  event) so the adaptive policy cannot make degenerate empty-arm decisions on
  day one.
- Toggle: `FRAUD_BANDIT_ENABLED=1`, alpha/epsilon/auto-action/audit-sample
  rates all env-driven. Reviews are fanned back into the policy through
  `update_outcome` → `apply_bandit_reward`.

## 2. LLM audit reports (with template fallback)

- **`audit_report.py`**: `build_report_context` (score, decision, tier,
  thresholds, top-5 SHAP drivers, amount vs typical ratio) → `build_prompt`
  (a fixed JSON-schema prompt, prompts never mention invented facts) →
  `parse_llm_response` (validates all `LLM_KEYS`, tolerates code fences,
  normalises driver direction) → `build_template_report` (deterministic
  fallback that always covers the same schema).
- `build_report` returns `(report, source)` where source is `llm` or
  `template`; reports are stored per transaction (`GET /api/review/{id}/report`,
  404 when absent) and regenerated on demand.
- Prompt hygiene: the JSON schema in the prompt is assembled from short line
  pieces — a naive `# noqa: E501` on a line *inside* the triple-quoted
  f-string is string content, i.e. it ends up in the LLM prompt. Keep schema
  lines short instead of suppressing the linter inside strings.

## 3. Appeal endpoint & reviewer outcome

- `POST /api/review/{transaction_id}/appeal` — one-click overturn
  (`AppealRequest(note)` is optional) → `update_outcome(tx, "safe", ...)` →
  reward −2.5 fans into the bandit checkpoint. 404 if no decision exists, 422
  if the transaction was already confirmed fraud.
- `POST /api/review/{transaction_id}/outcome` still requires an explicit
  `verdict` (`safe | fraud`).
- Fixed a pre-existing `UnboundLocalError` (`action`) in `simulate` and
  `predict_batch` by hoisting `action = _action_for_record(record)` out of the
  branching.

## 4. LLM provider — configuration-driven (no hardcoded values)

- LLM settings live in `src/fraud_detect/config.py` (env, single source of
  truth): `FRAUD_LLM_BASE_URL`, `FRAUD_LLM_MODEL` (default `llama3.1`),
  `FRAUD_LLM_API_KEY`, `FRAUD_LLM_TIMEOUT` (default 30s).
- `api/llm_provider.py` reads the config **at call time** (no import-time env
  reads → testable and overridable): `llm_enabled()` is
  `bool(config.LLM_BASE_URL)`; `generate_llm(context)` POSTs to
  `{base}/chat/completions` (stdlib urllib, no new dependency) and returns
  `None` on any failure so the report path always falls back to the template.

## 5. Synthetic payload hygiene

- `synthetic.py` now excludes the target column and `TransactionID` from
  generated feature payloads (validated: payloads carry exactly
  `TransactionAmt, card1, C1, D1`), preserves `-999` sentinels through noise,
  is seed-reproducible and supports fraud oversampling.

## 6. Frontend test fix (web/live.js, Node)

- `tests/test_frontend_live.py` failed with `createLiveQueue is not a
  function` for years-old-looking reasons that were actually subtle:
  `web/package.json` declares `"type": "module"`, so Node 24 evaluates
  `web/live.js` as **ESM** — the `module.exports` branch never runs and
  `require()` returns `{}` (proved by byte-identical copies working outside
  `web/`).
- Fix: `createLiveQueue` is now a top-level function with a real
  `export { createLiveQueue }` (plus the existing browser global branch, so
  `window.FraudLiveQueue` still exists in module browsers). Node suite 5/5,
  and `require('./web/live.js')` still resolves the named export.

## Verification

- `python -m pytest -q -p no:cacheprovider` → **0 failed**, total coverage
  **88.45%** (required ≥ 75%), 4 skips (optional catboost/optuna).
- `python -m ruff check api tests src` → **All checks passed**.
- `node tests/test_live_stream.js` → **5/5 pass**.
- Targeted suites: bandit store, audit report, synthetic, extensions API,
  LLM provider — all green.

## Env surface (new)

| Variable | Default | Purpose |
|---|---|---|
| `FRAUD_BANDIT_ENABLED` | — | `1` activates the adaptive policy path |
| `FRAUD_BANDIT_ALPHA` / `_EPSILON` | `1.0` / `0.10` | UCB exploration / epsilon |
| `FRAUD_AUTO_ACTION_ABOVE` | `0.95` | auto-DECLINE threshold |
| `FRAUD_AUDIT_SAMPLE_RATE` | `0.05` | audit sampling for DECLINE/MANUAL_REVIEW |
| `FRAUD_BANDIT_MIN_REWARDS` | `20` | cold-start gate before bandit serves |
| `FRAUD_LLM_BASE_URL` | — | enables LLM reports (empty = template only) |
| `FRAUD_LLM_MODEL` / `_API_KEY` / `_TIMEOUT` | `llama3.1` / — / `30` | LLM client settings |
