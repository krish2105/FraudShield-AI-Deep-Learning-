"""Explainability Panel - business-friendly reasons behind a fraud score."""

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))  # make _components importable under st.navigation
from _components import (
    inject_css, page_header, get_scored_data, mode_banner, section,
    risk_badge_html, config,
)
from src.feature_engineering import engineer_features

inject_css()
page_header("Explainability Panel",
            "Plain-English reasons a transaction is risky (no black box)")

scored, mode, source = get_scored_data()
mode_banner(mode, source)

# ---------------------------------------------------------------------------
# Approximate feature importance (correlation of features with the score)
# ---------------------------------------------------------------------------
section("Which Signals Drive Risk? (approximate importance)")
st.caption("SHAP-style values need the trained model. As a transparent "
           "approximation we show how strongly each engineered feature moves "
           "together with the fraud score.")

feat = engineer_features(scored)
imp_rows = []
for col in config.FEATURE_COLUMNS:
    try:
        corr = np.corrcoef(feat[col].astype(float), scored["fraud_probability"])[0, 1]
        imp_rows.append((col, abs(corr) if not np.isnan(corr) else 0.0))
    except Exception:
        imp_rows.append((col, 0.0))
imp = pd.DataFrame(imp_rows, columns=["feature", "importance"]).sort_values("importance")

fig = px.bar(imp, x="importance", y="feature", orientation="h",
             color="importance", color_continuous_scale="Blues",
             title="Approximate Feature Importance (|correlation| with risk)")
fig.update_layout(height=420)
st.plotly_chart(fig, use_container_width=True)

# ---------------------------------------------------------------------------
# Per-transaction explanation
# ---------------------------------------------------------------------------
section("Explain a Single Transaction")
high = scored.sort_values("fraud_probability", ascending=False).head(200).reset_index()
idx = st.selectbox(
    "Pick a transaction (sorted by risk)",
    options=high.index,
    format_func=lambda i: (f"{high.loc[i, 'type']} · "
                           f"{high.loc[i, 'amount']:,.0f} · "
                           f"score {high.loc[i, 'fraud_probability']:.0%}"),
)
row = high.loc[idx]
st.markdown("**Risk:** " + risk_badge_html(row["fraud_probability"]),
            unsafe_allow_html=True)

# Build human-readable reasons from the raw columns.
reasons = []
amount = row.get("amount", 0)
old_org = row.get("oldbalanceOrg", 0)
new_org = row.get("newbalanceOrig", 0)
ratio = amount / old_org if old_org else 0

if old_org > 0 and new_org <= 1:
    reasons.append("the **sender's balance becomes zero** after the transaction")
if ratio >= 0.9:
    reasons.append(f"the amount is **{ratio:.0%} of the old balance** (near-total sweep)")
if amount >= config.HIGH_AMOUNT_THRESHOLD:
    reasons.append(f"the amount (**{amount:,.0f}**) is unusually large")
if str(row.get("type")) in ("TRANSFER", "CASH_OUT"):
    reasons.append(f"it is a **{row.get('type')}**, the type most used for fraud")

if reasons:
    st.markdown("**This transaction is "
                f"{row['risk_label'].lower()} because:**")
    for r in reasons:
        st.markdown(f"- {r}")
else:
    st.markdown("This transaction shows **no strong fraud signals** — small "
                "amount relative to balance, healthy remaining balance.")

st.success(
    "Example explanation: *“This transaction is high risk because the amount "
    "is large compared to the old balance and the sender balance becomes "
    "zero.”* Human-readable reasons keep an analyst in control of the decision."
)
