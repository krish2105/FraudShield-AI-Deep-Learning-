"""Fraud Risk Scoring page - upload a CSV (or use sample) and get scores."""

import io

import pandas as pd
import plotly.express as px
import streamlit as st

import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))  # make _components importable under st.navigation
from _components import (
    inject_css, page_header, mode_banner, section, kpi_card,
    config, business_rules,
)
from src.predict import score_transactions
from src.data_loader import load_data

inject_css()
page_header("Fraud Risk Scoring",
            "Score transactions and get a recommended business action")

st.markdown(
    "Upload a CSV of transactions with the PaySim columns, or score the "
    "built-in sample. Each transaction receives a **fraud probability**, a "
    "**risk band** and a **recommended action**."
)

# ---------------------------------------------------------------------------
# Input: upload or sample
# ---------------------------------------------------------------------------
uploaded = st.file_uploader("Upload transactions CSV", type=["csv"])

source_df = None
if uploaded is not None:
    try:
        source_df = pd.read_csv(uploaded)
        st.success(f"Loaded {len(source_df):,} rows from upload.")
    except Exception as exc:
        st.error(f"Could not read CSV: {exc}")
else:
    if st.button("▶ Score the built-in sample instead"):
        source_df, _ = load_data()
        source_df = source_df.head(2000)

if source_df is None:
    st.info("Waiting for a CSV upload — or click the button above to score the sample.")
    st.stop()

# ---------------------------------------------------------------------------
# Score
# ---------------------------------------------------------------------------
with st.spinner("Scoring..."):
    scored, mode = score_transactions(source_df)
mode_banner(mode, "real" if "real" else "sample")

# Risk band summary
low = int((scored["fraud_probability"] <= config.LOW_THRESHOLD).sum())
med = int(scored["fraud_probability"].between(
    config.LOW_THRESHOLD, config.HIGH_THRESHOLD, inclusive="right").sum())
high = int((scored["fraud_probability"] > config.HIGH_THRESHOLD).sum())

c1, c2, c3 = st.columns(3)
kpi_card(c1, "Low Risk → Approve", f"{low:,}", "score ≤ 0.30", "#16a34a")
kpi_card(c2, "Medium Risk → Review/OTP", f"{med:,}", "0.31 – 0.70", "#f59e0b")
kpi_card(c3, "High Risk → Block/Alert", f"{high:,}", "score ≥ 0.71", "#dc2626")

section("Scored Transactions")
show_cols = [c for c in ["step", "type", "amount", "nameOrig", "nameDest",
                         "fraud_probability", "risk_label", "recommended_action"]
             if c in scored.columns]
display = scored[show_cols].copy()
display["fraud_probability"] = (display["fraud_probability"] * 100).round(1)
display = display.rename(columns={"fraud_probability": "fraud_%"})
st.dataframe(display.sort_values("fraud_%", ascending=False),
             use_container_width=True, height=380)

# Distribution of scores
fig = px.histogram(scored, x="fraud_probability", nbins=40,
                   title="Distribution of Fraud Scores",
                   color_discrete_sequence=["#3b82f6"])
fig.add_vline(x=config.LOW_THRESHOLD, line_dash="dash", line_color="#16a34a")
fig.add_vline(x=config.HIGH_THRESHOLD, line_dash="dash", line_color="#dc2626")
fig.update_layout(height=300)
st.plotly_chart(fig, use_container_width=True)

# ---------------------------------------------------------------------------
# Download
# ---------------------------------------------------------------------------
section("Export Results")
csv_buf = io.StringIO()
scored.to_csv(csv_buf, index=False)
st.download_button("⬇ Download scored results (CSV)",
                   data=csv_buf.getvalue(),
                   file_name="fraud_scored_results.csv",
                   mime="text/csv")
