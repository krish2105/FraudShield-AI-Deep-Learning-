"""
business_rules.py
=================
Turns a model fraud probability (0..1) into a business decision.

This is the bridge between the data-science output and the bank's
operational workflow:

    0.00 - 0.30  Low Risk     -> Approve
    0.31 - 0.70  Medium Risk  -> Manual Review / OTP
    0.71 - 1.00  High Risk    -> Block / Alert Fraud Team

It also provides a transparent "demo scoring" rule so the dashboard can
still produce sensible scores when no trained model file is present.
"""

from __future__ import annotations

from typing import Dict

import numpy as np
import pandas as pd

from . import config


def risk_band(probability: float) -> Dict[str, str]:
    """Return the risk band dictionary for a given fraud probability.

    The returned dict has keys: band, label, action, color.
    """
    p = float(probability)
    if p <= config.LOW_THRESHOLD:
        band = config.RISK_BANDS["LOW"]
        key = "LOW"
    elif p <= config.HIGH_THRESHOLD:
        band = config.RISK_BANDS["MEDIUM"]
        key = "MEDIUM"
    else:
        band = config.RISK_BANDS["HIGH"]
        key = "HIGH"
    return {
        "band": key,
        "label": band["label"],
        "action": band["action"],
        "color": band["color"],
    }


def risk_label(probability: float) -> str:
    """Convenience: just the human label (Low/Medium/High Risk)."""
    return risk_band(probability)["label"]


def recommended_action(probability: float) -> str:
    """Convenience: just the recommended business action string."""
    return risk_band(probability)["action"]


def add_risk_columns(df: pd.DataFrame, prob_col: str = "fraud_probability") -> pd.DataFrame:
    """Add risk_label, recommended_action and risk_color columns to a frame.

    `prob_col` must already contain fraud probabilities in [0, 1].
    """
    out = df.copy()
    out["risk_label"] = out[prob_col].apply(risk_label)
    out["recommended_action"] = out[prob_col].apply(recommended_action)
    out["risk_color"] = out[prob_col].apply(lambda p: risk_band(p)["color"])
    return out


def demo_score(df: pd.DataFrame) -> np.ndarray:
    """Transparent rule-based fraud score for DEMO MODE (no trained model).

    This is NOT a trained model. It is a deterministic heuristic so the
    dashboard always works. It rewards the classic fraud signals seen in
    PaySim: large transfers/cash-outs that drain the sender's balance to
    zero. Scores are squashed into [0, 1].

    Replace with real model predictions once the LSTM is trained.
    """
    df = df.copy()

    # Defensive defaults if a column is missing.
    amount = pd.to_numeric(df.get("amount", 0), errors="coerce").fillna(0)
    old_org = pd.to_numeric(df.get("oldbalanceOrg", 0), errors="coerce").fillna(0)
    new_org = pd.to_numeric(df.get("newbalanceOrig", 0), errors="coerce").fillna(0)
    ttype = df.get("type", pd.Series(["PAYMENT"] * len(df))).astype(str)

    score = np.zeros(len(df), dtype=float)

    # Signal 1: high amount relative to threshold.
    score += np.clip(amount / (config.HIGH_AMOUNT_THRESHOLD * 4), 0, 0.35)

    # Signal 2: sender balance drained to (near) zero after the txn.
    drained = (old_org > 0) & (new_org <= 1)
    score += np.where(drained, 0.30, 0.0)

    # Signal 3: amount almost equals the whole old balance (full sweep).
    ratio = np.where(old_org > 0, amount / old_org, 0)
    score += np.clip(np.where(ratio >= 0.9, 0.25, ratio * 0.1), 0, 0.25)

    # Signal 4: risky transaction types (TRANSFER / CASH_OUT).
    risky_type = ttype.isin(["TRANSFER", "CASH_OUT"]).to_numpy()
    score += np.where(risky_type, 0.15, 0.0)

    return np.clip(score, 0.0, 0.999)


def estimate_amount_at_risk(df: pd.DataFrame, prob_col: str = "fraud_probability",
                            threshold: float = config.HIGH_THRESHOLD) -> float:
    """Sum of transaction amounts for rows above the high-risk threshold."""
    if prob_col not in df.columns or "amount" not in df.columns:
        return 0.0
    mask = df[prob_col] >= threshold
    return float(df.loc[mask, "amount"].sum())
