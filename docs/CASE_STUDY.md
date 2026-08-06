# Portfolio case study — fraud-risk decisioning

A short, honest write-up of the problem and the engineering behind this
project. All numbers are reproducible from the scripts in this repo.

## Problem

Fraud detection on payment transactions is a heavily imbalanced (≈3.5%
fraud) classification problem where the *costs* of mistakes matter more than
accuracy. The IEEE-CIS competition supplies ~590K labeled transactions with
hundreds of anonymised and partially-missing features and a temporal axis.

## Constraints

- **Severe class imbalance** → ROC-AUC and PR-AUC, not accuracy.
- **Massive missingness** (>50% for many columns) and sparse identity data.
- **Temporal structure** → a naive random train/test split *inflates* metrics
  by letting the model memorise time-correlated signal.
- **Anonymised features** (`V1`–`V339`) → limited human interpretability.
- **Public-data demo**: must be safe, reproducible, and clearly labelled.

## Architecture

Web console (vanilla JS) → FastAPI service → `fraud_detect` package
(`serving` + `sim`) → model artefact → gated retraining. Reviewers' verdicts
feed a feedback pool; a scheduled retrain promotes a candidate only when it
beats the served model on a held-out split. Evaluation and drift are
reproducible scripts.

## Key trade-offs

- **Random vs time-ordered validation**: chose the leakage-resistant
  time-ordered split (0.909) as the headline over the flattering random
  split (0.954). Lower number, honest number.
- **Numeric-only features**: dropped object/categorical columns for a single
  consistent train/serve path, at some cost to signal (simplest, reproducible).
- **Gated retraining over always-update**: an anti-regression gate protects
  the deployed model — stability over chasing marginal AUC.
- **One web service over a split app**: simpler free deployment, at the cost
  of a wildcard CORS setup (documented as demo-scoped).

## Honest results

| Metric | Time-ordered (headline) |
|---|---|
| ROC-AUC | **0.909** |
| PR-AUC | 0.562 |
| Brier | 0.021 |
| Precision @ top 1% | 0.899 |
| Precision @ top 5% | 0.414 |

Calibration is imperfect (under-predicts at high risk). Random-split metrics
(0.954 AUC) are inflated and not used as results.

## Limitations

- 2017–2018 data, not a live model.
- No real labels → no label-based performance monitoring yet.
- External datasets incompatible (no merge, no fabricated validation).
- Demo-grade rate limiting; not a production fraud system.

## What I learned

1. **Evaluation design is the first-class decision** — reporting the leaky
   number would have been easy and wrong; time-ordered validation changed the
   whole story.
2. **Explainability turns a score into a usable decision** — the SHAP-based
   summary is what makes the tool feel like an analyst assistant.
3. **A safety gate for auto-learning** (validate before swap) is more
   important than the retraining frequency.
4. **Reproducibility and honesty are features**: pinned seeds, committed
   result artifacts, and a model card make the project defensible.