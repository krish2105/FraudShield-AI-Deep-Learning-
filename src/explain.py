"""
explain.py
==========
Per-decision explainability (Phase 7, lightweight).

Returns plain-English **reason codes** for why a transaction scored the way it
did, based on the same engineered signals the models use. This is dependency-free
and instant (no SHAP needed), so it can run inline with every score. It is a
faithful, rule-grounded approximation — the roadmap (docs/BRAINSTORM.md §2)
upgrades this to true SHAP / Integrated-Gradient attributions.

    explain_transaction(txn) -> {"reasons": [...], "signals": {...}}
"""

from __future__ import annotations

from pathlib import Path

try:
    from . import config
except ImportError:  # pragma: no cover
    import sys
    sys.path.append(str(Path(__file__).resolve().parents[1]))
    from src import config


def _f(v, default=0.0) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def explain_transaction(txn: dict) -> dict:
    """Generate ranked reason codes for a single transaction dict."""
    amount = _f(txn.get("amount"))
    old_org = _f(txn.get("oldbalanceOrg"))
    new_org = _f(txn.get("newbalanceOrig"))
    old_dest = _f(txn.get("oldbalanceDest"))
    new_dest = _f(txn.get("newbalanceDest"))
    ttype = str(txn.get("type", "")).upper()

    # The two strongest PaySim fraud signals: double-entry inconsistencies.
    err_orig = new_org + amount - old_org
    err_dest = old_dest + amount - new_dest
    ratio = amount / old_org if old_org > 0 else (1.0 if amount > 0 else 0.0)

    reasons = []  # (severity 0-1, text)

    if ttype in config.FRAUD_TYPES and old_org > 0 and new_org == 0:
        reasons.append((0.95, f"Account fully drained: a {ttype} emptied the balance "
                              f"to zero (classic account-takeover sweep)."))
    if abs(err_dest) > 1.0 and ttype in config.FRAUD_TYPES:
        reasons.append((0.85, "Destination balance did not update for the amount "
                              "received — the books don't balance (mule-account signature)."))
    if ratio >= 0.9 and old_org > 0:
        reasons.append((0.8, f"Amount is {ratio*100:.0f}% of the available balance — "
                             f"an unusually large share."))
    if amount >= config.HIGH_AMOUNT_THRESHOLD:
        reasons.append((0.7, f"Very high amount ({amount:,.0f}) above the "
                             f"{config.HIGH_AMOUNT_THRESHOLD:,} review threshold."))
    if ttype in config.FRAUD_TYPES:
        reasons.append((0.4, f"Transaction type {ttype} is where fraud concentrates "
                             f"in payment networks."))
    if abs(err_orig) > 1.0:
        reasons.append((0.5, "Origin balance change is inconsistent with the amount."))

    if not reasons:
        reasons.append((0.1, "No strong fraud signals — amount and balance changes "
                             "are consistent with normal behaviour."))

    reasons.sort(key=lambda r: r[0], reverse=True)
    return {
        "reasons": [{"severity": round(s, 2), "text": t} for s, t in reasons[:5]],
        "signals": {
            "amount_to_balance_ratio": round(ratio, 4),
            "errorBalanceOrig": round(err_orig, 2),
            "errorBalanceDest": round(err_dest, 2),
            "drained_to_zero": bool(old_org > 0 and new_org == 0),
            "high_amount": bool(amount >= config.HIGH_AMOUNT_THRESHOLD),
        },
    }
