"""
feature_engineering.py
======================
Builds the model input features from the raw PaySim columns.

Engineered features (explained in simple language):
    origin_balance_change        : how much the sender's balance dropped
    destination_balance_change   : how much the receiver's balance rose
    amount_to_balance_ratio      : how big the payment is vs the old balance
    zero_balance_flag            : did the sender's balance go to zero?
    high_amount_flag             : is this an unusually large amount?
    transaction_count_by_customer: how active is this customer?
    type_encoded                 : transaction type turned into a number
"""

from __future__ import annotations

import numpy as np
import pandas as pd

try:
    from . import config
except ImportError:  # pragma: no cover
    import sys
    from pathlib import Path

    sys.path.append(str(Path(__file__).resolve().parents[1]))
    from src import config


# A fixed mapping so the encoding is identical in training and inference.
TYPE_MAP = {t: i for i, t in enumerate(config.TRANSACTION_TYPES)}


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add the engineered feature columns to a copy of `df` and return it."""
    out = df.copy()

    # Make sure numeric columns are numeric (defensive against bad CSVs).
    for col in ["amount", "oldbalanceOrg", "newbalanceOrig",
                "oldbalanceDest", "newbalanceDest"]:
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce").fillna(0.0)

    # 1. Balance changes.
    out["origin_balance_change"] = out["oldbalanceOrg"] - out["newbalanceOrig"]
    out["destination_balance_change"] = (
        out["newbalanceDest"] - out["oldbalanceDest"]
    )

    # 1b. Balance-consistency errors (very strong PaySim fraud signals).
    # For a legitimate debit:  newbalanceOrig = oldbalanceOrg - amount, so the
    # error is ~0. Fraud often breaks this identity (e.g. destination balance
    # never updates), leaving a non-zero error.
    out["errorBalanceOrig"] = (
        out["newbalanceOrig"] + out["amount"] - out["oldbalanceOrg"]
    )
    out["errorBalanceDest"] = (
        out["oldbalanceDest"] + out["amount"] - out["newbalanceDest"]
    )

    # 2. Amount relative to the sender's balance (guard divide-by-zero).
    out["amount_to_balance_ratio"] = np.where(
        out["oldbalanceOrg"] > 0,
        out["amount"] / out["oldbalanceOrg"],
        0.0,
    )

    # 3. Did the sender's account drain to (near) zero?
    out["zero_balance_flag"] = (
        (out["oldbalanceOrg"] > 0) & (out["newbalanceOrig"] <= 1)
    ).astype(int)

    # 4. Is this an unusually large amount?
    out["high_amount_flag"] = (
        out["amount"] >= config.HIGH_AMOUNT_THRESHOLD
    ).astype(int)

    # 5. How many transactions does this customer have? (activity signal)
    if "nameOrig" in out.columns:
        counts = out.groupby("nameOrig")["amount"].transform("count")
        out["transaction_count_by_customer"] = counts.astype(int)
    else:
        out["transaction_count_by_customer"] = 1

    # 6. Encode the transaction type as a number.
    if "type" in out.columns:
        out["type_encoded"] = out["type"].map(TYPE_MAP).fillna(-1).astype(int)
    else:
        out["type_encoded"] = -1

    # Clean any inf / nan produced by the arithmetic above.
    out = out.replace([np.inf, -np.inf], 0.0)
    out[config.FEATURE_COLUMNS] = out[config.FEATURE_COLUMNS].fillna(0.0)

    return out


def get_feature_matrix(df: pd.DataFrame) -> pd.DataFrame:
    """Return only the engineered feature columns (in a stable order)."""
    engineered = engineer_features(df)
    return engineered[config.FEATURE_COLUMNS].copy()


if __name__ == "__main__":
    from src.data_loader import load_data

    frame, _ = load_data()
    feat = engineer_features(frame)
    print(feat[config.FEATURE_COLUMNS].head())
    print("Feature columns:", config.FEATURE_COLUMNS)
