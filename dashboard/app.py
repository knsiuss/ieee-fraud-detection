"""Fraud Detection Dashboard — Streamlit App.

Usage:
    streamlit run dashboard/app.py
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st

# Custom Page Config
st.set_page_config(
    page_title="IEEE-CIS Fraud Detection Dashboard",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Custom CSS for Premium Design Look
st.markdown(
    """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700;800&display=swap');

    html, body, [class*="css"] {
        font-family: 'Outfit', sans-serif;
    }

    .main-title {
        font-size: 2.5rem;
        font-weight: 800;
        background: linear-gradient(135deg, #1e3c72, #2a5298, #c44e52);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.1rem;
    }

    .subtitle {
        font-size: 1.1rem;
        color: #888888;
        margin-bottom: 1.5rem;
    }

    /* Metrics panel decoration - size and weight only to prevent color clashes */
    div[data-testid="stMetricValue"] {
        font-size: 2rem !important;
        font-weight: 700 !important;
    }
</style>
""",
    unsafe_allow_html=True,
)

DATA_DIR = Path(__file__).resolve().parent / "data"
META_DIR = Path(__file__).resolve().parents[1] / "data" / "metadata"

C = {
    "blue": "#4c72b0",
    "red": "#c44e52",
    "green": "#55a868",
    "orange": "#dd8452",
    "coral": "#e74c3c",
}


# Matplotlib styling helper for a clean, premium visual aesthetic
def apply_plot_theme(fig, ax):
    fig.patch.set_facecolor("#ffffff")  # Solid white background
    ax.set_facecolor("#ffffff")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#cccccc")
    ax.spines["bottom"].set_color("#cccccc")
    ax.grid(True, linestyle="--", alpha=0.5, color="#eaeaea")
    ax.tick_params(colors="#2b2b2b", which="both", labelsize=8)
    ax.yaxis.label.set_color("#2b2b2b")
    ax.xaxis.label.set_color("#2b2b2b")
    if ax.title:
        ax.title.set_color("#2b2b2b")


#  helpers


@st.cache_data
def csv(name: str) -> pd.DataFrame:
    p = DATA_DIR / name
    return pd.read_csv(p) if p.exists() else pd.DataFrame()


@st.cache_data
def meta(name: str) -> pd.DataFrame:
    p = META_DIR / name
    return pd.read_csv(p) if p.exists() else pd.DataFrame()


@st.cache_data
def stats() -> dict:
    df = csv("overall_stats.csv")
    return dict(zip(df["metric"], df["value"], strict=False)) if not df.empty else {}


@st.cache_data
def sample() -> pd.DataFrame:
    p = DATA_DIR / "sample.parquet"
    return pd.read_parquet(p) if p.exists() else pd.DataFrame()


def bar(labels, values, color=None, overall=None, ylabel="", title="", rot=0):
    fig, ax = plt.subplots(figsize=(8, 3.8))
    ax.bar(labels, values, color=color or C["blue"])
    if overall is not None:
        ax.axhline(overall, color=C["red"], ls="--", label=f"Overall ({overall:.2f}%)")
        ax.legend(fontsize=8)
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.tick_params(axis="x", rotation=rot)
    apply_plot_theme(fig, ax)
    return fig


def barh(vals, labels, color=None, title=""):
    fig, ax = plt.subplots(figsize=(8, max(3, len(labels) * 0.28)))
    ax.barh(range(len(labels)), vals, color=color or C["blue"])
    ax.set_yticks(range(len(labels)))
    ax.set_yticklabels(labels, fontsize=8)
    ax.invert_yaxis()
    ax.set_title(title)
    apply_plot_theme(fig, ax)
    return fig


def metric(col, label, val):
    col.metric(label, val)


#  page

S = stats()
OVERALL = float(S.get("fraud_rate", 0))

t1, t2, t3, t4 = st.tabs(
    [
        "EDA Overview",
        "Missing Values",
        "Feature Analysis",
        "Model Performance",
    ]
)

#
# TAB 1 — OVERVIEW
#
with t1:
    st.title("Overview — Dataset EDA")
    st.markdown(
        "Dataset-level statistics, target distribution, time patterns, card & identity features."
    )
    if not S:
        st.warning("Run `python dashboard/precompute.py` first.")
        st.stop()

    cols = st.columns(6)
    metric(cols[0], "Transactions", f"{S['total_rows']:,.0f}")
    metric(cols[1], "Columns", f"{S['total_cols']:,.0f}")
    metric(cols[2], "Fraud Rate", f"{OVERALL:.2f}%")
    metric(cols[3], "Fraud Cases", f"{S['fraud_count']:,.0f}")
    metric(cols[4], "Imbalance", f"{S['imbalance_ratio']:.0f}:1")
    metric(cols[5], "Identity Coverage", f"{S['identity_coverage_pct']:.1f}%")

    st.divider()

    #  Row 1: Target + Product
    r1 = st.columns(2)
    with r1[0]:
        tgt = csv("target_dist.csv")
        if not tgt.empty:
            st.markdown("**Target Distribution**")
            fig, ax = plt.subplots(figsize=(4.5, 3))
            bars = ax.bar(["Not Fraud", "Fraud"], tgt["count"], color=[C["blue"], C["red"]])
            for b, r in zip(bars, tgt.itertuples(), strict=False):
                ax.text(
                    b.get_x() + b.get_width() / 2,
                    b.get_height(),
                    f"{r.count:,}\n({r.pct:.1f}%)",
                    ha="center",
                    va="bottom",
                    fontsize=8,
                )
            ax.set_ylabel("Count")
            apply_plot_theme(fig, ax)
            st.pyplot(fig, use_container_width=True)

    with r1[1]:
        prod = csv("fraud_by_product.csv")
        if not prod.empty:
            st.markdown("**Fraud Rate by Product**")
            ps = prod.sort_values("fraud_rate", ascending=False)
            st.pyplot(
                bar(ps["ProductCD"], ps["fraud_rate"], C["coral"], OVERALL, "Fraud Rate (%)"),
                use_container_width=True,
            )

    #  Row 2: Hour + DOW
    r2 = st.columns(2)
    with r2[0]:
        hr = csv("fraud_by_hour.csv")
        if not hr.empty:
            st.markdown("**Fraud Rate by Hour**")
            fig, ax = plt.subplots(figsize=(6, 3.5))
            ax.bar(hr["hour"], hr["fraud_rate"], color=C["blue"])
            ax.axhline(OVERALL, color=C["red"], ls="--", label=f"Overall ({OVERALL:.2f}%)")
            ax.set_xlabel("Hour")
            ax.set_ylabel("Fraud Rate (%)")
            ax.set_xticks(range(0, 24, 2))
            ax.legend(fontsize=8)
            pk = hr.loc[hr["fraud_rate"].idxmax()]
            ax.annotate(
                f"Peak: {pk['hour']:.0f}:00 ({pk['fraud_rate']:.1f}%)",
                xy=(pk["hour"], pk["fraud_rate"]),
                xytext=(pk["hour"] + 3, pk["fraud_rate"] + 0.5),
                arrowprops=dict(arrowstyle="->", color="gray"),
                fontsize=8,
            )
            ax2 = ax.twinx()
            ax2.plot(
                hr["hour"],
                hr["tx_pct"],
                color=C["orange"],
                marker=".",
                alpha=0.6,
                label="% of Total TX",
            )
            ax2.set_ylabel("% of TX", fontsize=9)
            ax2.legend(fontsize=8, loc="upper left")
            # For the twin axis, also style spines
            ax2.spines["top"].set_visible(False)
            ax2.spines["right"].set_color("#cccccc")
            ax2.spines["left"].set_color("#cccccc")
            ax2.spines["bottom"].set_color("#cccccc")
            ax2.tick_params(colors="#888888", labelsize=8)
            ax2.yaxis.label.set_color("#888888")
            apply_plot_theme(fig, ax)
            st.pyplot(fig, use_container_width=True)

    with r2[1]:
        dow = csv("fraud_by_dow.csv")
        if not dow.empty:
            st.markdown("**Fraud Rate by Day of Week**")
            st.pyplot(
                bar(
                    dow["day_name"],
                    dow["fraud_rate"],
                    C["green"],
                    OVERALL,
                    "Fraud Rate (%)",
                    rot=30,
                ),
                use_container_width=True,
            )

    #  Row 3: Card
    st.divider()
    st.markdown("### Card Features")
    r3 = st.columns(3)

    with r3[0]:
        c4 = csv("fraud_by_card4.csv")
        if not c4.empty:
            st.caption("Fraud by Card Network")
            c4s = c4.sort_values("fraud_rate", ascending=False)
            st.pyplot(
                bar(c4s["card4"], c4s["fraud_rate"], C["green"], OVERALL), use_container_width=True
            )

    with r3[1]:
        c6 = csv("fraud_by_card6.csv")
        if not c6.empty:
            st.caption("Fraud by Card Type")
            c6s = c6.sort_values("fraud_rate", ascending=False)
            st.pyplot(
                bar(c6s["card6"], c6s["fraud_rate"], C["orange"], OVERALL), use_container_width=True
            )

    with r3[2]:
        c1 = csv("fraud_by_card1_top15.csv")
        if not c1.empty:
            st.caption("Top 15 Card Issuers (card1)")
            frac = c1["fraud_rate"] / c1["fraud_rate"].max()
            colors = plt.cm.Reds(frac.values)
            fig, ax = plt.subplots(figsize=(4.5, 3))
            ax.barh(range(len(c1)), c1["fraud_rate"], color=colors)
            ax.set_yticks(range(len(c1)))
            ax.set_yticklabels(c1["card1"].astype(int), fontsize=7)
            ax.invert_yaxis()
            ax.set_xlabel("Fraud Rate (%)")
            apply_plot_theme(fig, ax)
            st.pyplot(fig, use_container_width=True)

    #  Row 4: Identity + Device + Amount
    st.divider()
    st.markdown("### Identity, Device & Amount")
    r4 = st.columns(3)

    with r4[0]:
        cov = csv("identity_coverage.csv")
        if not cov.empty:
            st.caption("Identity Coverage")
            fig, ax = plt.subplots(figsize=(4, 3))
            ax.bar(cov["has_identity"], cov["count"], color=[C["blue"], C["red"]])
            ax.set_ylabel("Count")
            for i, v in enumerate(cov["count"]):
                ax.text(i, v + 5000, f"{v:,}", ha="center", fontsize=9)
            apply_plot_theme(fig, ax)
            st.pyplot(fig, use_container_width=True)

    with r4[1]:
        idf = csv("fraud_by_identity.csv")
        if not idf.empty:
            st.caption("Fraud Rate by Identity Presence")
            st.pyplot(
                bar(idf["has_identity"], idf["fraud_rate"], [C["red"], C["blue"]], OVERALL),
                use_container_width=True,
            )

    with r4[2]:
        dev = csv("fraud_by_device_type.csv")
        if not dev.empty:
            st.caption("Fraud by Device Type")
            d = dev.sort_values("fraud_rate", ascending=False)
            st.pyplot(
                bar(
                    d["DeviceType"].fillna("NaN").astype(str), d["fraud_rate"], C["coral"], OVERALL
                ),
                use_container_width=True,
            )

    #  Row 5: Amount + Email
    r5 = st.columns(2)
    with r5[0]:
        amt = csv("amt_by_fraud.csv")
        if not amt.empty:
            st.caption("Amount Stats by Fraud Status")
            amt["isFraud"] = amt["isFraud"].map({0: "Not Fraud", 1: "Fraud"})
            sc = ["mean", "std", "50%", "75%", "95%"]
            x = np.arange(len(sc))
            w = 0.35
            fig, ax = plt.subplots(figsize=(5, 3.5))
            cols_ = [C["blue"], C["red"]]
            for i, r in amt.iterrows():
                vals = [r[c] for c in sc]
                ax.bar(
                    x + (-w / 2 if i == 0 else w / 2),
                    vals,
                    w,
                    label=r["isFraud"],
                    color=cols_[i],
                    alpha=0.8,
                )
            ax.set_xticks(x)
            ax.set_xticklabels(["Mean", "Std", "Median", "P75", "P95"], fontsize=8)
            ax.set_ylabel("$")
            ax.legend(fontsize=8)
            apply_plot_theme(fig, ax)
            st.pyplot(fig, use_container_width=True)

    with r5[1]:
        eml = csv("fraud_by_P_emaildomain.csv")
        if not eml.empty:
            st.caption("Fraud Rate by Email Domain (P_emaildomain)")
            eml_s = eml.sort_values("fraud_rate", ascending=False)
            st.pyplot(
                bar(eml_s["P_emaildomain"], eml_s["fraud_rate"], C["coral"], OVERALL, rot=45),
                use_container_width=True,
            )

    match = csv("fraud_by_email_match.csv")
    if not match.empty:
        st.caption("Fraud Rate by Email Match")
        st.pyplot(
            bar(match["email_match"], match["fraud_rate"], [C["blue"], C["red"]], OVERALL),
            use_container_width=True,
        )


#
# TAB 2 — MISSING VALUES
#
with t2:
    st.title("Missing Value Analysis")
    st.markdown("Missing value distribution, imputation strategies, and per-column analysis.")
    rpt = meta("missing_value_report.csv")
    if rpt.empty:
        st.warning("missing_value_report.csv not found.")
        st.stop()

    cols = st.columns(4)
    metric(cols[0], "Total Columns", len(rpt))
    metric(cols[1], "With Missing", len(rpt[rpt["missing_pct"] > 0]))
    metric(cols[2], ">75% Missing", len(rpt[rpt["missing_pct"] > 75]))
    metric(cols[3], "0% Missing", len(rpt[rpt["missing_pct"] == 0]))

    st.divider()

    r1 = st.columns(2)
    with r1[0]:
        st.markdown("**Imputation Strategy Summary**")
        strat = rpt["strategy"].value_counts()
        fig, ax = plt.subplots(figsize=(5, 3.5))
        colors = [C["green"], C["blue"], C["orange"], C["red"], "#7f7f7f"]
        bars = ax.bar(strat.index, strat.values, color=colors[: len(strat)])
        for b, v in zip(bars, strat.values, strict=False):
            ax.text(
                b.get_x() + b.get_width() / 2, b.get_height() + 1, str(v), ha="center", fontsize=9
            )
        ax.set_ylabel("Count")
        ax.tick_params(axis="x", rotation=30)
        apply_plot_theme(fig, ax)
        st.pyplot(fig, use_container_width=True)

    with r1[1]:
        st.markdown("**Missing % Buckets**")
        bins = [0, 1, 10, 50, 75, 90, 100]
        lbl = ["0%", "1-10%", "10-50%", "50-75%", "75-90%", ">90%"]
        rpt["b"] = pd.cut(rpt["missing_pct"], bins=bins, labels=lbl)
        buck = rpt["b"].value_counts().reindex(lbl)
        fig, ax = plt.subplots(figsize=(5, 3.5))
        ax.bar(buck.index, buck.values, color=C["blue"])
        for i, v in enumerate(buck.values):
            ax.text(i, v + 1, str(v), ha="center", fontsize=9)
        ax.set_ylabel("Count")
        ax.tick_params(axis="x", rotation=30)
        apply_plot_theme(fig, ax)
        st.pyplot(fig, use_container_width=True)

    st.divider()
    st.markdown("**Top Missing Columns**")
    n = st.slider("Count", 10, 434, 30, key="mv_n")
    top = rpt.sort_values("missing_pct", ascending=False).head(n)
    colors = [
        C["red"] if v > 75 else C["orange"] if v > 50 else C["blue"] for v in top["missing_pct"]
    ]
    st.pyplot(
        barh(top["missing_pct"], top["column"], colors, f"Top {n} by Missing %"),
        use_container_width=True,
    )

    st.divider()
    r2 = st.columns(2)
    with r2[0]:
        st.markdown("**Avg Missing % by Data Type**")
        dtype_m = rpt.groupby("dtype")["missing_pct"].mean().sort_values(ascending=False)
        st.pyplot(
            bar(dtype_m.index, dtype_m.values, C["green"], ylabel="Avg Missing (%)", rot=30),
            use_container_width=True,
        )
    with r2[1]:
        st.markdown("**Strategy × Data Type**")
        st.dataframe(pd.crosstab(rpt["dtype"], rpt["strategy"]), use_container_width=True)

    with st.expander(" Full Report"):
        cols = st.multiselect(
            "Columns", rpt.columns.tolist(), default=["column", "missing_pct", "dtype", "strategy"]
        )
        if cols:
            st.dataframe(
                rpt[cols].sort_values("missing_pct", ascending=False),
                use_container_width=True,
                hide_index=True,
            )


#
# TAB 3 — FEATURE IMPORTANCE
#
with t3:
    st.title("Feature Importance & Correlation")
    st.markdown(
        "Feature gain importance, group breakdown, correlations with fraud, and redundant features."
    )
    imp = meta("feature_importance.csv")
    if imp.empty:
        st.warning("feature_importance.csv not found.")
        st.stop()

    total = len(imp)
    top5_pct = imp.head(5)["importance"].sum() / imp["importance"].sum() * 100
    zero = len(imp[imp["importance"] == 0])

    cols = st.columns(4)
    metric(cols[0], "Total Features", total)
    metric(cols[1], "Top 5 Account For", f"{top5_pct:.1f}%")
    metric(cols[2], "Zero-Importance", f"{zero} ({zero / total * 100:.1f}%)")
    redundant = meta("redundant_feature.csv")
    if not redundant.empty:
        metric(cols[3], "Redundant", len(redundant))

    st.divider()

    #  Top-N
    st.markdown("**Top Features by Gain Importance**")
    n = st.slider("Features", 10, min(200, total), 30, key="fi_n")
    top = imp.sort_values("importance", ascending=False).head(n)
    st.pyplot(
        barh(top["importance"], top["feature"], title=f"Top {n} Features"), use_container_width=True
    )

    st.divider()

    #  Feature groups
    grp = csv("feature_group_importance.csv")
    if not grp.empty:
        st.markdown("### Feature Group Analysis")
        r1 = st.columns(2)
        with r1[0]:
            fig, ax = plt.subplots(figsize=(5, 3.5))
            ax.bar(grp["group"], grp["mean_imp"], color=C["green"])
            ax.tick_params(axis="x", rotation=45)
            ax.set_ylabel("Mean Importance")
            for i, v in enumerate(grp["mean_imp"]):
                ax.text(i, v + max(grp["mean_imp"]) * 0.02, f"{v:.0f}", ha="center", fontsize=7)
            apply_plot_theme(fig, ax)
            st.pyplot(fig, use_container_width=True)
        with r1[1]:
            fig, ax = plt.subplots(figsize=(5, 3.5))
            # Pie charts have different structures, but we can set transparent bg
            fig.patch.set_alpha(0.0)
            ax.patch.set_alpha(0.0)
            ax.pie(
                grp["pct_of_total"],
                labels=grp["group"],
                autopct="%1.1f%%",
                startangle=90,
                textprops={"fontsize": 7, "color": "#888888"},
            )
            st.pyplot(fig, use_container_width=True)

    st.divider()

    #  Distribution
    st.markdown("### Importance Distribution")
    th = st.slider("Threshold", 0, int(imp["importance"].max()), 500, key="fi_th")
    above = imp[imp["importance"] >= th]
    r1 = st.columns([2, 1])
    with r1[0]:
        fig, ax = plt.subplots(figsize=(7, 3.5))
        ax.hist(imp["importance"], bins=80, color=C["blue"], edgecolor="white")
        ax.axvline(th, color=C["red"], ls="--", label=f"Threshold={th}")
        ax.legend(fontsize=8)
        apply_plot_theme(fig, ax)
        st.pyplot(fig, use_container_width=True)
    with r1[1]:
        a, b, c = st.columns(3)
        metric(a, "Above Threshold", f"{len(above)} / {total}")
        metric(b, "Importance Sum", f"{above['importance'].sum():,.0f}")
        metric(c, "% of Total", f"{above['importance'].sum() / imp['importance'].sum() * 100:.1f}%")

    st.divider()

    #  Correlations
    st.markdown("### Feature Correlation with isFraud")
    r1 = st.columns(2)
    with r1[0]:
        cc = csv("c_features_corr.csv")
        if not cc.empty:
            st.caption("C Features (Count)")
            colors = [C["red"] if v < 0 else C["blue"] for v in cc["correlation"]]
            fig, ax = plt.subplots(figsize=(5, 3.5))
            ax.bar(cc["feature"], cc["correlation"], color=colors)
            ax.axhline(0, color="gray", lw=0.5)
            ax.tick_params(axis="x", rotation=45)
            ax.set_ylabel("Correlation")
            apply_plot_theme(fig, ax)
            st.pyplot(fig, use_container_width=True)
    with r1[1]:
        vc = csv("v_features_corr_top20.csv")
        if not vc.empty:
            st.caption("Top 20 V Features (from sample)")
            vc = vc.sort_values("correlation")
            colors = [C["red"] if v < 0 else C["blue"] for v in vc["correlation"]]
            fig, ax = plt.subplots(figsize=(5, 3.5))
            ax.barh(range(len(vc)), vc["correlation"], color=colors)
            ax.set_yticks(range(len(vc)))
            ax.set_yticklabels(vc["feature"].values, fontsize=7)
            ax.invert_yaxis()
            ax.set_xlabel("Correlation")
            apply_plot_theme(fig, ax)
            st.pyplot(fig, use_container_width=True)

    st.divider()

    #  Redundant
    if not redundant.empty:
        st.markdown("### Redundant Features")
        rc = redundant.columns[0]
        rl = redundant[rc].dropna().tolist()
        st.info(f"**{len(rl)}** features with |r| > 0.95 — candidates for removal.")
        srch = st.text_input(" Search", "")
        flt = [f for f in rl if srch.lower() in f.lower()] if srch else rl
        st.code("\n".join(flt[:50]) + ("\n..." if len(flt) > 50 else ""))


#
# TAB 4 — MODELS
#
with t4:
    st.title("Model Performance")
    st.markdown(
        "LightGBM trained on 80K sample — metrics, confusion matrix, PR curve, and feature importance."
    )
    mm = csv("model_metrics.csv")
    if mm.empty:
        st.warning("Model metrics not found. Run `python dashboard/precompute.py` first.")
        st.stop()

    m = mm.iloc[0]

    auc_val = m["auc"]
    targets = [
        ("Target", "AUC", "Status"),
        ("Minimum", "> 0.88", "Achieved" if auc_val > 0.88 else "Missed"),
        ("Expectation", "> 0.91", "Achieved" if auc_val > 0.91 else "Missed"),
        ("Stretch", "> 0.93", "Achieved" if auc_val > 0.93 else "Missed"),
    ]
    c1, c2, c3 = st.columns(3)
    metric(c1, "ROC-AUC", f"{m['auc']:.5f}")
    metric(c2, "F1 Score", f"{m['f1']:.4f}")
    metric(c3, "Avg Precision", f"{m['avg_precision']:.4f}")
    c1, c2, c3 = st.columns(3)
    metric(c1, "Precision", f"{m['precision']:.4f}")
    metric(c2, "Recall", f"{m['recall']:.4f}")
    metric(c3, "Youden Index", f"{m['youden']:.4f}")

    st.markdown("### Result Targets")
    st.markdown(
        f"**AUC = {auc_val:.4f}** on 20% validation holdout from 80K sample. "
        "Model: LightGBM with early stopping."
    )
    st.dataframe(
        pd.DataFrame(targets[1:], columns=targets[0]),
        use_container_width=True,
        hide_index=True,
    )

    st.divider()

    st.markdown(
        f"**Model:** LightGBM on {int(m['train_samples']):,} train / {int(m['val_samples']):,} val samples"
    )
    st.markdown(
        f"**Threshold:** {m['threshold']} | **Youden Index:** {m['youden']:.4f} | **TPR:** {m['tpr']:.4f} | **FPR:** {m['fpr']:.4f}"
    )

    st.divider()

    #  Confusion Matrix
    st.markdown("### Confusion Matrix")
    r1 = st.columns(2)
    with r1[0]:
        cm = np.array([[int(m["tn"]), int(m["fp"])], [int(m["fn"]), int(m["tp"])]])
        fig, ax = plt.subplots(figsize=(4, 3.5))
        im = ax.imshow(cm, cmap="Blues", aspect="auto")
        ax.set_xticks([0, 1])
        ax.set_yticks([0, 1])
        ax.set_xticklabels(["Pred 0", "Pred 1"])
        ax.set_yticklabels(["Actual 0", "Actual 1"])
        for i in range(2):
            for j in range(2):
                ax.text(
                    j,
                    i,
                    str(cm[i, j]),
                    ha="center",
                    va="center",
                    fontsize=14,
                    fontweight="bold",
                    color="white" if cm[i, j] > cm.max() / 2 else "black",
                )
        apply_plot_theme(fig, ax)
        st.pyplot(fig, use_container_width=True)

    with r1[1]:
        st.markdown("**Metrics Breakdown**")
        st.dataframe(
            pd.DataFrame(
                {
                    "Metric": [
                        "Accuracy",
                        "TPR (Recall)",
                        "TNR",
                        "FPR",
                        "FNR",
                        "Precision",
                        "F1",
                        "Youden",
                    ],
                    "Value": [
                        f"{(m['tp'] + m['tn']) / (m['tp'] + m['tn'] + m['fp'] + m['fn']):.4f}",
                        f"{m['tpr']:.4f}",
                        f"{1 - m['fpr']:.4f}",
                        f"{m['fpr']:.4f}",
                        f"{1 - m['tpr']:.4f}",
                        f"{m['precision']:.4f}",
                        f"{m['f1']:.4f}",
                        f"{m['youden']:.4f}",
                    ],
                }
            ),
            use_container_width=True,
            hide_index=True,
        )

    st.divider()

    #  PR Curve
    pr = csv("pr_curve.csv")
    if not pr.empty:
        st.markdown("### Precision-Recall Curve")
        fig, ax = plt.subplots(figsize=(7, 4.5))
        ax.plot(pr["recall"], pr["precision"], color=C["blue"], lw=2)
        ax.fill_between(pr["recall"], pr["precision"], alpha=0.2, color=C["blue"])
        ax.set_xlabel("Recall")
        ax.set_ylabel("Precision")
        ax.set_title(f"PR Curve (Avg Precision = {m['avg_precision']:.4f})")
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.grid(alpha=0.3)
        apply_plot_theme(fig, ax)
        st.pyplot(fig, use_container_width=True)

    st.divider()

    #  Feature Importance (model)
    mfi = csv("model_feat_importance.csv")
    if not mfi.empty:
        st.markdown("### Feature Importance (Model)")
        n_mfi = st.slider("Show top N", 10, 100, 20, key="mfi_n")
        top_mfi = mfi.head(n_mfi)
        st.pyplot(
            barh(top_mfi["importance"], top_mfi["feature"], title=f"Top {n_mfi} Features (Model)"),
            use_container_width=True,
        )

    st.divider()

    #  Best params
    bp = META_DIR / "lightgbm_best_params.json"
    if bp.exists():
        with open(bp) as f:
            import json

            params = json.load(f)
        st.markdown("### LightGBM Best Params (from Tuning)")
        st.json(params)
