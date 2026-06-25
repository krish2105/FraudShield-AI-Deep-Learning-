"""Alert Center - the operations queue of high-risk transactions."""

import io

import streamlit as st

import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))  # make _components importable under st.navigation
from _components import (
    inject_css, page_header, get_scored_data, mode_banner, section, kpi_card,
    config, format_currency,
)

inject_css()
page_header("Alert Center",
            "Operational queue of high-risk transactions for the fraud team")

scored, mode, source = get_scored_data()
mode_banner(mode, source)

# ---------------------------------------------------------------------------
# Threshold control
# ---------------------------------------------------------------------------
thr = st.slider("Alert threshold (fraud probability)", 0.30, 0.95,
                float(config.HIGH_THRESHOLD), 0.01)
alerts = scored[scored["fraud_probability"] >= thr].copy()
alerts = alerts.sort_values("fraud_probability", ascending=False)

c1, c2, c3 = st.columns(3)
kpi_card(c1, "Open Alerts", f"{len(alerts):,}", f"score ≥ {thr:.2f}", "#dc2626")
kpi_card(c2, "Amount in Alerts", format_currency(alerts["amount"].sum()),
         "total exposure", "#f59e0b")
kpi_card(c3, "Customers Involved",
         f"{alerts['nameOrig'].nunique():,}" if "nameOrig" in alerts else "—",
         "unique senders", "#3b82f6")

# ---------------------------------------------------------------------------
# Alert table
# ---------------------------------------------------------------------------
section("High-Risk Alert Queue")
alerts = alerts.reset_index(drop=True)
alerts["status"] = "OPEN"
cols = [c for c in ["nameOrig", "type", "amount", "fraud_probability",
                    "risk_label", "recommended_action", "status"]
        if c in alerts.columns]
view = alerts[cols].copy()
view["fraud_probability"] = (view["fraud_probability"] * 100).round(1)
view = view.rename(columns={"fraud_probability": "fraud_%",
                            "nameOrig": "customer_id"})
st.dataframe(view, use_container_width=True, height=420, hide_index=True)

# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------
section("Export Alert Report")
buf = io.StringIO()
alerts[cols].to_csv(buf, index=False)
st.download_button("⬇ Download alert report (CSV)",
                   data=buf.getvalue(),
                   file_name="fraudshield_alert_report.csv",
                   mime="text/csv")

st.caption("Each alert maps to a recommended action: Block / Alert Fraud Team "
           "for high risk, Manual Review / OTP for medium risk.")
