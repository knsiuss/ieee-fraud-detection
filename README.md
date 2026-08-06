<p align="center">
  <img src="https://img.shields.io/badge/Status-COMPLETED-brightgreen?style=for-the-badge" alt="Status: Completed"/>
  <img src="https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python 3.10+"/>
  <img src="https://img.shields.io/badge/ROC--AUC-0.909-blue?style=for-the-badge" alt="ROC-AUC 0.909 (time-ordered split)"/>
  <img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge" alt="MIT License"/>
  <img src="https://img.shields.io/github/actions/workflow/status/knsiuss/ieee-fraud-detection/ci.yml?branch=main&style=for-the-badge&label=CI&logo=github" alt="CI"/>
</p>

# IEEE-CIS Fraud Detection

> End-to-end machine learning solution for detecting fraudulent e-commerce transactions, built on the [IEEE-CIS / Vesta Corporation](https://www.kaggle.com/c/ieee-fraud-detection) dataset.

This repository contains a complete, production-shaped data science pipeline — from raw data ingestion through exploratory analysis, feature engineering, model training, hyperparameter optimisation, ensembling, and evaluation — packaged as a reusable Python module (`fraud_detect`), a reproducible notebook series, a FastAPI service, and a browser-based review console (vanilla JS + Chart.js) with gated auto-retraining.

> **Demo / portfolio.** Built on public Kaggle competition data for learning
> and review. **Not a production fraud system** — do not use it for real
> payment decisions. See the [Model Card](docs/MODEL_CARD.md) for honest scope.

---

## Table of Contents

- [Repository Structure](#repository-structure)
- [Analysis Pipeline](#analysis-pipeline)
- [Core Python Package](#core-python-package)
- [Service & Web App](#service--web-app)
- [Results (honest evaluation)](#results-honest-evaluation)
- [Reproducing Results](#reproducing-results)
- [Limitations](#limitations)
- [Roadmap](#roadmap)
- [Dataset](#dataset)
- [Feature Groups](#feature-groups)
- [Tech Stack](#tech-stack)
- [Getting Started](#getting-started)
- [Development & QA](#development--qa)
- [Contributing](#contributing)
- [Citation](#citation)
- [License](#license)

---

## Overview

The objective is to predict the probability that an online payment transaction is fraudulent (`isFraud`). The challenge is notable for its severity of class imbalance, high dimensionality, and large volumes of missing data.

| Aspect | Detail |
|---|---|
| **Task** | Binary classification |
| **Target** | `isFraud` (0 = legitimate, 1 = fraud) |
| **Primary metric** | ROC-AUC |
| **Training size** | ~590K transactions |
| **Features** | 400+, including 339 anonymised Vesta features (`V1`–`V339`) |
| **Fraud rate** | ~3.5% (heavily imbalanced) |

### Problem Characteristics

- **Class imbalance** — only ~3.5% of transactions are fraudulent, requiring threshold calibration and PR-aware evaluation.
- **High dimensionality** — 339 anonymous engineered features plus raw transaction, card, and identity attributes.
- **Sparse identity data** — the identity table covers only ~25% of transactions.
- **Missing values** — many columns exceed 50% missingness and require per-column imputation strategies.
- **Relative timestamps** — `TransactionDT` is expressed as seconds from an unknown reference point.

---

## Repository Structure

```
ieee-fraud-detection/
│
├── src/fraud_detect/            # Core Python package — typed, documented utilities
│   ├── config.py                #   Paths, column groups, hyperparameters, tuning spaces
│   ├── io.py                    #   Parquet/CSV read & write helpers
│   ├── data.py                  #   Memory optimisation, missing-value reports, imputation
│   ├── features.py              #   Feature engineering transforms
│   ├── models.py                #   Train/val split, model training + cross-validation
│   ├── tuning.py                #   Optuna hyperparameter optimisation
│   ├── ensemble.py              #   Voting and stacking ensembles
│   ├── evaluation.py            #   Metrics, optimal threshold, model comparison, McNemar's test
│   ├── error_analysis.py        #   Error segmentation, distribution-shift, FP/FN analysis
│   ├── viz.py                   #   Plotting helpers (18 functions)
│   ├── serving.py               #   Model serving: artefacts, prediction, risk tiers, SHAP
│   ├── sim.py                   #   Checkout-style inputs → model features + profiles
│   ├── monitoring.py            #   PSI drift + data-quality checks
│   └── _exceptions.py           #   Domain exceptions
│
├── notebook/                    # 15 ordered analysis notebooks (01–15)
│   ├── README.md                #   Notebook index & dependency graph
│   ├── 01_data_loading.ipynb    #   Data loading, merging & sanity checks
│   ├── 02_eda_transaction.ipynb #   EDA — transaction features
│   └── ...                       #   (see Analysis Pipeline table below)
│
├── api/                         # FastAPI service
│   ├── main.py                  #   Routes (predict, batch, explain, feedback, retrain)
│   ├── store.py                 #   Versioned model store + gated retrain
│   └── schemas.py               #   Pydantic request/response models
│
├── web/                         # Vanilla-JS frontend (served by FastAPI at /)
│   ├── index.html               #   Scorer / batch / model UI
│   ├── style.css
│   └── app.js
│
├── dashboard/data/              # Committed analysis CSVs + demo sample (train fallback)
│
├── scripts/
│   ├── prepare_data.py          #   CSV → Parquet conversion CLI
│   ├── train_model.py           #   Train + serialise the serving artefact
│   ├── retrain.py               #   Gated auto-retrain loop (cron-safe)
│   ├── evaluate_model.py        #   Random vs time-aware honest evaluation
│   └── drift_report.py          #   PSI drift + data-quality report
│
├── tests/                       # 100+ unit / integration / property tests
│
├── data/
│   ├── raw/                     # Original Kaggle CSVs (gitignored)
│   ├── interim/                 # Merged training table (gitignored)
│   ├── processed/               # Engineered features (gitignored)
│   └── metadata/                # Analysis outputs & best parameters
│
├── docs/
│   ├── MODEL_CARD.md            #   Intended use, honest metrics, risks, monitoring
│   ├── DEPLOYMENT.md            #   Free-tier deployment guide
│   ├── EXTERNAL_DATA.md         #   External-dataset comparability research
│   └── source/                  #   Sphinx documentation
├── .github/workflows/           # CI (lint + test) and docs deployment workflows
├── CONTRIBUTING.md              # Contribution guide
├── CHANGELOG.md                 # Version history
├── SECURITY.md                  # Security policy
├── Makefile                     # Dev workflow shortcuts
├── pyproject.toml               # Package metadata + dependencies
└── README.md
```

---

## Analysis Pipeline

The analysis is organised as a numbered series of reproducible notebooks. Each stage consumes the outputs of the previous one and produces a documented deliverable — tables, figures, or trained artefacts — stored under `data/metadata/`.

| # | Notebook | Purpose | Key Output |
|---|---|---|---|
| 01 | **Data Loading** | Load the transaction and identity tables, merge them, and run sanity checks. | Clean merged training table |
| 02 | **EDA — Transaction Features** | Examine distribution and ranges of transaction-level features (amount, product, card). | Data-quality notes |
| 03 | **EDA — Identity Features** | Analyse coverage and value distribution of the identity/device table. | Coverage assessment |
| 04 | **Missing Value Analysis** | Quantify missingness per column and define the imputation strategy. | `missing_value_report.csv` |
| 05 | **Target Distribution & Imbalance** | Characterise the class imbalance and its impact on evaluation. | Imbalance strategy |
| 06 | **Feature Correlation Analysis** | Identify correlated and redundant feature groups. | `redundant_feature.csv` |
| 07 | **Feature Engineering** | Derive new features (e.g. amount-vs-address means, card-amount means, temporal aggregates). | Engineered feature set |
| 08 | **Feature Importance & Selection** | Rank features with LightGBM importance and select the top set. | `feature_importance.csv` |
| 09 | **Baseline Model** | Train a logistic regression reference point. | Baseline ROC-AUC |
| 10 | **Model Training** | Train gradient-boosted models (LightGBM, XGBoost, CatBoost) with cross-validation. | Trained models + CV scores |
| 11 | **Hyperparameter Tuning** | Optimise each model with Optuna (100 trials). | `lightgbm_best_params.json` |
| 12 | **Ensemble Methods** | Combine models via hard/soft voting and stacking. | Ensemble scores |
| 13 | **Model Evaluation** | Compare ROC/PR curves, confusion matrices, and McNemar significance tests. | Model comparison |
| 14 | **Error Analysis** | Segment errors, detect distribution shift, and review FP/FN cases. | Error analysis report |
| 15 | **Final Summary** | Consolidate final model performance and select the best model. | Final results |

---

## Core Python Package

All I/O, feature engineering, modelling, and serving logic lives in the `fraud_detect` package so that notebooks, the API, and the web app consume a single, tested implementation rather than duplicating code.

| Module | Responsibility |
|---|---|
| `config.py` | Centralised paths, column groups, hyperparameters, and tuning spaces |
| `io.py` | Parquet/CSV read/write; `load_train_features()` with fallback |
| `data.py` | `reduce_mem_usage()`, missing-value reporting, per-column imputation strategy |
| `features.py` | Vectorised time, amount, email, and card feature transforms |
| `models.py` | Train/validation split, logistic pipeline, LightGBM / XGBoost / CatBoost, CV |
| `tuning.py` | Optuna optimisation and persistence of best parameters |
| `ensemble.py` | Hard/soft voting and stacking ensembles |
| `evaluation.py` | Metrics, optimal threshold, model comparison, McNemar's test |
| `error_analysis.py` | Error segmentation, distribution shift, FP/FN analysis |
| `viz.py` | All plotting for EDA, evaluation, and error analysis (18 functions) |
| `serving.py` | Model artefact save/load, feature alignment, risk tiers, prediction, SHAP explanation |
| `_exceptions.py` | Domain exceptions (`FraudDetectError`, `MissingArtefactError`, `InvalidDataError`) |

---

## Service & Web App

The trained model is exposed through a **FastAPI** service with a browser-based review console in **vanilla JavaScript + Chart.js** (English UI), served by FastAPI at `/`. It is built for a fraud-analyst / reviewer workflow.

### API endpoints

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/health` | Service status + model presence |
| `GET` | `/api/model` | Served model metadata (version, ROC-AUC) |
| `GET` | `/api/stats` | Dataset overview + top features (for the UI) |
| `POST` | `/api/predict` | Score a single transaction → probability, risk tier, action |
| `POST` | `/api/predict/batch` | Upload a CSV of transactions → scored rows |
| `POST` | `/api/explain` | SHAP top contributors for one transaction |
| `POST` | `/api/feedback` | Record a reviewer verdict into the retrain pool |
| `POST` | `/api/retrain` | Train a candidate; swap if it beats the gate (admin) |

Interactive API docs are available at `/docs`.

### Frontend tabs

- **Score** — enter a few transaction fields (the rest default to the training median); see a probability gauge, risk tier, recommended action, and a SHAP bar chart explaining *why*.
- **Batch** — upload a CSV, inspect the risk-tier breakdown and preview table, and download the scored CSV.
- **Model** — served model metadata, dataset overview, and top predictive features.

### Feedback & auto-retraining

Reviewers mark a transaction safe or fraud; each vote is appended to `data/feedback/`
(gitignored). A scheduled retrain (`scripts/retrain.py`) folds that pool into the next
run and **only swaps the served model when the candidate scores ≥ the current model on a
held-out validation split** — an anti-regression gate. A failed gate never touches the
deployed model, so the loop is safe to run on a cron.

---

## Results (honest evaluation)

The headline metric is **ROC-AUC 0.909 on a time-ordered validation split**
(the last ~20% of the time series is held out, so the model is scored on
transactions that happen after everything it trained on).

A **random split scores 0.954** — that number is **inflated by temporal
leakage** (a random split lets the model memorise time-correlated signal),
so it is reported for transparency, not as the result. Reproducible metrics
live in [`data/metadata/evaluation.json`](data/metadata/evaluation.json) and
[`docs/MODEL_CARD.md`](docs/MODEL_CARD.md).

| Metric | Time-ordered split (honest) | Random split (inflated) |
|---|---|---|
| **ROC-AUC** | **0.909** | 0.954 |
| PR-AUC | 0.562 | 0.773 |
| Brier score | 0.021 | 0.014 |
| Precision @ threshold 0.5 | 0.824 | 0.934 |
| Recall @ threshold 0.5 | 0.360 | 0.531 |
| Precision @ top 1% riskiest | 0.899 | 0.987 |
| Precision @ top 5% riskiest | 0.414 | 0.543 |

### Calibration caveat

The model is only roughly calibrated (Brier 0.021). In the top probability
decile it **under-predicts**: mean prediction 0.225 vs actual fraud rate
0.251. Treat the output as a **risk ranking**, not a calibrated likelihood,
unless you recalibrate it for your threshold.

### Optimal Hyperparameters (Optuna)

### Optimal Hyperparameters (Optuna)

```json
{
  "num_leaves": 64,
  "learning_rate": 0.05,
  "subsample": 0.8
}
```

### Top Predictive Features

Ranked by LightGBM gain importance (`dashboard/data/model_feat_importance.csv`):

| Rank | Feature | Importance |
|---|---|---|
| 1 | `V258` | 7,353 |
| 2 | `C1` | 2,483 |
| 3 | `TransactionAmt` | 2,446 |
| 4 | `card1` | 2,279 |
| 5 | `C14` | 2,236 |
| 6 | `card2` | 2,096 |
| 7 | `C13` | 1,825 |
| 8 | `D2` | 1,553 |
| 9 | `addr1` | 1,495 |
| 10 | `V294` | 1,248 |

Engineered features such as `amt_vs_addr_mean` and `card1_amt_mean` also rank among the strongest predictors, confirming the value of the feature-engineering stage.

---

## Dataset

The dataset is provided by **Vesta Corporation** through the [IEEE-CIS Fraud Detection](https://www.kaggle.com/c/ieee-fraud-detection) competition.

| File | Rows | Description |
|---|---|---|
| `train_transaction` | ~590K | Transaction records with target (`isFraud`) |
| `train_identity` | ~144K | Identity/device information (~25% coverage) |
| `test_transaction` | ~506K | Test transactions (unlabelled) |
| `test_identity` | ~133K | Test identity data |

> The dataset is **not** included in this repository. Download it from Kaggle and place the CSVs in `data/raw/` (see [Getting Started](#getting-started)).

---

## Feature Groups

| Group | Features | Description |
|---|---|---|
| **Transaction** | `TransactionAmt`, `ProductCD` | Basic transaction attributes |
| **Card** | `card1`–`card6` | Payment card information |
| **Address** | `addr1`, `addr2`, `dist1`, `dist2` | Billing address and distances |
| **Email** | `P_emaildomain`, `R_emaildomain` | Purchaser and recipient email domains |
| **Count** | `C1`–`C14` | Counting features (e.g. address matches) |
| **Time delta** | `D1`–`D15` | Time-delta features |
| **Vesta** | `V1`–`V339` | Anonymised engineered features by Vesta |
| **Match** | `M1`–`M9` | Match flags |
| **Identity** | `id_01`–`id_38` | Device and identity signals |
| **Device** | `DeviceType`, `DeviceInfo` | Device metadata |

---

## Tech Stack

| Category | Tools |
|---|---|
| **Language** | Python 3.10+ |
| **Data** | Pandas, NumPy, PyArrow |
| **Visualisation** | Matplotlib, Seaborn |
| **Machine learning** | LightGBM, XGBoost, CatBoost, Scikit-learn |
| **Hyperparameter tuning** | Optuna |
| **Service** | FastAPI, Uvicorn, python-multipart |
| **Explanability** | SHAP |
| **Frontend** | Vanilla JS, Chart.js |
| **Testing** | Pytest, Hypothesis |
| **QA** | Ruff, Pre-commit |
| **Documentation** | Sphinx |
| **Storage** | Parquet (Snappy compression) |

---

## Getting Started

### Prerequisites

- Python **3.10+**
- `pip` or `conda`

### Installation

```bash
# Clone the repository
git clone https://github.com/knsiuss/ieee-fraud-detection.git
cd ieee-fraud-detection

# Create and activate a virtual environment (recommended)
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS/Linux

# Install the package in editable mode (all dependencies)
pip install -e ".[lgbm,dev]"
```

### Prepare the Data

1. Download the dataset from the [Kaggle competition page](https://www.kaggle.com/c/ieee-fraud-detection/data).
2. Place the CSV files in `data/raw/`.
3. Convert them to Parquet for faster I/O and reduced storage:

```bash
python scripts/prepare_data.py
```

### Run the Test Suite

The test suite runs without the dataset:

```bash
pytest
```

### Run the Notebooks

```bash
jupyter notebook notebook/
```

Execute notebooks in numerical order (`01` → `15`).

### Train the Service Model

```bash
python scripts/train_model.py
```

Writes a serving artefact to `data/models/current/` (model, feature list, median baseline, and metadata). On a fresh clone with no Kaggle data it falls back to the committed demo sample.

### Run the Service

```bash
uvicorn api.main:app --reload
```

Open `http://localhost:8000` for the review console, or `http://localhost:8000/docs` for the interactive API docs.

### Auto-retrain (optional)

```bash
python scripts/retrain.py            # once, manually
# 7 4 * * *  python scripts/retrain.py >> retrain.log 2>&1   # cron
```

---

## Deployment

The API and frontend are served from a single process, so free-tier hosting is straightforward.

### Docker

```bash
docker build -t fraud-detection .
docker run -p 8000:8000 fraud-detection
```

The image bootstraps a model from the bundled training data so it responds cold. Mount `data/models` and `data/feedback` as a volume to keep retrained artefacts across restarts.

### Free hosting options

| Component | Host |
|---|---|
| FastAPI + frontend (single service) | **Render** free tier or **Hugging Face Spaces** |
| Frontend hosted separately | **Netlify** / **GitHub Pages** (set `window.API_BASE`) |
| Scheduled retraining | GitHub Actions `schedule`, or cron on the host |

Free hosting services sleep after idle, so the first request can be slow (cold start) — expected for a demo, and fine once the service is warm.

---

## Development & QA

```bash
pip install -e ".[lgbm,dev]"
pre-commit install
make lint
make test
```

Continuous integration runs **lint and tests on Python 3.10, 3.11, and 3.12** for every push to `main` (`.github/workflows/ci.yml`), and the documentation is built and deployed to GitHub Pages on the main branch (`.github/workflows/docs.yml`).

---

## Reproducing Results

```bash
# 1. Train + serialise the serving artefact (needs the merged table)
python scripts/train_model.py

# 2. Honest evaluation — random vs time-ordered split, full metric set
python scripts/evaluate_model.py        # -> data/metadata/evaluation.json

# 3. Drift / data-quality report against a recent transactions file
python scripts/drift_report.py          # -> data/metadata/drift_report.json

# 4. Tests (no dataset required)
make lint && make test
```

Every number in this README comes from those scripts (fixed seeds and
splits in `fraud_detect/config.py`).

---

## Limitations

- **Data is from 2017–2018** (Vesta / IEEE contest) — outdated relative to
  current fraud patterns; the model is a benchmark, not a live system.
- **Temporal leakage** inflates any random-split metric; only the
  time-ordered numbers are trustworthy.
- **Calibration is approximate** — the model under-predicts at high risk.
- **No live deployment or live labels** — real-time drift and
  label-based performance monitoring are future work
  (`docs/MODEL_CARD.md`).
- **No external dataset is merged or validated** — feature spaces are
  incompatible (`docs/EXTERNAL_DATA.md`).
- **Rate limiting is per-process and demo-grade**; the retrain guard needs
  `FRAUD_API_ADMIN_KEY` set (`docs/DEPLOYMENT.md`).

---

## Roadmap

- [x] Production-shaped pipeline + honest (time-aware) evaluation
- [x] FastAPI service: predict / batch / explain / feedback / gated retrain
- [x] Checkout-style web console with SHAP explanations (replaces Streamlit)
- [x] Model card, monitoring scaffold, external-data research, deploy docs
- [ ] Real-time prediction logging + drift alerts in the service
- [ ] Label-based performance monitoring (needs a trusted label source)
- [ ] Recalibration + threshold-setting tooling
- [ ] Public demo deployment (requires approval — see `docs/DEPLOYMENT.md`)

---

## Contributing

Contributions are welcome. Please open an issue to discuss proposed changes, and ensure the linting and test checks pass before submitting a pull request. The repo includes issue templates and a PR template under `.github/`. See [CONTRIBUTING.md](CONTRIBUTING.md).

---

## Citation

If you use this project in your work, please cite it as follows:

```bibtex
@software{frauddetection2026,
  author = {P. Kanisius Bagaskara},
  title = {{IEEE-CIS Fraud Detection}},
  year = {2026},
  url = {https://github.com/knsiuss/ieee-fraud-detection}
}
```

---

## License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.

---

<p align="center">
  <i>Complete pipeline: EDA → feature engineering → model training → tuning → ensembling → evaluation → error analysis.</i>
</p>
