"""Precompute aggregated statistics for the Streamlit dashboard.

Run once after the merged parquet is available:
    python dashboard/precompute.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score, precision_recall_curve, average_precision_score
import numpy as np
import pandas as pd
import lightgbm as lgb

_SRC = Path(__file__).resolve().parents[1] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from fraud_detect import config  # noqa: E402

OUT = Path(__file__).resolve().parent / "data"
OUT.mkdir(parents=True, exist_ok=True)

N_SAMPLE = 80_000


def _hour(dt): return (dt // 3600) % 24
def _dow(dt): return (dt // 86400) % 7
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def precompute():
    print("Loading merged parquet …")
    df = pd.read_parquet(config.MERGED_TRAIN_PATH)
    N = len(df)

    # ── 0. Sample ───────────────────────────────────────────────────────
    sample = df.sample(n=min(N_SAMPLE, N), random_state=42).reset_index(drop=True)
    sample.to_parquet(OUT / "sample.parquet", engine="pyarrow", compression="snappy")
    print(f"  sample → {OUT / 'sample.parquet'}  ({len(sample):,} rows)")

    # ── 1. Target ───────────────────────────────────────────────────────
    tgt = df["isFraud"].value_counts().reset_index()
    tgt.columns = ["isFraud", "count"]
    tgt["pct"] = tgt["count"] / N * 100
    tgt.to_csv(OUT / "target_dist.csv", index=False)

    # ── 2. Stats ────────────────────────────────────────────────────────
    id_cols = [c for c in df.columns if c.startswith("id_")]
    has_id = df[id_cols + ["DeviceType", "DeviceInfo"]].notna().any(axis=1)
    imb = int(df["isFraud"].value_counts().iloc[0] // df["isFraud"].value_counts().iloc[1])
    stats = {
        "total_rows": N, "total_cols": len(df.columns),
        "fraud_count": int(df["isFraud"].sum()), "fraud_rate": float(df["isFraud"].mean() * 100),
        "nonfraud_count": int((df["isFraud"] == 0).sum()), "imbalance_ratio": imb,
        "identity_coverage_pct": float(has_id.mean() * 100),
        "nunique_card1": int(df["card1"].nunique()),
        "vesta_features": int(sum(c.startswith("V") and c[1:].isdigit() for c in df.columns)),
    }
    pd.DataFrame(list(stats.items()), columns=["metric", "value"]).to_csv(OUT / "overall_stats.csv", index=False)

    # ── 3. Time ─────────────────────────────────────────────────────────
    hr = _hour(df["TransactionDT"])
    fb_h = df.groupby(hr)["isFraud"].agg(total="count", fraud="sum").reset_index().rename(columns={"TransactionDT": "hour"})
    fb_h["fraud_rate"] = fb_h["fraud"] / fb_h["total"] * 100
    fb_h["tx_pct"] = fb_h["total"] / N * 100
    fb_h.to_csv(OUT / "fraud_by_hour.csv", index=False)

    dw = _dow(df["TransactionDT"])
    fb_d = df.groupby(dw)["isFraud"].agg(total="count", fraud="sum").reset_index().rename(columns={"TransactionDT": "day_of_week"})
    fb_d["day_name"] = fb_d["day_of_week"].map(lambda x: DAYS[int(x)])
    fb_d["fraud_rate"] = fb_d["fraud"] / fb_d["total"] * 100
    fb_d.to_csv(OUT / "fraud_by_dow.csv", index=False)

    # ── 4. Product ──────────────────────────────────────────────────────
    prod = df.groupby("ProductCD")["isFraud"].agg(total="count", fraud="sum").reset_index()
    prod["fraud_rate"] = prod["fraud"] / prod["total"] * 100
    prod.to_csv(OUT / "fraud_by_product.csv", index=False)

    # ── 5. Card ─────────────────────────────────────────────────────────
    for col in ("card4", "card6"):
        g = df.groupby(col)["isFraud"].agg(total="count", fraud="sum").reset_index()
        g["fraud_rate"] = g["fraud"] / g["total"] * 100
        g.to_csv(OUT / f"fraud_by_{col}.csv", index=False)

    c1 = df.groupby("card1")["isFraud"].agg(total="count", fraud="sum").reset_index()
    c1 = c1.sort_values("total", ascending=False).head(15)
    c1["fraud_rate"] = c1["fraud"] / c1["total"] * 100
    c1.to_csv(OUT / "fraud_by_card1_top15.csv", index=False)

    # ── 6. Email ────────────────────────────────────────────────────────
    for col in ("P_emaildomain", "R_emaildomain"):
        if col not in df.columns: continue
        top = df[col].value_counts().head(15).index.tolist()
        g = df.loc[df[col].isin(top)].groupby(col)["isFraud"].agg(total="count", fraud="sum").reset_index()
        g["fraud_rate"] = g["fraud"] / g["total"] * 100
        g.to_csv(OUT / f"fraud_by_{col}.csv", index=False)

    match = (df["P_emaildomain"].astype(str) == df["R_emaildomain"].astype(str)).fillna(False)
    em = match.to_frame(name="email_match").join(df["isFraud"]).groupby("email_match")["isFraud"].mean().reset_index()
    em.columns = ["email_match", "fraud_rate"]
    em["email_match"] = em["email_match"].map({True: "Match", False: "No Match"})
    em["fraud_rate"] *= 100
    em.to_csv(OUT / "fraud_by_email_match.csv", index=False)

    # ── 7. Identity + Device ────────────────────────────────────────────
    cov = has_id.to_frame(name="has_identity").groupby("has_identity")["has_identity"].agg(count="count")
    cov.index = cov.index.map({True: "With identity", False: "Without identity"})
    cov.to_csv(OUT / "identity_coverage.csv", header=["count"])

    idf = has_id.to_frame(name="has_identity").join(df["isFraud"])
    idfr = (idf.groupby("has_identity")["isFraud"].mean() * 100).reset_index()
    idfr.columns = ["has_identity", "fraud_rate"]
    idfr["has_identity"] = idfr["has_identity"].map({True: "With identity", False: "Without identity"})
    idfr.to_csv(OUT / "fraud_by_identity.csv", index=False)

    if "DeviceType" in df.columns:
        dev = df.groupby("DeviceType", dropna=False)["isFraud"].agg(total="count", fraud="sum").reset_index()
        dev["fraud_rate"] = dev["fraud"] / dev["total"] * 100
        dev.to_csv(OUT / "fraud_by_device_type.csv", index=False)

    # ── 8. Amount ───────────────────────────────────────────────────────
    amt = df.groupby("isFraud")["TransactionAmt"].describe(percentiles=[.25, .5, .75, .9, .95, .99]).reset_index()
    amt.to_csv(OUT / "amt_by_fraud.csv", index=False)

    # ── 9. C features correlation ───────────────────────────────────────
    ccols = [f"C{i}" for i in range(1, 15)]
    ccols = [c for c in ccols if c in df.columns]
    cc = df[ccols + ["isFraud"]].corr()["isFraud"].drop("isFraud").reset_index()
    cc.columns = ["feature", "correlation"]
    cc["abs_corr"] = cc["correlation"].abs()
    cc.sort_values("abs_corr", ascending=False).to_csv(OUT / "c_features_corr.csv", index=False)

    # ── 10. Feature group importance ────────────────────────────────────
    fi_path = config.FEATURE_IMPORTANCE_PATH
    if fi_path.exists():
        fi = pd.read_csv(fi_path)
        groups = {
            "Vesta (V)": "V", "Count (C)": "C", "TimeDelta (D)": "D",
            "Match (M)": "M", "Card": "card", "Address": "addr",
            "Identity (id)": "id_", "Device": "Device", "Email": "email",
        }
        def label(f):
            for g, p in groups.items():
                if f.startswith(p): return g
            return "Other"
        fi["group"] = fi["feature"].apply(label)
        grp = fi.groupby("group")["importance"].agg(mean_imp="mean", total_imp="sum", count="count").reset_index()
        grp["pct_of_total"] = grp["total_imp"] / grp["total_imp"].sum() * 100
        grp.sort_values("mean_imp", ascending=False).to_csv(OUT / "feature_group_importance.csv", index=False)

    # ── 11. V features correlation (sample) ─────────────────────────────
    vcols = sorted((c for c in df.columns if c.startswith("V") and c[1:].isdigit()), key=lambda x: int(x[1:]))[:50]
    vc = sample[vcols + ["isFraud"]].corr()["isFraud"].drop("isFraud").reset_index()
    vc.columns = ["feature", "correlation"]
    vc["abs_corr"] = vc["correlation"].abs()
    vc.sort_values("abs_corr", ascending=False).head(20).to_csv(OUT / "v_features_corr_top20.csv", index=False)

    # ── 12. Model Performance ────────────────────────────────────────────
    print("  training LightGBM on sample …")
    train_ids = sample["TransactionID"].values
    sample_train = sample[sample["TransactionID"].isin(train_ids)].copy()
    ex_cols = ["TransactionID", "isFraud", "TransactionDT"]
    obj_cols = sample_train.select_dtypes(include=["object", "category"]).columns.tolist()
    feats = [c for c in sample_train.columns if c not in ex_cols and c not in obj_cols]

    X = sample_train[feats].fillna(-999).astype("float32")
    y = sample_train["isFraud"].values

    X_tr, X_va, y_tr, y_va = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

    lgb_params = {
        "objective": "binary", "metric": "auc", "num_leaves": 31,
        "learning_rate": 0.1, "feature_fraction": 0.8, "bagging_fraction": 0.8,
        "bagging_freq": 5, "verbose": -1, "random_state": 42,
    }
    model = lgb.train(
        lgb_params, lgb.Dataset(X_tr, label=y_tr),
        num_boost_round=200,
        valid_sets=[lgb.Dataset(X_va, label=y_va)],
        valid_names=["valid"],
        callbacks=[lgb.early_stopping(20), lgb.log_evaluation(0)],
    )

    y_prob = model.predict(X_va)
    y_pred = (y_prob >= 0.5).astype(int)

    # Metrics
    auc = float(roc_auc_score(y_va, y_prob))
    ap = float(average_precision_score(y_va, y_prob))
    from sklearn.metrics import f1_score, precision_score, recall_score, confusion_matrix
    f1 = float(f1_score(y_va, y_pred))
    prec = float(precision_score(y_va, y_pred))
    rec = float(recall_score(y_va, y_pred))
    cm = confusion_matrix(y_va, y_pred).tolist()
    tn, fp, fn, tp = cm[0][0], cm[0][1], cm[1][0], cm[1][1]
    tpr = tp / (tp + fn) if (tp + fn) else 0
    fpr = fp / (fp + tn) if (fp + tn) else 0
    youden = tpr - fpr

    metrics = {
        "auc": auc, "avg_precision": ap, "f1": f1,
        "precision": prec, "recall": rec, "youden": float(youden),
        "threshold": 0.5, "train_samples": len(X_tr), "val_samples": len(X_va),
        "tn": tn, "fp": fp, "fn": fn, "tp": tp,
    }
    metrics["tpr"] = tpr
    metrics["fpr"] = fpr

    pd.DataFrame([metrics]).to_csv(OUT / "model_metrics.csv", index=False)
    print(f"    AUC={auc:.5f} | F1={f1:.4f} | Prec={prec:.4f} | Rec={rec:.4f}")

    # Feature importance from this model too
    fi_model = pd.DataFrame({"feature": feats, "importance": model.feature_importance("gain")})
    fi_model.sort_values("importance", ascending=False).to_csv(OUT / "model_feat_importance.csv", index=False)

    # PR curve points
    precisions, recalls, thresholds = precision_recall_curve(y_va, y_prob)
    pr_df = pd.DataFrame({"precision": precisions[:-1], "recall": recalls[:-1], "threshold": thresholds})
    pr_df.to_csv(OUT / "pr_curve.csv", index=False)
    print("  model performance done")

    print("All done.")


if __name__ == "__main__":
    precompute()
