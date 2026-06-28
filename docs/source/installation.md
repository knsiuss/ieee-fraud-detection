# Installation

## Prerequisites

- Python >= 3.10
- pip or conda

## Editable install (recommended)

```bash
git clone https://github.com/knsiuss/ieee-fraud-detection.git
cd ieee-fraud-detection

# Create a virtual environment
python -m venv .venv
source .venv/bin/activate   # macOS/Linux
# .venv\Scripts\activate     # Windows

# Install with all optional dependencies
pip install -e ".[lgbm,dev,docs]"
```

## Installing extras

| Extra | Purpose |
|---|---|
| `[lgbm]` | LightGBM for feature importance |
| `[xgb]` | XGBoost support |
| `[cat]` | CatBoost support |
| `[dev]` | Testing & linting tools |
| `[docs]` | Documentation build tools |

## Verify the install

```python
>>> from fraud_detect import __version__
>>> __version__
'0.1.0'
```

## Data

Download the dataset from
[Kaggle](https://www.kaggle.com/c/ieee-fraud-detection/data) and place CSV
files in `data/raw/`. Then convert to Parquet:

```bash
python data_prep.py
```
