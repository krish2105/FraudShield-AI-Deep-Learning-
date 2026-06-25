"""Fraud Pattern Insights - where and how fraud concentrates."""

import pandas as pd
import plotly.express as px
import streamlit as st

import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))  # make _components importable under st.navigation
from _components import (
    inject_css, page_header, get_scored_data, mode_banner, section, config,
)

inject_css()
page_header("Fraud Pattern Insights",
            "Where fraud concentrates: type, amount, time and balance behaviour")

scored, mode, source = get_scored_data()
mode_banner(mode, source)

# Use the model risk flag as the "fraud-like" signal for charts.
scored = scored.copy()
scored["high_risk"] = (scored["fraud_probability"] >= config.HIGH_THRESHOLD).astype(int)

# ---------------------------------------------------------------------------
# Fraud by transaction type
# ---------------------------------------------------------------------------
section("High-Risk by Transaction Type")
if "type" in scored.columns:
    by_type = scored.groupby("type").agg(
        total=("amount", "size"),
        high_risk=("high_risk", "sum"),
    ).reset_index()
    by_type["high_risk_rate_%"] = (100 * by_type["high_risk"] / by_type["total"]).round(2)
    fig = px.bar(by_type, x="type", y="high_risk_rate_%", color="high_risk_rate_%",
                 color_continuous_scale="Reds", text="high_risk_rate_%",
                 title="High-Risk Rate by Transaction Type (%)")
    fig.update_layout(height=340)
    st.plotly_chart(fig, use_container_width=True)

# ---------------------------------------------------------------------------
# Fraud by amount range
# ---------------------------------------------------------------------------
section("High-Risk by Amount Range")
bins = [0, 1000, 10000, 50000, 200000, float("inf")]
labels = ["0–1K", "1K–10K", "10K–50K", "50K–200K", "200K+"]
scored["amount_band"] = pd.cut(scored["amount"], bins=bins, labels=labels)
by_amt = scored.groupby("amount_band", observed=True).agg(
    total=("amount", "size"),
    high_risk=("high_risk", "sum"),
).reset_index()
by_amt["high_risk_rate_%"] = (100 * by_amt["high_risk"] / by_amt["total"]).round(2)
fig2 = px.bar(by_amt, x="amount_band", y="high_risk_rate_%",
              color="high_risk_rate_%", color_continuous_scale="Oranges",
              text="high_risk_rate_%", title="High-Risk Rate by Amount Band (%)")
fig2.update_layout(height=320)
st.plotly_chart(fig2, use_container_width=True)

# ---------------------------------------------------------------------------
# Fraud by time step
# ---------------------------------------------------------------------------
if "step" in scored.columns:
    section("High-Risk by Time Step")
    by_step = scored.groupby("step")["high_risk"].sum().reset_index()
    fig3 = px.line(by_step, x="step", y="high_risk",
                   title="High-Risk Transactions Over Time",
                   color_discrete_sequence=["#dc2626"])
    fig3.update_layout(height=300)
    st.plotly_chart(fig3, use_container_width=True)

# ---------------------------------------------------------------------------
# Balance-draining transactions
# ---------------------------------------------------------------------------
section("Balance-Draining Transactions")
if {"oldbalanceOrg", "newbalanceOrig"}.issubset(scored.columns):
    drained = scored[(scored["oldbalanceOrg"] > 0) & (scored["newbalanceOrig"] <= 1)]
    st.metric("Transactions that drained the sender to ~0", f"{len(drained):,}")
    cols = [c for c in ["nameOrig", "type", "amount", "oldbalanceOrg",
                        "newbalanceOrig", "fraud_probability", "risk_label"]
            if c in drained.columns]
    st.dataframe(drained[cols].sort_values("amount", ascending=False).head(50),
                 use_container_width=True, hide_index=True)

# ---------------------------------------------------------------------------
# High-risk customers
# ---------------------------------------------------------------------------
section("Top High-Risk Customers")
if "nameOrig" in scored.columns:
    top_cust = (scored.groupby("nameOrig")
                .agg(max_score=("fraud_probability", "max"),
                     txns=("amount", "size"),
                     total_amount=("amount", "sum"))
                .reset_index()
                .sort_values("max_score", ascending=False)
                .head(25))
    top_cust["max_score"] = (top_cust["max_score"] * 100).round(1)
    st.dataframe(top_cust.rename(columns={"max_score": "max_fraud_%"}),
                 use_container_width=True, hide_index=True)
