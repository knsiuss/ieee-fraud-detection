# Decision economics

The detector answers "how likely is fraud?". A business needs a second answer:
**what should we do about it, given what each mistake costs?** This page
documents the cost model, the cost-based decision policy, the honest metrics
endpoint, and the offline backtest that calibrates them.

Code: `src/fraud_detect/economics.py`, wired into `api/main.py` and
`api/store.py`. Calibration: `scripts/backtest_policies.py` →
`data/metadata/policy_backtest.json`.

## 1. The cost model

Every action has an expected cost in currency units, for one transaction of
amount `a` with fraud probability `p`:

| action | expected cost |
| --- | --- |
| APPROVE | `p * (a * liability_rate + chargeback_fee)` — fraud loss when we let it through |
| MANUAL_REVIEW | `review_cost + p * (1 - review_catch_rate) * (a * liability_rate + chargeback_fee)` — analyst time plus fraud that slips past the review |
| DECLINE | `(1 - p) * (a * margin_rate + friction_cost)` — lost margin and customer friction on a good sale |

Defaults (`CostModel`): `margin_rate=0.30`, `review_cost=2.00`,
`chargeback_fee=25.00`, `friction_cost=1.50`, `liability_rate=1.00`,
`review_catch_rate=0.85`, `max_review_rate=0.05`, `version=cost-v1`.

All of these are assumptions, not accounting facts. The important property is
that they are explicit, versioned (`version` is stamped on every decision) and
overridable through environment variables — the model is the policy document.

## 2. The decision policy

`economics.decide()` minimises expected cost over the three actions and adds
the chosen `policy_version` plus the full expected-cost table to each decision,
so any decision can be audited after the fact.

Two regimes are selected with `DECISION_POLICY`:

- `threshold` (default, backwards compatible): review ≥ 0.15, decline ≥ 0.50.
- `cost`: expected-cost minimisation per transaction, as above.

### Review capacity

Analysts are finite. `max_review_rate` caps how much traffic may be reviewed.
The naive approach — review only above a score percentile — is wrong, because
the value of a review is **not monotone in the score**: a very high score is
already cheaper to decline, and a very low one cheaper to approve. The most
valuable reviews sit in the middle, on high-value transactions.

So capacity is allocated by **review benefit**
(`min(approve_cost, decline_cost) - review_cost`): a floor is the k-th largest
benefit on a labelled sample, where `k = max_review_rate * n`. Transactions
whose review saves less than the floor skip review and take the cheaper of
approve/decline.

Calibrate the floor offline and deploy it:

```bash
python scripts/backtest_policies.py --limit 100000
# copy capacity.recommended_env from data/metadata/policy_backtest.json
export DECISION_POLICY=cost
export DECISION_REVIEW_BENEFIT_FLOOR=<floor from the report>
```

With no floor set, the live cost policy reviews every transaction where a
review is the cheapest action — fine for evaluation, too expensive in
production. The backtest exists specifically to produce that number.

## 3. Measured impact (100k labelled transactions, served model)

From `data/metadata/policy_backtest.json`:

| policy | net cost | per txn | fraud caught | review % | savings vs v1 |
| --- | --- | --- | --- | --- | --- |
| deployed threshold v1 | 144,849.53 | 1.45 | 2,953 | 1.48 | — |
| best fixed thresholds (in-sample) | 90,199.88 | 0.90 | 3,408 | 15.54 | 54,649.65 |
| best fixed within 5% capacity | 108,626.28 | 1.09 | 3,175 | 3.40 | 36,223.25 |
| **cost policy, 5% capacity** | **100,435.00** | **1.00** | **3,128** | **5.00** | **44,414.53** |

Reading the table honestly:

- Under the same 5% review capacity, the cost policy saves **~44k** on 100k
  transactions versus the shipped thresholds, i.e. **~0.44 per transaction**.
- It catches *fewer* frauds than the best fixed thresholds within capacity
  (3,128 vs 3,175) yet costs less: it spends reviews on high-value
  mid-score cases and lets the model decline the rest, which is the whole
  point of weighing amounts.
