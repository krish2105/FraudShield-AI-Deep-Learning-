"""Executive Overview page - the C-level snapshot of fraud risk."""

import pandas as pd
import plotly.express as px
import streamlit as st

import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))  # make _components importable under st.navigation
from _components import (
    inject_css, page_header, get_scored_data, mode_banner, kpi_card,
    section, business_rules, config, format_currency,
)

inject_css()
page_header("Executive Overview",
            "Portfolio-level view of payment fraud risk and exposure")

scored, mode, source = get_scored_data()
mode_banner(mode, source)

# ---------------------------------------------------------------------------
# KPI row
# ---------------------------------------------------------------------------
total_txn = len(scored)
fraud_txn = int(scored["isFraud"].sum()) if "isFraud" in scored else 0
fraud_pct = 100 * fraud_txn / total_txn if total_txn else 0
total_value = float(scored["amount"].sum()) if "amount" in scored else 0
amount_at_risk = business_rules.estimate_amount_at_risk(scored)
high_risk = int((scored["fraud_probability"] >= config.HIGH_THRESHOLD).sum())
high_risk_customers = (
    scored.loc[scored["fraud_probability"] >= config.HIGH_THRESHOLD, "nameOrig"].nunique()
    if "nameOrig" in scored else high_risk
)

c1, c2, c3, c4 = st.columns(4)
kpi_card(c1, "Total Transactions", f"{total_txn:,}", "in current view", "#3b82f6")
kpi_card(c2, "Flagged Fraud (label)", f"{fraud_txn:,}", f"{fraud_pct:.2f}% of volume", "#dc2626")
kpi_card(c3, "Total Transaction Value", format_currency(total_value), "processed", "#0ea5e9")
kpi_card(c4, "Estimated Amount at Risk", format_currency(amount_at_risk),
         "high-risk transactions", "#f59e0b")

c5, c6, c7, c8 = st.columns(4)
kpi_card(c5, "High-Risk Transactions", f"{high_risk:,}", "score ≥ 0.71", "#dc2626")
kpi_card(c6, "High-Risk Customers", f"{high_risk_customers:,}", "need review", "#f59e0b")
avg_score = scored["fraud_probability"].mean()
kpi_card(c7, "Avg Fraud Score", f"{avg_score:.1%}", "portfolio mean", "#3b82f6")
review_rate = 100 * (scored["fraud_probability"].between(
    config.LOW_THRESHOLD, config.HIGH_THRESHOLD)).mean()
kpi_card(c8, "Manual Review Rate", f"{review_rate:.1f}%", "medium-risk band", "#8b5cf6")

# ---------------------------------------------------------------------------
# Trends
# ---------------------------------------------------------------------------
section("Fraud & Volume Trends Over Time")
left, right = st.columns(2)

if "step" in scored.columns:
    by_step = scored.groupby("step").agg(
        transactions=("amount", "size"),
        fraud=("isFraud", "sum") if "isFraud" in scored else ("amount", "size"),
        high_risk=("fraud_probability", lambda s: int((s >= config.HIGH_THRESHOLD).sum())),
    ).reset_index()

    fig_fraud = px.area(by_step, x="step", y="high_risk",
                        title="High-Risk Transactions by Time Step",
                        color_discrete_sequence=["#dc2626"])
    fig_fraud.update_layout(height=320, margin=dict(t=50, b=10))
    left.plotly_chart(fig_fraud, use_container_width=True)

    fig_vol = px.line(by_step, x="step", y="transactions",
                      title="Transaction Volume by Time Step",
                      color_discrete_sequence=["#2563eb"])
    fig_vol.update_layout(height=320, margin=dict(t=50, b=10))
    right.plotly_chart(fig_vol, use_container_width=True)
else:
    st.info("No `step` column available to plot trends.")

# ---------------------------------------------------------------------------
# Top fraud transaction types
# ---------------------------------------------------------------------------
section("Top Fraud Transaction Types")
if "type" in scored.columns and "isFraud" in scored.columns:
    by_type = scored.groupby("type").agg(
        total=("amount", "size"),
        fraud=("isFraud", "sum"),
    ).reset_index()
    by_type["fraud_rate_%"] = (100 * by_type["fraud"] / by_type["total"]).round(2)
    by_type = by_type.sort_values("fraud", ascending=False)

    a, b = st.columns([2, 1])
    fig_type = px.bar(by_type, x="type", y="fraud", color="fraud",
                      title="Fraud Count by Transaction Type",
                      color_continuous_scale="Reds", text="fraud")
    fig_type.update_layout(height=340, margin=dict(t=50, b=10))
    a.plotly_chart(fig_type, use_container_width=True)
    b.dataframe(by_type, use_container_width=True, hide_index=True)
else:
    st.info("Transaction `type` / `isFraud` columns not available.")

st.caption("FraudShield AI · scores blend sequence behaviour into a single "
           "risk number that maps directly to a business action.")
