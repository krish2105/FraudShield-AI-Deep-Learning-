"""
streamlit_app.py
================
Entry point for the FraudShield AI dashboard.

Run with:
    streamlit run app/streamlit_app.py

Uses st.navigation / st.Page to give a clean, explicitly-ordered sidebar.
Each page lives in app/pages/ and runs as its own script, sharing helpers
from app/pages/_components.py.

The dashboard ALWAYS runs:
  * If data/paysim.csv is missing -> it uses the synthetic sample data.
  * If the trained model is missing -> it scores with transparent demo rules
    and shows a "Running in demo mode" warning.
"""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

# Make the project root importable.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
PAGES_DIR = PROJECT_ROOT / "app" / "pages"

# Put both the project root (for `import src...`) and the pages folder (for
# `import _components` inside each page) on the path. st.navigation runs the
# page scripts in this same process, so these additions persist into them.
for _p in (str(PROJECT_ROOT), str(PAGES_DIR)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# ---------------------------------------------------------------------------
# Global page configuration (must be the first Streamlit call).
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="FraudShield AI",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)


def _sidebar_brand() -> None:
    """Render the FraudShield brand block at the top of the sidebar."""
    st.sidebar.markdown(
        """
        <div class="fs-brand">🛡️ FraudShield AI</div>
        <div class="fs-brand-sub">Payment Fraud Sequence Detection</div>
        <hr style="border-color:#1e3a5f;">
        """,
        unsafe_allow_html=True,
    )


# Inject CSS as early as possible so the brand block is styled.
_css = PROJECT_ROOT / "app" / "assets" / "style.css"
if _css.exists():
    st.markdown(f"<style>{_css.read_text()}</style>", unsafe_allow_html=True)

_sidebar_brand()

# ---------------------------------------------------------------------------
# Define the navigation. Order + titles + icons are controlled here, so the
# sidebar reads like a product, not a folder listing.
# ---------------------------------------------------------------------------
pages = [
    st.Page(str(PAGES_DIR / "executive_overview.py"),
            title="Executive Overview", icon="📊", default=True),
    st.Page(str(PAGES_DIR / "dataset_explorer.py"),
            title="Dataset Explorer", icon="🗂️"),
    st.Page(str(PAGES_DIR / "fraud_prediction.py"),
            title="Fraud Risk Scoring", icon="🎯"),
    st.Page(str(PAGES_DIR / "sequence_analyzer.py"),
            title="Customer Sequence Analyzer", icon="🔗"),
    st.Page(str(PAGES_DIR / "fraud_insights.py"),
            title="Fraud Pattern Insights", icon="🔍"),
    st.Page(str(PAGES_DIR / "model_performance.py"),
            title="Model Performance", icon="📈"),
    st.Page(str(PAGES_DIR / "explainability.py"),
            title="Explainability Panel", icon="💡"),
    st.Page(str(PAGES_DIR / "alert_center.py"),
            title="Alert Center", icon="🚨"),
    st.Page(str(PAGES_DIR / "business_impact.py"),
            title="Business Impact Simulator", icon="💰"),
    st.Page(str(PAGES_DIR / "recommendations.py"),
            title="Recommendations", icon="✅"),
]

nav = st.navigation(pages, position="sidebar")

st.sidebar.markdown(
    "<hr style='border-color:#1e3a5f;'>"
    "<div style='font-size:11px;color:#93c5fd;'>MAIB Sept 25 · Term 3<br>"
    "Deep Learning Project</div>",
    unsafe_allow_html=True,
)

nav.run()
