"""Recommendations - business guidance, limitations, ethics, future scope."""

import streamlit as st

import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))  # make _components importable under st.navigation
from _components import inject_css, page_header, section

inject_css()
page_header("Recommendations",
            "Business guidance, limitations, ethics and the road ahead")

section("Business Recommendations")
st.markdown(
    """
- **Deploy fraud scoring before payment approval**, not after — block losses
  before money leaves the account.
- **Use the three-band action policy**: auto-approve low risk, OTP / manual
  review for medium risk, block + escalate for high risk.
- **Prioritise the fraud team's time** on the high-risk queue in the Alert
  Center instead of reviewing everything.
- **Tune the threshold to the bank's risk appetite** — lower it to catch more
  fraud (higher recall), raise it to reduce false alarms.
- **Monitor model drift** monthly; fraud patterns change, so retrain regularly.
"""
)

section("Limitations")
st.markdown(
    """
- The demo runs on **synthetic PaySim-style data**; real bank data is private
  and behaves differently.
- **Fraud patterns evolve** — a model trained today will decay over time.
- **False positives** inconvenience genuine customers and must be minimised.
- The sample dataset is **small and balanced for demonstration**, not a true
  reflection of real-world class imbalance.
"""
)

section("Ethics & Responsible Use")
st.markdown(
    """
- **Human-in-the-loop**: the model *recommends*, a human *decides* on
  borderline and high-impact cases.
- **Data privacy**: customer transaction data is sensitive and must be
  protected and access-controlled.
- **Fairness**: monitor that the model does not unfairly target particular
  customer groups.
- **Transparency**: every alert ships with a plain-language reason
  (see the Explainability Panel).
"""
)

section("Future Scope")
st.markdown(
    """
- ⚡ **Real-time fraud API** scoring each payment in milliseconds.
- 🔐 **OTP / SMS step-up** verification for medium-risk transactions.
- 🔁 **Analyst feedback loop** so confirmed outcomes retrain the model.
- 🧠 **Explainable AI (SHAP)** for richer per-feature attributions.
- ☁️ **Cloud deployment** with automatic, scheduled model retraining.
"""
)

st.info("FraudShield AI is a decision-support tool. The goal is to make the "
        "fraud team faster and the customer safer — never to replace human "
        "judgement on high-impact decisions.")
