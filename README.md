<p align="center">
  <img src="https://img.shields.io/badge/Status-COMPLETED-brightgreen?style=for-the-badge" alt="Status: Completed"/>
  <img src="https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python 3.10+"/>
  <img src="https://img.shields.io/badge/ROC--AUC-0.910-blue?style=for-the-badge" alt="ROC-AUC 0.910"/>
  <img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge" alt="MIT License"/>
  <img src="https://img.shields.io/github/actions/workflow/status/knsiuss/ieee-fraud-detection/ci.yml?branch=main&style=for-the-badge&label=CI&logo=github" alt="CI"/>
</p>

# IEEE-CIS Fraud Detection

> End-to-end machine learning solution for detecting fraudulent e-commerce transactions, built on the [IEEE-CIS / Vesta Corporation](https://www.kaggle.com/c/ieee-fraud-detection) dataset.

This repository contains a complete, production-shaped data science pipeline — from raw data ingestion through exploratory analysis, feature engineering, model training, hyperparameter optimisation, ensembling, and evaluation — packaged as a reusable Python module (`fraud_detect`), a series of reproducible analysis notebooks, and an interactive Streamlit dashboard.

---

## Table of Contents

- [Repository Structure](#repository-structure)
- [Analysis Pipeline](#analysis-pipeline)
- [Core Python Package](#core-python-package)
- [Interactive Dashboard](#interactive-dashboard)
- [Results](#results)
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
│   └── _exceptions.py           #   Domain exceptions
│
├── notebook/                    # 15 ordered analysis notebooks (01–15)
│   ├── README.md                #   Notebook index & dependency graph
│   ├── 01_data_loading.ipynb    #   Data loading, merging & sanity checks
│   ├── 02_eda_transaction.ipynb #   EDA — transaction features
│   └── ...                       #   (see Analysis Pipeline table below)
│
├── dashboard/                   # Interactive Streamlit dashboard
│   ├── app.py                   #   Main dashboard application
│   └── data/                    #   Pre-computed analysis CSVs
│
├── scripts/
│   └── prepare_data.py          # CSV → Parquet conversion CLI
│
├── tests/                       # 102 unit / integration / property tests (no dataset required)
│
├── data/
│   ├── raw/                     # Original Kaggle CSVs (gitignored)
│   ├── interim/                 # Merged training table (gitignored)
│   ├── processed/               # Engineered features (gitignored)
│   └── metadata/                # Analysis outputs & best parameters
│
├── docs/                        # Sphinx documentation source
├── .github/workflows/           # CI (lint + test) and docs deployment workflows
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

All I/O, feature engineering, modelling, and evaluation logic lives in the `fraud_detect` package so that notebooks and the dashboard consume a single, tested implementation rather than duplicating code.

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
| `_exceptions.py` | Domain exceptions (`FraudDetectError`, `MissingArtefactError`, `InvalidDataError`) |

---

## Interactive Dashboard

An interactive exploration tool built with **Streamlit** lets stakeholders inspect the data without touching code:

```bash
streamlit run dashboard/app.py
```

The dashboard surfaces pre-computed analysis of fraud rates by hour, day of week, device type, product code, card type, and email domain, alongside feature-group importance and final model metrics. All visualisations are rendered from committed CSVs in `dashboard/data/`.

---

## Results

The reference model is a **tuned LightGBM** classifier. Metrics below are reported on a held-out validation split (64K train / 16K validation samples).

| Metric | Value |
|---|---|
| **ROC-AUC** | **0.910** |
| Average precision | 0.615 |
| Precision (threshold 0.5) | 0.843 |
| Recall (threshold 0.5) | 0.387 |

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
| **Dashboard** | Streamlit |
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

### Run the Dashboard

```bash
streamlit run dashboard/app.py
```

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

## Contributing

Contributions are welcome. Please open an issue to discuss proposed changes, and ensure the linting and test checks pass before submitting a pull request. The repo includes issue templates and a PR template under `.github/`.

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
