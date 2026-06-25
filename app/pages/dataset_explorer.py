"""Dataset Explorer page - understand the raw data before modelling."""

import pandas as pd
import plotly.express as px
import streamlit as st

import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))  # make _components importable under st.navigation
from _components import (
    inject_css, page_header, get_raw_data, mode_banner, section,
)
from src.data_loader import basic_overview

inject_css()
page_header("Dataset Explorer",
            "Preview, quality checks and distributions of the transaction data")

df, source = get_raw_data()
mode_banner("model", source)  # only data-source note here

ov = basic_overview(df)
c1, c2, c3, c4 = st.columns(4)
c1.metric("Rows", f"{ov['rows']:,}")
c2.metric("Columns", ov["n_columns"])
c3.metric("Missing values", ov["null_values"])
c4.metric("Duplicate rows", ov["duplicate_rows"])

# ---------------------------------------------------------------------------
# Filters
# ---------------------------------------------------------------------------
section("Filters")
fc1, fc2 = st.columns(2)
types = sorted(df["type"].unique()) if "type" in df else []
sel_types = fc1.multiselect("Transaction type", types, default=types)
fraud_choice = fc2.selectbox("Fraud label", ["All", "Fraud only", "Non-fraud only"])

view = df.copy()
if sel_types:
    view = view[view["type"].isin(sel_types)]
if fraud_choice == "Fraud only" and "isFraud" in view:
    view = view[view["isFraud"] == 1]
elif fraud_choice == "Non-fraud only" and "isFraud" in view:
    view = view[view["isFraud"] == 0]

section("Data Preview")
st.dataframe(view.head(200), use_container_width=True, height=300)
st.caption(f"Showing first 200 of {len(view):,} filtered rows.")

# ---------------------------------------------------------------------------
# Column descriptions
# ---------------------------------------------------------------------------
section("Column Descriptions")
desc = pd.DataFrame([
    ("step", "Time step (1 = 1 hour of simulation)"),
    ("type", "PAYMENT, TRANSFER, CASH_OUT, DEBIT, CASH_IN"),
    ("amount", "Transaction amount"),
    ("nameOrig", "Sender (origin) customer ID"),
    ("oldbalanceOrg", "Sender balance before the transaction"),
    ("newbalanceOrig", "Sender balance after the transaction"),
    ("nameDest", "Receiver (destination) ID"),
    ("oldbalanceDest", "Receiver balance before"),
    ("newbalanceDest", "Receiver balance after"),
    ("isFraud", "1 = fraud, 0 = genuine (the label)"),
    ("isFlaggedFraud", "1 = flagged by a naive business rule"),
], columns=["Column", "Description"])
st.dataframe(desc, use_container_width=True, hide_index=True)

# ---------------------------------------------------------------------------
# Missing values per column
# ---------------------------------------------------------------------------
section("Missing Values by Column")
miss = df.isnull().sum().reset_index()
miss.columns = ["column", "missing"]
st.dataframe(miss, use_container_width=True, hide_index=True)

# ---------------------------------------------------------------------------
# Distributions
# ---------------------------------------------------------------------------
section("Distributions")
g1, g2 = st.columns(2)

if "isFraud" in view.columns:
    fraud_dist = view["isFraud"].map({0: "Genuine", 1: "Fraud"}).value_counts().reset_index()
    fraud_dist.columns = ["label", "count"]
    fig1 = px.pie(fraud_dist, names="label", values="count", hole=0.5,
                  title="Fraud vs Genuine",
                  color="label",
                  color_discrete_map={"Genuine": "#2563eb", "Fraud": "#dc2626"})
    fig1.update_layout(height=330)
    g1.plotly_chart(fig1, use_container_width=True)

if "type" in view.columns:
    type_dist = view["type"].value_counts().reset_index()
    type_dist.columns = ["type", "count"]
    fig2 = px.bar(type_dist, x="type", y="count", title="Transaction Type Distribution",
                  color="count", color_continuous_scale="Blues")
    fig2.update_layout(height=330)
    g2.plotly_chart(fig2, use_container_width=True)

if "amount" in view.columns and len(view):
    section("Amount Distribution")
    capped = view[view["amount"] <= view["amount"].quantile(0.99)]
    fig3 = px.histogram(capped, x="amount", nbins=50,
                        title="Amount Distribution (99th percentile capped)",
                        color_discrete_sequence=["#3b82f6"])
    fig3.update_layout(height=330)
    st.plotly_chart(fig3, use_container_width=True)
