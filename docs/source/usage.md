# Usage

This guide walks through a typical workflow: load data, optimise memory,
analyse missingness, engineer features, split, and train a baseline model.

## 1. Load and optimise

```python
from fraud_detect import io, data, config

df = io.load_train_features()
print(f"Loaded: {df.shape}")

df = data.reduce_mem_usage(df)
```

## 2. Analyse missingness

```python
report = data.compute_missing_report(df)
print(report["strategy"].value_counts())
```

## 3. Engineer features

```python
from fraud_detect import features

df = features.build_all_features(df)
```

## 4. Train/validation split

```python
from fraud_detect import models

split = models.make_train_val_split(df)
```

## 5. Train and evaluate baseline

```python
pipe = models.build_logistic_pipeline()
result = models.evaluate_classifier(pipe, split)

print(f"Train AUC: {result['train_auc']:.4f}")
print(f"Val AUC:   {result['val_auc']:.4f}")
```

## 6. Visualise

```python
from fraud_detect import viz

viz.configure_style()
fig, ax = viz.plot_target_distribution(df[config.TARGET_COLUMN])
viz.save_figure(fig, "figures/target_distribution.png")
```

## Running notebooks

```bash
jupyter notebook notebook/
```

Navigate notebooks in order (01 → 09) for the full analysis pipeline.
