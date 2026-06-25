"""Model Performance - metrics from reports/, with honest placeholders."""

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))  # make _components importable under st.navigation
from _components import (
    inject_css, page_header, get_metrics, get_model_comparison, section,
)

inject_css()
page_header("Model Performance",
            "Evaluation metrics for the LSTM and the Dense baseline")

metrics = get_metrics()
not_trained = (not metrics) or metrics.get("status") == "NOT_TRAINED"

if not_trained:
    st.warning(
        "⚠️ **No trained-model metrics found yet.** The numbers below are "
        "placeholders. Run `notebooks/Payment_Fraud_LSTM_Complete.ipynb` to "
        "train the models — it overwrites `reports/metrics.json` with real "
        "values. After training on the **real PaySim dataset**, these become "
        "final.",
        icon="⚠️",
    )

# ---------------------------------------------------------------------------
# Metric explanations (always shown — educational)
# ---------------------------------------------------------------------------
section("What the Metrics Mean")
st.markdown(
    """
| Metric | Plain meaning | Why it matters for fraud |
|--------|---------------|--------------------------|
| **Accuracy** | % of all predictions correct | Misleading when fraud is rare |
| **Precision** | Of flagged frauds, how many were real | High precision = fewer false alarms |
| **Recall** | Of real frauds, how many we caught | **Most important** — missing fraud is costly |
| **F1-score** | Balance of precision & recall | Good single summary |
| **ROC-AUC** | Ranking quality across thresholds | 1.0 = perfect, 0.5 = random |
| **PR-AUC** | Precision/recall on the rare class | Best for imbalanced fraud data |
"""
)
st.info("👉 We optimise for **recall**: catching a real fraud matters more than "
        "occasionally reviewing a genuine transaction.")

# ---------------------------------------------------------------------------
# Metric cards
# ---------------------------------------------------------------------------
section("LSTM Metrics")
lstm = metrics.get("lstm", {}) if isinstance(metrics, dict) else {}


def _fmt(v):
    if isinstance(v, (int, float)):
        return f"{v:.3f}"
    return "—" if not_trained else str(v)


cols = st.columns(6)
for col, key in zip(cols, ["accuracy", "precision", "recall", "f1", "roc_auc", "pr_auc"]):
    col.metric(key.upper().replace("_", "-"), _fmt(lstm.get(key)))

# ---------------------------------------------------------------------------
# Confusion matrix (real or placeholder)
# ---------------------------------------------------------------------------
section("Confusion Matrix")
cm = lstm.get("confusion_matrix") if isinstance(lstm, dict) else None
if cm:
    cm_df = pd.DataFrame(cm, index=["Actual: Genuine", "Actual: Fraud"],
                         columns=["Pred: Genuine", "Pred: Fraud"])
    fig = px.imshow(cm_df, text_auto=True, color_continuous_scale="Blues",
                    title="Confusion Matrix (LSTM)")
    st.plotly_chart(fig, use_container_width=True)
else:
    st.caption("Placeholder — confusion matrix appears here after training.")
    placeholder = pd.DataFrame([["TN", "FP"], ["FN", "TP"]],
                               index=["Actual: Genuine", "Actual: Fraud"],
                               columns=["Pred: Genuine", "Pred: Fraud"])
    st.table(placeholder)

# ---------------------------------------------------------------------------
# Model comparison table
# ---------------------------------------------------------------------------
section("Model Comparison")
comp = get_model_comparison()
if comp is not None:
    st.dataframe(comp, use_container_width=True, hide_index=True)
else:
    st.caption("`reports/model_comparison.csv` not found.")
