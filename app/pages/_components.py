"""
_components.py  (NOT a dashboard page - shared helpers)
======================================================
Reusable Streamlit helpers shared by every page of FraudShield AI:
project-path bootstrap, CSS injection, cached data loading + scoring,
KPI cards and risk badges.

Files starting with "_" are ignored by Streamlit's page auto-detection,
so this never appears as a navigation entry.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

# --- Make the project root importable (so `from src...` always works) -------
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src import config                      # noqa: E402
from src import business_rules              # noqa: E402
from src.data_loader import load_data, basic_overview   # noqa: E402
from src.predict import score_transactions, model_available  # noqa: E402
from src.utils import read_json, format_currency          # noqa: E402

ASSETS_DIR = PROJECT_ROOT / "app" / "assets"


# ---------------------------------------------------------------------------
# Styling
# ---------------------------------------------------------------------------
def inject_css() -> None:
    """Load the shared stylesheet once per page."""
    css_path = ASSETS_DIR / "style.css"
    if css_path.exists():
        st.markdown(f"<style>{css_path.read_text()}</style>",
                    unsafe_allow_html=True)


def page_header(title: str, subtitle: str = "") -> None:
    """Render a consistent page title block."""
    st.markdown(
        f"""
        <div class="fs-header">
            <div class="fs-header-title">{title}</div>
            <div class="fs-header-sub">{subtitle}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Cached data + scoring (shared across pages, computed once)
# ---------------------------------------------------------------------------
@st.cache_data(show_spinner=False)
def get_raw_data():
    """Load the dataset once and cache it. Returns (df, source)."""
    df, source = load_data()
    return df, source


@st.cache_data(show_spinner="Scoring transactions...")
def get_scored_data(max_rows: int = 20000):
    """Load + score the data (cached). Returns (scored_df, mode, source).

    `max_rows` keeps the dashboard responsive on the full PaySim file.
    """
    df, source = load_data()
    if len(df) > max_rows:
        df = df.sample(max_rows, random_state=config.RANDOM_SEED).reset_index(drop=True)
    scored, mode = score_transactions(df)
    return scored, mode, source


def get_metrics() -> dict:
    """Read reports/metrics.json (or an empty dict if absent)."""
    return read_json(config.METRICS_PATH, default={}) or {}


def get_model_comparison() -> pd.DataFrame | None:
    """Read reports/model_comparison.csv if it exists."""
    if config.MODEL_COMPARISON_PATH.exists():
        try:
            return pd.read_csv(config.MODEL_COMPARISON_PATH)
        except Exception:
            return None
    return None


# ---------------------------------------------------------------------------
# Mode / data banners
# ---------------------------------------------------------------------------
def mode_banner(mode: str, source: str) -> None:
    """Show whether we are running on real/sample data and model/demo mode."""
    if mode == "demo":
        st.warning(
            "⚠️ **Trained model not found. Running in demo mode.** "
            "Fraud scores below come from transparent business rules, not a "
            "trained LSTM. Train the model in the notebook for real scores.",
            icon="⚠️",
        )
    if source != "real":
        st.info(
            "ℹ️ Using **synthetic sample data** (demo only). Add the real "
            "PaySim file at `data/paysim.csv` for genuine results.",
            icon="ℹ️",
        )


# ---------------------------------------------------------------------------
# Small UI atoms
# ---------------------------------------------------------------------------
def kpi_card(col, label: str, value: str, sub: str = "", accent: str = "#3b82f6"):
    """Render a KPI card inside a given Streamlit column."""
    col.markdown(
        f"""
        <div class="fs-kpi" style="border-left:4px solid {accent};">
            <div class="fs-kpi-label">{label}</div>
            <div class="fs-kpi-value">{value}</div>
            <div class="fs-kpi-sub">{sub}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def risk_badge_html(probability: float) -> str:
    """Return an HTML pill for a fraud probability."""
    band = business_rules.risk_band(probability)
    return (
        f"<span class='fs-badge' style='background:{band['color']};'>"
        f"{band['label']} · {probability:.0%}</span>"
    )


def section(title: str) -> None:
    """A simple styled section divider."""
    st.markdown(f"<div class='fs-section'>{title}</div>", unsafe_allow_html=True)