- The unrestricted best fixed pair reaches 90,200 — but only by reviewing
  15.5% of traffic, which exceeds the stated capacity. That row is an
  optimistic upper bound for *any* threshold policy, kept for context.
- Highest possible accuracy is not the objective; lowest expected cost is.

## 4. Live economics endpoint

`GET /api/metrics/economics` returns:

- `assumptions` — the full cost model, active `policy_mode`, and the
  counterfactual's review-benefit floor.
- `coverage` — decisions logged vs decisions with a reviewer label.
- `actual` — realised net cost of what happened, cost by action, action mix,
  fraud caught/missed.
- `counterfactual` — same transactions scored by the cost-optimal policy.
- `delta` — `net_cost_saved`, per-1k savings, and how many more/fewer frauds.
- `caveats` — states that only labelled decisions are compared and that the
  counterfactual is an estimate.

If no decision has a reviewer label yet, the endpoint says so instead of
inventing numbers, exactly like `/api/metrics/loss` explains its basis.

## 5. What the other metrics now mean

The same PR removed the fabricated numbers from `/api/metrics/summary`:

- `tps` is measured from decisions logged in the last 5 minutes; it is `0`
  when idle, not a made-up `14.8`.
- `latency.p50_ms/p95_ms/p99_ms` cover the last 15 minutes of decisions
  (`latency.window_seconds`), so a fixed regression stops polluting the KPI once
  its samples age out. They come from per-decision latency
  (`decisions.latency_ms`, added by migration) and measure the **whole decision
  pipeline**, including the SHAP driver computation that `/api/predict` returns.
  `samples` is how many decisions in the window carry a measurement; the KPI
  shows `—` instead of a fabricated number when there are none. The SHAP
  explainer is cached per model, so this number reflects steady-state serving
  rather than rebuilding the explainer on every request.
- `psi_drift` is read from `data/metadata/drift_report.json` (source path and
  alert threshold included); without a drift report the value is absent
  instead of a constant `0.018`.
- `chargeback_bps` is computed from **labelled approved** volume, with
  `label_coverage_pct` next to it. It is no longer derived from the share of
  declines (which is not a fraud rate). It stays `null` until at least 20
  labelled approvals exist: one fraud among ten approvals is noise, not a
  10 000 bps rate, and the KPI shows `—` instead of a number it cannot support.

## 6. Changing the model

Edit the defaults in `CostModel` (versioned) or override per deployment:

| env var | meaning |
| --- | --- |
| `DECISION_POLICY` | `threshold` or `cost` |
| `COST_MARGIN_RATE` | gross margin fraction on a good sale |
| `COST_REVIEW_COST` | cost of one manual review |
| `COST_CHARGEBACK_FEE` | fixed fee per fraud loss |
| `COST_FRICTION_COST` | fixed friction per wrongly declined sale |
| `COST_LIABILITY_RATE` | share of the transaction lost on a fraud |
| `COST_REVIEW_CATCH_RATE` | share of fraud a review catches |
| `COST_MAX_REVIEW_RATE` | cap on reviewer workload |
| `COST_MODEL_VERSION` | version string stamped on decisions |
| `DECISION_REVIEW_BENEFIT_FLOOR` | capacity floor from the backtest |

After changing costs, re-run the backtest and update
`policy_backtest.json`; the endpoint and any decision audit will then point at
the same model.

## 7. Caveats

- Costs are hypotheses. Validate `liability_rate`, `margin_rate` and
  `review_cost` against finance data before relying on absolute savings.
- The backtest is in-sample on one dataset; the best-fixed row is an upper
  bound, and the cost policy is scored on its own model's scores.
- `metrics_economics` compares only labelled decisions, so its savings estimate
  is directional until reviewer coverage is high.
- Fraud losses are modelled as `amount * liability_rate + chargeback_fee`;
  real accounting also involves refunds, disputes and operational costs.
