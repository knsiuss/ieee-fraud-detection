# Notebook Pipeline

This directory contains the analysis and modeling notebooks for the IEEE-CIS Fraud Detection project. Run them in numerical order as later notebooks depend on artefacts produced by earlier ones.

## Pipeline Dependency Graph

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
       07 ──► 08 ──► 09
```

## Notebook Index

| # | Notebook | Description | Key Output |
|---|----------|-------------|------------|
| 01 | `01_data_loading.ipynb` | Load parquet files, merge transaction + identity, sanity checks | `train_merged.parquet` |
| 02 | `02_eda_transaction.ipynb` | EDA on transaction, card, email, count features | Insights & feature ideas |
| 03 | `03_eda_identity.ipynb` | EDA on device, browser, identity features | Identity coverage analysis |
| 04 | `04_missing_value_analysis.ipynb` | Missingness quantification, imputation strategy | `missing_value_report.csv` |
| 05 | `05_target_distribution_imbalance.ipynb` | Class imbalance analysis & mitigation | Resampling strategy |
| 06 | `06_feature_correlation_analysis.ipynb` | Feature redundancy detection | `redundant_feature.csv` |
| 07 | `07_feature_engineering_exploration.ipynb` | Feature engineering experiments | `train_features.parquet` |
| 08 | `08_feature_importance_selection.ipynb` | LightGBM importance, feature selection | `feature_importance.csv` |
| 09 | `09_baseline_model_logistic.ipynb` | Logistic regression baseline | Model evaluation |

## Setup

Before running notebooks, install the package:

```bash
pip install -e ".[lgbm,dev]"
```

Notebooks also inject `src/` onto `sys.path` as a fallback. Ensure the raw data CSVs have been converted to Parquet:

```bash
python data_prep.py
```
