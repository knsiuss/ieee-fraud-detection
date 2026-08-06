# Model Card — IEEE-CIS Fraud Probability

> This is a **portfolio / demonstration** model for a public-data science
> competition. It is **not** a bank-ready fraud system and must not be used
> to make real financial decisions. All numbers below are measured on the
> public IEEE-CIS competition data and are reproducible via
> `scripts/evaluate_model.py`.

## Model summary

| Field | Value |
|---|---|
| Task | Binary classification — probability a payment transaction is fraudulent (`isFraud`) |
| Primary metric | ROC-AUC (skew-robust), reported **on a time-ordered split** |
| Model | Gradient-boosted trees (LightGBM), tuned |
| Features | 400 numeric features (numeric subset of the competition schema) |
| Training data | ~590K labeled transactions from the IEEE-CIS / Vesta Kaggle competition |
| Artefact | `data/models/current/` (model + features + segment baselines + metadata) |

## Honest evaluation (reproducible)

Metrics are computed with `scripts/evaluate_model.py`, which trains the same
model under **two competing validation designs** to make the effect of
temporal leakage visible. The **time-ordered split is the primary, honest
numbers**: it holds out the latest ~20% of the time series, so the model is
scored on transactions that happen *after* everything it trained on.

| Metric | Time-ordered split (honest) | Random split (inflated) |
|---|---|---|
| **ROC-AUC** | **0.909** | 0.954 |
| PR-AUC | 0.562 | 0.773 |
| Brier score | 0.021 | 0.014 |
| Precision @ threshold 0.5 | 0.824 | 0.934 |
| Recall @ threshold 0.5 | 0.360 | 0.531 |
| Precision @ top 1% riskiest | 0.899 | 0.987 |
| Precision @ top 5% riskiest | 0.414 | 0.543 |

The random-split ROC-AUC (0.95) that an initial README quoted was **inflated
by temporal leakage** (random split lets the model memorise time-correlated
signal). The leakage-resistant benchmark is **ROC-AUC ≈ 0.91**.

### Calibration (time-ordered split)

The model is only roughly calibrated (Brier 0.021), and at high risk it
**under-predicts**: in the top probability decile the mean prediction is
0.225 while the actual fraud rate is 0.251. Thresholds should be chosen on
precision/recall trade-offs, not taken as probabilities.

### Segment performance (time-ordered split, ROC-AUC)

| Segment | ROC-AUC |
|---|---|
| Identity data present | 0.919 |
| Identity data absent | 0.877 |
| Validation early half | 0.916 |
| Validation late half | 0.902 |
| Transaction amount ≥ median | 0.898 |
| Transaction amount < median | 0.919 |

Performance does not materially degrade across the validation window
(late half 0.902), which is encouraging, but the whole validation set is a
single point in time from one competition — **no forward test against truly
deployed, live data exists**.

## Intended use

- Reproducing an interpretable, time-aware baseline for the IEEE-CIS fraud
  problem.
- Demonstrating a production-inspired serving API and reviewer workflows.
- Educational: inspecting SHAP-based explanations and risk-tiering.

## Non-intended use

- Making real-time authorisation or fraud decisions on actual payments.
- Generalising to other banks, countries, or card schemes without
  re-validation (feature definitions are largely anonymised; card1–card6 are
  *counts and issuer codes*, not real card data).
- Using the plain model probabilities as calibrated likelihoods without a
  recalibration / threshold setting step.

## Data limitations

- Data is from a **2017–2018 Vesta / IEEE contest** and is likely outdated
  relative to 2026 fraud patterns.
- **Heavily class-imbalanced** (~3.5% fraud). PR-AUC and precision@capacity
  are the informative metrics, not accuracy.
- **Large missingness**: many features >50% missing; sparse identity table.
- Anonymised `V*` features are uninterpretable by design; only a subset of
  human-readable features can be explained in plain language.

## Risks & monitoring plan

- **Threshold drift / calibration decay** → monitor precision@top-k and the
  calibration curve over time; recalibrate if the top-decile gap widens.
- **Distribution shift** → monitor per-feature PSI against the training
  distribution (`scripts/drift_report.py`, see repo) on incoming scores.
- **No live labels** → label-based performance monitoring (false negative /
  false positive tracking) requires a review-feedback loop, which is the
  tool's feedback pool; without a trusted label source it is **blocked**.
- **Infrastructure** → the service is a portfolio demo. It ships with a
  public-test-only scope: never wire it to a payment gateway.

## Environment / reproducibility

- `python scripts/train_model.py` reproduces the served artefact.
- `python scripts/evaluate_model.py` reproduces the table above and writes
  `data/metadata/evaluation.json`.
- Seeds and split parameters are fixed in `fraud_detect/config.py`.