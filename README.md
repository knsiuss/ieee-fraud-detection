<p align="center">
  <img src="https://img.shields.io/badge/Status-COMPLETED-brightgreen?style=for-the-badge" alt="Status: Completed"/>
  <img src="https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python"/>
  <img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge" alt="License"/>
  <img src="https://img.shields.io/badge/Task-Binary%20Classification-blueviolet?style=for-the-badge" alt="Task"/>
  <img src="https://img.shields.io/github/actions/workflow/status/knsiuss/ieee-fraud-detection/ci.yml?branch=main&style=for-the-badge&label=CI&logo=github" alt="CI"/>
  <img src="https://img.shields.io/badge/pre--commit-active-brightgreen?style=for-the-badge&logo=pre-commit" alt="pre-commit"/>
  <img src="https://img.shields.io/badge/docs-Sphinx-blue?style=for-the-badge&logo=readthedocs" alt="Docs"/>
</p>

# IEEE-CIS Fraud Detection

> **End-to-end machine learning pipeline for detecting fraudulent e-commerce transactions using the IEEE-CIS / Vesta Corporation dataset from Kaggle.**

> 📖 **Documentation**: [https://knsiuss.github.io/ieee-fraud-detection](https://knsiuss.github.io/ieee-fraud-detection)

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
- [Contributing](#contributing)
- [Citation](#citation)
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
ieee-fraud-detection/
│
├── README.md                          # Project documentation (this file)
├── LICENSE                            # MIT License
├── CONTRIBUTING.md                    # Contribution guide
├── CODE_OF_CONDUCT.md                 # Contributor Covenant v2.1
├── SECURITY.md                        # Security policy & reporting
├── pyproject.toml                     # Package metadata + dependencies
├── Makefile                           # Dev workflow shortcuts
├── .pre-commit-config.yaml            # Pre-commit hooks (ruff, format, lint)
├── scripts/                           # CLI utilities
│   └── prepare_data.py                # CSV → Parquet conversion CLI
│
├── .github/
│   ├── CODEOWNERS                     # Auto-assign reviewers
│   ├── workflows/
│   │   ├── ci.yml                     # CI: lint + test (3.10-3.12)
│   │   └── docs.yml                   # Docs: build + deploy to GitHub Pages
│   └── ISSUE_TEMPLATE/                # Bug report, feature request templates
│
├── src/fraud_detect/                  # Reusable, typed Python package
│   ├── __init__.py                    # Public API re-exports
│   ├── config.py                      # Paths, column groups, hyperparameters
│   ├── _exceptions.py                 # Domain exceptions
│   ├── io.py                          # Parquet/CSV read/write helpers
│   ├── data.py                        # Memory optimisation, missing-value reports
│   ├── features.py                    # Time/amount/email/card feature transforms
│   ├── models.py                      # Split, train, CV (3 backends + logistic)
│   ├── tuning.py                      # Optuna hyperparameter optimisation
│   ├── ensemble.py                    # Voting + stacking ensembles
│   ├── evaluation.py                  # Metrics, threshold, McNemar's test
│   ├── error_analysis.py              # Segmentation, shift, FP/FN analysis
│   └── viz.py                         # Plotting helpers (18 functions)
│
├── tests/                             # 94 tests (no dataset needed)
│   ├── conftest.py                    # Shared fixtures (synthetic_df)
│   ├── test_pure_functions.py         # Unit tests
│   ├── test_integration.py            # End-to-end pipeline tests
│   ├── test_property_based.py         # Hypothesis property-based tests
│   ├── test_models_advanced.py        # Advanced model training tests
│   ├── test_tuning.py                 # Optuna tuning tests
│   ├── test_ensemble.py               # Ensemble method tests
│   ├── test_evaluation.py             # Evaluation metric tests
│   ├── test_error_analysis.py         # Error analysis tests
│   └── test_viz_advanced.py           # Visualisation smoke tests
│
├── scripts/                           # CLI utilities
│   ├── prepare_data.py                # CSV -> Parquet conversion CLI
│   └── .gitkeep
│
├── data/
│   ├── raw/                           # Original parquet files (gitignored)
│   ├── interim/                       # Merged training table (gitignored)
│   ├── processed/                     # Engineered features (gitignored)
│   └── metadata/                      # Analysis outputs & best params
│   ├── processed/                     # Engineered features
│   └── metadata/                      # Analysis outputs & reports
│       ├── feature_importance.csv     # LightGBM feature importance scores
│       ├── missing_value_report.csv   # Missing value analysis per column
│       └── redundant_feature.csv      # Identified redundant features
│
├── docs/                              # Sphinx documentation site
│   ├── requirements.txt               # Sphinx deps
│   └── source/                        # RST/MD sources, conf.py, API stubs
│
└── notebook/                          # Analysis & modeling notebooks
    ├── README.md                      # Pipeline index & dependency graph
    ├── 01_data_loading.ipynb                  # Data loading, merging & sanity checks
    ├── 02_eda_transaction.ipynb               # EDA on transaction features
    ├── 03_eda_identity_features.ipynb         # EDA on identity features
    ├── 04_missing_value_analysis.ipynb        # Missing value deep-dive
    ├── 05_target_distribution_imbalance.ipynb # Target distribution & imbalance study
    ├── 06_feature_correlation_analysis.ipynb  # Feature correlation analysis
    ├── 07_feature_engineering_exploration.ipynb # Feature engineering experiments
    ├── 08_feature_importance_selection.ipynb  # Feature importance & selection
    └── 09_baseline_model_logistic.ipynb       # Logistic-regression baseline
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
01 ──► 02 ──► 03
 │              │
 └────► 04 ────┤
       │       │
       ├──► 05 │
       │       │
       └──► 06 │
              │
              ▼
       07 ──► 08 ──► 09 ──► 10 ──► 11 ──► 12 ──► 13 ──► 14 ──► 15
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
| 09 | Baseline Model (Logistic Regression) | Done | Logistic regression baseline evaluation |
| 10 | Advanced Model Training | Done | LightGBM, XGBoost, CatBoost with CV |
| 11 | Hyperparameter Tuning | Done | Optuna-based optimisation (100 trials) |
| 12 | Ensemble Methods | Done | Hard/soft voting + stacking ensembles |
| 13 | Model Evaluation & Comparison | Done | ROC, PR, threshold, McNemar's test |
| 14 | Error Analysis | Done | Segmentation, shift, FP/FN analysis |
| 15 | Final Summary | Done | Pipeline recap & final results |
---

## Key Findings

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
- Shared `fraud_detect.data.reduce_mem_usage()` function for dtype downcasting
- CSV → Parquet conversion via `scripts/prepare_data.py` for faster I/O and reduced storage (~60-70% compression)

### Package Architecture
The `src/fraud_detect/` package provides typed, documented utilities consumed by
the notebooks so that I/O, feature engineering, plotting and modelling logic
live in exactly one place:

| Module | Responsibility |
|---|---|
| `config.py` | Paths, column groups, hyperparameters, tuning spaces |
| `io.py` | Parquet/CSV read/write, `load_train_features()` with fallback |
| `data.py` | `reduce_mem_usage`, `compute_missing_report`, imputation strategy |
| `features.py` | Vectorised time/amount/email/card feature transforms |
| `models.py` | Train/val split, logistic pipeline, LightGBM/XGBoost/CatBoost, CV |
| `tuning.py` | Optuna hyperparameter optimisation, save/load best params |
| `ensemble.py` | Hard/soft voting, stacking ensembles |
| `evaluation.py` | Metrics, optimal threshold, model comparison, McNemar's test |
| `error_analysis.py` | Error segmentation, distribution shift, FP/FN analysis |
| `viz.py` | All plotting (EDA + evaluation + error analysis), 18 functions |
| `_exceptions.py` | Domain exceptions (`FraudDetectError`, `MissingArtefactError`, `InvalidDataError`) |

---

## Tech Stack

| Category | Tools |
|---|---|
| **Language** | Python 3.10+ |
| **Data** | Pandas, NumPy, PyArrow |
| **Visualization** | Matplotlib, Seaborn |
| **ML** | LightGBM, XGBoost, CatBoost, Scikit-learn |
| **Tuning** | Optuna |
| **Testing** | Pytest, Hypothesis |
| **QA** | Ruff, Pre-commit |
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
git clone https://github.com/knsiuss/ieee-fraud-detection.git
cd ieee-fraud-detection

# Create a virtual environment (optional but recommended)
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS/Linux

# Install the package in editable mode (pulls in all dependencies)
pip install -e ".[lgbm,dev]"

# Download the dataset from Kaggle
# https://www.kaggle.com/c/ieee-fraud-detection/data
# Place CSV files in data/raw/ folder

# Convert CSV to Parquet (optimized storage)
python scripts/prepare_data.py

# Run the smoke tests (no dataset required)
pytest
```

> Notebooks that use the shared utilities import `fraud_detect`. They also
> inject `src/` onto `sys.path` so they run without an editable install, but
> `pip install -e .` is the recommended setup.

### Run Notebooks

```bash
jupyter notebook notebook/
```

Navigate notebooks in order (`01` → `09`) for the full analysis, feature engineering, and baseline modeling pipeline. Advanced modeling notebooks are upcoming.

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
- [x] Hyperparameter tuning (Optuna)
- [x] Ensemble methods (voting + stacking)
- [x] Model evaluation & comparison
- [x] Error analysis
- [x] Documentation & final report

---

## Contributing

Contributions are welcome! Please see the [CONTRIBUTING.md](CONTRIBUTING.md) for detailed setup instructions, code conventions, and the PR workflow.

Quickstart:

```bash
pip install -e ".[lgbm,dev]"
pre-commit install
make lint
make test
```

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

## Author

**P. Kanisius Bagaskara**

---

<p align="center">
  <i>Pipeline complete — EDA, feature engineering, advanced models, tuning, ensemble, evaluation, and error analysis done.</i>
</p>
