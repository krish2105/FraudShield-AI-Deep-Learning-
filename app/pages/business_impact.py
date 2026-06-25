"""Business Impact Simulator - translate detection into money saved."""

import plotly.graph_objects as go
import streamlit as st

import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))  # make _components importable under st.navigation
from _components import (
    inject_css, page_header, get_scored_data, mode_banner, section, kpi_card,
    config, format_currency,
)

inject_css()
page_header("Business Impact Simulator",
            "Estimate fraud loss prevented, review cost and net savings")

scored, mode, source = get_scored_data()
mode_banner(mode, source)

# Sensible defaults derived from the data.
n_high = int((scored["fraud_probability"] >= config.HIGH_THRESHOLD).sum())
n_medium = int(scored["fraud_probability"].between(
    config.LOW_THRESHOLD, config.HIGH_THRESHOLD).sum())

section("Your Assumptions")
c1, c2 = st.columns(2)
avg_loss = c1.number_input("Average fraud loss per case ($)",
                           min_value=0.0, value=config.DEFAULT_AVG_FRAUD_LOSS, step=100.0)
review_cost = c2.number_input("Manual review cost per case ($)",
                              min_value=0.0, value=config.DEFAULT_MANUAL_REVIEW_COST, step=1.0)
c3, c4 = st.columns(2)
caught = c3.number_input("Fraud cases caught (high-risk)",
                         min_value=0, value=n_high, step=1)
false_alerts = c4.slider("Estimated false-alert rate (%)", 0, 80, 25)

# ---------------------------------------------------------------------------
# Calculations
# ---------------------------------------------------------------------------
true_frauds = caught * (1 - false_alerts / 100.0)
loss_prevented = true_frauds * avg_loss
review_cases = caught + n_medium            # high + medium both get reviewed
total_review_cost = review_cases * review_cost
net_savings = loss_prevented - total_review_cost

section("Projected Impact")
k1, k2, k3, k4 = st.columns(4)
kpi_card(k1, "Fraud Loss Prevented", format_currency(loss_prevented),
         f"~{true_frauds:.0f} true frauds", "#16a34a")
kpi_card(k2, "Manual Review Cost", format_currency(total_review_cost),
         f"{review_cases:,} cases reviewed", "#f59e0b")
kpi_card(k3, "Net Savings", format_currency(net_savings),
         "prevented − review cost", "#2563eb")
workload = 100 * review_cases / max(len(scored), 1)
kpi_card(k4, "Review Workload", f"{workload:.1f}%",
         "of all transactions", "#8b5cf6")

# ---------------------------------------------------------------------------
# Waterfall chart
# ---------------------------------------------------------------------------
section("From Fraud Prevented to Net Savings")
fig = go.Figure(go.Waterfall(
    orientation="v",
    measure=["absolute", "relative", "total"],
    x=["Fraud loss prevented", "Manual review cost", "Net savings"],
    y=[loss_prevented, -total_review_cost, net_savings],
    connector={"line": {"color": "#94a3b8"}},
    increasing={"marker": {"color": "#16a34a"}},
    decreasing={"marker": {"color": "#dc2626"}},
    totals={"marker": {"color": "#2563eb"}},
))
fig.update_layout(height=380, title="Business Impact Waterfall")
st.plotly_chart(fig, use_container_width=True)

st.caption("These figures are illustrative and depend on your assumptions. "
           "Update the inputs with your bank's real numbers for a board-ready "
           "estimate.")
