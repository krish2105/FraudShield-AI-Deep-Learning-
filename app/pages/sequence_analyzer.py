"""Customer Sequence Analyzer - inspect one customer's transaction history."""

import plotly.graph_objects as go
import streamlit as st

import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))  # make _components importable under st.navigation
from _components import (
    inject_css, page_header, get_scored_data, mode_banner, section,
    risk_badge_html, config,
)

inject_css()
page_header("Customer Sequence Analyzer",
            "How the LSTM reads a customer's recent behaviour as a sequence")

scored, mode, source = get_scored_data()
mode_banner(mode, source)

if "nameOrig" not in scored.columns:
    st.error("No `nameOrig` column to analyze customer sequences.")
    st.stop()

# ---------------------------------------------------------------------------
# Pick a customer (default to a high-risk one to make the demo interesting)
# ---------------------------------------------------------------------------
high_risk_customers = (
    scored.loc[scored["fraud_probability"] >= config.HIGH_THRESHOLD, "nameOrig"]
    .value_counts().index.tolist()
)
all_customers = scored["nameOrig"].value_counts().index.tolist()
default_list = high_risk_customers or all_customers

cust = st.selectbox(
    "🔎 Search / select a customer ID",
    options=all_customers,
    index=all_customers.index(default_list[0]) if default_list else 0,
)

cust_df = scored[scored["nameOrig"] == cust].copy()
if "step" in cust_df.columns:
    cust_df = cust_df.sort_values("step")
last10 = cust_df.tail(config.SEQUENCE_LENGTH + 1)

# ---------------------------------------------------------------------------
# Summary badges
# ---------------------------------------------------------------------------
max_p = float(cust_df["fraud_probability"].max())
c1, c2, c3 = st.columns(3)
c1.metric("Transactions", len(cust_df))
c2.metric("Max fraud score", f"{max_p:.0%}")
c3.markdown("**Current risk**<br>" + risk_badge_html(max_p), unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Last 10 transactions table
# ---------------------------------------------------------------------------
section(f"Last {len(last10)} Transactions — {cust}")
cols = [c for c in ["step", "type", "amount", "oldbalanceOrg", "newbalanceOrig",
                    "fraud_probability", "risk_label", "recommended_action"]
        if c in last10.columns]
tbl = last10[cols].copy()
tbl["fraud_probability"] = (tbl["fraud_probability"] * 100).round(1)
tbl = tbl.rename(columns={"fraud_probability": "fraud_%"})
st.dataframe(tbl, use_container_width=True, hide_index=True)

# ---------------------------------------------------------------------------
# Timeline chart: amount + balance before/after
# ---------------------------------------------------------------------------
section("Behaviour Timeline")
x = list(range(1, len(last10) + 1))
fig = go.Figure()
fig.add_trace(go.Bar(x=x, y=last10["amount"], name="Amount",
                     marker_color="#3b82f6"))
if "oldbalanceOrg" in last10:
    fig.add_trace(go.Scatter(x=x, y=last10["oldbalanceOrg"], name="Balance before",
                             mode="lines+markers", line=dict(color="#0ea5e9")))
if "newbalanceOrig" in last10:
    fig.add_trace(go.Scatter(x=x, y=last10["newbalanceOrig"], name="Balance after",
                             mode="lines+markers", line=dict(color="#dc2626")))
fig.update_layout(height=380, title=f"Transaction amounts & balance for {cust}",
                  xaxis_title="Transaction # in sequence", legend=dict(orientation="h"))
st.plotly_chart(fig, use_container_width=True)

# ---------------------------------------------------------------------------
# Plain-language explanation
# ---------------------------------------------------------------------------
section("Why the Sequence Matters")
drained = ((last10["oldbalanceOrg"] > 0) & (last10["newbalanceOrig"] <= 1)).any() \
    if "newbalanceOrig" in last10 else False
big_jump = last10["amount"].max() > 5 * (last10["amount"].median() + 1)

notes = []
if big_jump:
    notes.append("📈 There is a **sudden large jump** in transaction amount "
                 "compared to this customer's normal behaviour.")
if drained:
    notes.append("🩸 At least one transaction **drains the sender's balance to "
                 "near zero** — a classic fraud signal.")
if max_p >= config.HIGH_THRESHOLD:
    notes.append("🚨 The most recent behaviour scores **High Risk** and would "
                 "be blocked / sent to the fraud team.")
if not notes:
    notes.append("✅ This customer's behaviour looks **stable and consistent** — "
                 "small, regular amounts with healthy balances.")

for n in notes:
    st.markdown(f"- {n}")

st.info(
    "**How the LSTM uses sequence memory:** a normal model looks at one "
    "transaction alone. The LSTM instead reads the last "
    f"{config.SEQUENCE_LENGTH} transactions **in order** and remembers the "
    "pattern. So a payment of 9,000 looks fine on its own, but right after a "
    "history of 100 → 120 → 90 it stands out as suspicious."
)
