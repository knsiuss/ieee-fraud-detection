# Operations runbook

Scheduled jobs and health checks that keep the served model honest. Every
command assumes the repository root and `PYTHONPATH=src` (the `Makefile`
targets set it up for you).

## Cadence

| Job | Command | Cadence | Output |
| --- | --- | --- | --- |
| Decision ledger snapshot | `python scripts/stream_transactions.py` | continuous / demo | `data/metadata/decisions.db` |
| Label backfill | `python scripts/labelled_replay.py --limit 2500` | daily (or after a label batch lands) | reviewer outcomes + replay decisions |
| Drift report | `python scripts/drift_report.py` | daily | `data/metadata/drift_report.json` |
| Drift guard | `python scripts/drift_guard.py` | after the drift report | `data/metadata/drift_alert.json` |
| Gated retrain | `python scripts/retrain.py` | weekly, or when the guard says `alert` | `data/models/current` |
| Calibration refresh | `python scripts/calibrate_model.py --limit 60000` | after each retrain | `data/metadata/calibration.json` |
| Policy backtest | `python scripts/backtest_policies.py --limit 100000` | after each retrain | `data/metadata/policy_backtest.json` |

## Drift guard exit codes

`scripts/drift_guard.py` maps the drift artefact to an action and a cron-friendly
exit code:

- `0` **ok** — no threshold crossed; wait for the scheduled retrain.
- `2` **warn** — the artefact is stale (> 14 days) or drift is mild; refresh the
  report and let the next retrain absorb it.
- `3` **alert** — a feature PSI >= 0.25 or >= 5 drifted features; run
  `make retrain`. The candidate still has to beat the served model on the
  validation split, so an alert never silently degrades production.

```cron
# daily 04:07 — measure, then decide
7 4 * * *  cd /srv/fraud-detection && PYTHONPATH=src python scripts/drift_report.py \
             && PYTHONPATH=src python scripts/drift_guard.py >> drift.log 2>&1
```

## Health endpoints

- `GET /api/health` — process is up and the model artefact is loadable.
- `GET /api/health/ready` — the service can serve traffic: model loaded, SQLite
  ledger writable, and the drift artefact is no older than 14 days
  (`503` with `checks` otherwise).
- `GET /api/model/drift` — the raw PSI artefact for dashboards.

## Rollback

Model artefacts are versioned directories under `data/models/`. To roll back,
point `FRAUD_DETECT_MODEL_DIR` at the previous version and restart; the SQLite
ledger keeps every decision's `model_version`, so the split is auditable.
