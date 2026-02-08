<p align="center">
  <img src="https://img.shields.io/badge/Status-COMPLETED-brightgreen?style=for-the-badge" alt="Status: Completed"/>
  <img src="https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python"/>
  <img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge" alt="License"/>
  <img src="https://img.shields.io/badge/Task-Binary%20Classification-blueviolet?style=for-the-badge" alt="Task"/>
</p>

# IEEE-CIS Fraud Detection

> **End-to-end machine learning pipeline for detecting fraudulent e-commerce transactions using the IEEE-CIS / Vesta Corporation dataset from Kaggle.**

> **End-to-end machine learning pipeline for fraud detection — from data exploration to model evaluation.**

---

## Table of Contents

- [Overview](#overview)
- [Business Context](#business-context)
- [Project Structure](#project-structure)
- [Dataset](#dataset)
- [Notebook Pipeline](#notebook-pipeline)
- [Key Findings (So Far)](#key-findings-so-far)
- [Tech Stack](#tech-stack)
- [Getting Started](#getting-started)
- [Roadmap](#roadmap)
- [License](#license)
- [Author](#author)

---

## Overview

This project tackles the **IEEE-CIS Fraud Detection** challenge — predicting the probability that an online transaction is fraudulent (`isFraud`). The dataset is provided by **Vesta Corporation**, a leading payment processing company, and contains real-world anonymized transaction records.

| Aspect | Detail |
|---|---|
| **Task** | Binary Classification |
| **Target** | `isFraud` (0 = legitimate, 1 = fraud) |
| **Primary Metric** | ROC-AUC |
| **Dataset Size** | ~590K training transactions, 400+ features |
| **Fraud Rate** | ~3.5% (heavily imbalanced) |

---

## Business Context

| Scenario | Impact |
|---|---|
| False Negative (missed fraud) | Direct financial loss, trust damage |
| False Positive (false alert) | Customer friction, declined legitimate transactions |
| True Positive (caught fraud) | Prevented loss, reduced abuse |

### Key Challenges
- **Class Imbalance** — Only ~3.5% of transactions are fraudulent
- **High Dimensionality** — 400+ features including 339 anonymous engineered features (`V1`–`V339`)
- **Sparse Identity Data** — Identity table covers only ~25% of transactions
- **Extensive Missing Values** — Many features have >50% missing data
- **Temporal Features** — `TransactionDT` is relative (seconds from a reference point)

### Success Criteria
| Level | AUC Target |
|---|---|
| Bronze | > 0.90 |
| Silver | > 0.93 |
| Gold | > 0.95 |

---

## Project Structure

```
FraudDetection/
│
├── README.md                          # Project documentation (this file)
├── LICENSE                            # MIT License
├── data_prep.py                       # CSV → Parquet conversion with memory optimization
│
├── data/
│   ├── raw/                           # Original raw data files
│   ├── interim/                       # Intermediate processed data
│   └── metadata/                      # Analysis outputs & reports
│       ├── feature_importance.csv     # LightGBM feature importance scores
│       ├── missing_value_report.csv   # Missing value analysis per column
│       └── redundant_feature.csv      # Identified redundant features (132 features)
│
└── notebook/                          # Analysis & modeling notebooks
    ├── 01_data_loading_overview.ipynb        # Data loading, merging & sanity checks
    ├── 02_eda_transaction_features.ipynb     # EDA on transaction features
    ├── 03_eda_identity_features.ipynb        # EDA on identity features
    ├── 04_missing_value_analysis.ipynb       # Missing value deep-dive
    ├── 05_target_distribution_imbalance.ipynb # Target distribution & imbalance study
    ├── 06_feature_correlation_analysis.ipynb  # Feature correlation analysis
    ├── 07_feature_engineering_exploration.ipynb # Feature engineering experiments
    ├── 08_feature_importance_selection.ipynb   # Feature importance & selection
    ├── 09_baseline_model_logistic.ipynb       # Logistic regression baseline
    ├── 10_model_lightgbm.ipynb               # LightGBM model training
    ├── 11_model_xgboost.ipynb                # XGBoost model training
    ├── 12_model_catboost.ipynb               # CatBoost model training
    ├── 13_hyperparameter_tuning.ipynb        # Hyperparameter optimization
    ├── 14_model_ensemble_stacking.ipynb      # Ensemble stacking approach
    └── 15_error_analysis.ipynb               # Model error analysis
```

---

## Dataset

The dataset originates from the [IEEE-CIS Fraud Detection](https://www.kaggle.com/c/ieee-fraud-detection) Kaggle competition.

| File | Rows | Description |
|---|---|---|
| `train_transaction` | ~590K | Transaction records with target (`isFraud`) |
| `train_identity` | ~144K | Identity/device info (~25% coverage) |
| `test_transaction` | ~506K | Test transactions (no labels) |
| `test_identity` | ~133K | Test identity data |

### Feature Groups

| Group | Features | Description |
|---|---|---|
| **Transaction** | `TransactionAmt`, `ProductCD` | Basic transaction attributes |
| **Card** | `card1`–`card6` | Payment card information |
| **Address** | `addr1`, `addr2`, `dist1`, `dist2` | Billing address & distance |
| **Email** | `P_emaildomain`, `R_emaildomain` | Purchaser & recipient email domains |
| **Count** | `C1`–`C14` | Counting features (e.g., address matches) |
| **Time Delta** | `D1`–`D15` | Time delta features |
| **Vesta** | `V1`–`V339` | Anonymized engineered features by Vesta |
| **Match** | `M1`–`M9` | Match features (T/F flags) |
| **Identity** | `id_01`–`id_38` | Device & identity signals |
| **Device** | `DeviceType`, `DeviceInfo` | Device metadata |

---

## Notebook Pipeline

The analysis follows a structured, sequential notebook pipeline:

```
01 Data Loading ──► 02 EDA Transaction ──► 03 EDA Identity
        │
        ▼
04 Missing Values ──► 05 Target Imbalance ──► 06 Correlation
        │
        ▼
07 Feature Engineering ──► 08 Feature Importance
        │
        ▼
09 Logistic Baseline ──► 10 LightGBM ──► 11 XGBoost ──► 12 CatBoost
        │
        ▼
13 Hyperparameter Tuning ──► 14 Ensemble Stacking ──► 15 Error Analysis
```

| # | Notebook | Status | Description |
|---|---|---|---|
| 01 | Data Loading Overview | Done | Load parquet files, merge tables, sanity checks |
| 02 | EDA — Transaction Features | Done | Analyze transaction amount, product codes, card features |
| 03 | EDA — Identity Features | Done | Explore device info, browser, OS, identity signals |
| 04 | Missing Value Analysis | Done | Quantify missingness, define imputation strategies |
| 05 | Target Distribution Imbalance | Done | Study class imbalance (~3.5% fraud) |
| 06 | Feature Correlation Analysis | Done | Identify correlated & redundant feature groups |
| 07 | Feature Engineering Exploration | Done | Create new features, transformations |
| 08 | Feature Importance Selection | Done | LightGBM-based importance, select top features |
| 09 | Baseline Model — Logistic | Done | Logistic regression baseline model |
| 10 | Model — LightGBM | Done | LightGBM gradient boosting model |
| 11 | Model — XGBoost | Done | XGBoost gradient boosting model |
| 12 | Model — CatBoost | Done | CatBoost gradient boosting model |
| 13 | Hyperparameter Tuning | Done | Optimize hyperparameters across models |
| 14 | Model Ensemble — Stacking | Done | Stacking ensemble of best models |
| 15 | Error Analysis | Done | Analyze model errors and failure cases |

---

## Key Findings (So Far)

### Feature Importance (Top 10)
Based on LightGBM feature importance analysis:

| Rank | Feature | Importance |
|---|---|---|
| 1 | `V258` | 47,798 |
| 2 | `C1` | 22,748 |
| 3 | `DeviceInfo` | 21,567 |
| 4 | `C13` | 18,922 |
| 5 | `V201` | 12,641 |
| 6 | `R_emaildomain` | 12,605 |
| 7 | `C14` | 11,127 |
| 8 | `card2` | 10,688 |
| 9 | `V294` | 8,967 |
| 10 | `TransactionAmt` | 8,404 |

### Missing Value Strategy
- **132 redundant features** identified and flagged for removal
- Imputation strategies defined per column based on missing percentage and data type
- Features with >90% missing → indicator-only approach
- Features with moderate missingness → median imputation + missing indicator

### Memory Optimization
- Custom `reduce_mem_usage()` function for dtype downcasting
- CSV → Parquet conversion for faster I/O and reduced storage (~60-70% compression)

---

## Tech Stack

| Category | Tools |
|---|---|
| **Language** | Python 3.10+ |
| **Data** | Pandas, NumPy, PyArrow |
| **Visualization** | Matplotlib, Seaborn |
| **ML** | LightGBM, XGBoost, CatBoost, Scikit-learn |
| **Environment** | Jupyter Notebook, VS Code |
| **Storage** | Parquet (Snappy compression) |

---

## Getting Started

### Prerequisites

```bash
Python >= 3.10
pip or conda
```

### Installation

```bash
# Clone the repository
git clone https://github.com/your-username/FraudDetection.git
cd FraudDetection

# Install dependencies
pip install pandas numpy pyarrow matplotlib seaborn scikit-learn lightgbm xgboost catboost jupyter

# Download the dataset from Kaggle
# https://www.kaggle.com/c/ieee-fraud-detection/data
# Place CSV files in dataset/ folder

# Convert CSV to Parquet (optimized storage)
python data_prep.py
```

### Run Notebooks

```bash
jupyter notebook notebook/
```

Navigate notebooks in order (`01` → `15`) for the complete end-to-end machine learning pipeline.

---

## Roadmap

- [x] Data loading & validation
- [x] Exploratory data analysis (transaction + identity)
- [x] Missing value analysis & imputation strategy
- [x] Target distribution & imbalance study
- [x] Feature correlation analysis
- [x] Feature engineering exploration
- [x] Feature importance & selection
- [x] Full data preprocessing pipeline
- [x] Baseline model (Logistic Regression)
- [x] Advanced models (LightGBM, XGBoost, CatBoost)
- [x] Hyperparameter tuning
- [x] Ensemble stacking approach
- [x] Model evaluation & comparison
- [x] Error analysis
- [ ] Documentation & final report

---

## License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.

---

## Author

**P. Kanisius Bagaskara**

---

<p align="center">
  <i>Complete end-to-end ML pipeline demonstrating best practices in fraud detection modeling.</i>
</p>
