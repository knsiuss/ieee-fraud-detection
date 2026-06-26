# Overview

This project tackles the **IEEE-CIS Fraud Detection** challenge — predicting
the probability that an online transaction is fraudulent. The dataset is
provided by Vesta Corporation, a leading payment processing company.

| Aspect | Detail |
|---|---|
| **Task** | Binary Classification |
| **Target** | `isFraud` (0 = legitimate, 1 = fraud) |
| **Primary Metric** | ROC-AUC |
| **Dataset Size** | ~590K training transactions, 400+ features |
| **Fraud Rate** | ~3.5% (heavily imbalanced) |

## Key Challenges

- **Class Imbalance** — Only ~3.5% of transactions are fraudulent.
- **High Dimensionality** — 400+ features including 339 anonymous engineered
  features (`V1` – `V339`).
- **Sparse Identity Data** — Identity table covers only ~25% of transactions.
- **Extensive Missing Values** — Many features have >50% missing data.
- **Temporal Features** — `TransactionDT` is relative (seconds from a
  reference point).

## Module overview

| Module | Responsibility |
|---|---|
| Module | Responsibility |
|---|---|
| `config.py` | Paths, column groups, hyperparameters, thresholds |
| `_exceptions.py` | Domain exceptions (`FraudDetectError`, `MissingArtefactError`, `InvalidDataError`) |
| `io.py` | Parquet/CSV read/write helpers with fallback logic |
| `data.py` | Memory optimisation, missing-value reporting |
| `features.py` | Vectorised time/amount/email/card transforms |
| `viz.py` | Shared EDA plotting functions + `save_figure` |
| `models.py` | Train/val split, logistic pipeline, LightGBM importance |
