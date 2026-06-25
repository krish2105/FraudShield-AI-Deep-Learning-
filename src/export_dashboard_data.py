"""
export_dashboard_data.py
========================
Bridges the Python data/model pipeline to the React dashboard.

It loads the data, scores it with the SAME logic the rest of the project uses
(real LSTM if trained, otherwise transparent demo rules), computes every
aggregate the React pages need, and writes a single JSON file:

    web/public/data/dashboard.json

Run:
    python src/export_dashboard_data.py

Re-run this whenever the data or the trained model changes — the React app
reads the refreshed JSON on its next load.
"""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pandas as pd

try:
    from . import config, business_rules
    from .data_loader import load_data
    from .feature_engineering import engineer_features
    from .predict import score_transactions
    from .utils import read_json, log
except ImportError:  # pragma: no cover - direct script execution
    import sys

    sys.path.append(str(Path(__file__).resolve().parents[1]))
    from src import config, business_rules
    from src.data_loader import load_data
    from src.feature_engineering import engineer_features
    from src.predict import score_transactions
    from src.utils import read_json, log

OUT_PATH = config.PROJECT_ROOT / "web" / "public" / "data" / "dashboard.json"

MAX_SCORED_SAMPLE = 1500   # rows shipped for client-side tables/filters
MAX_ALERTS = 600
MAX_CUSTOMERS = 60


def _r(x, n=4):
    """Round safely, turning NaN/inf into 0 (JSON has no NaN)."""
    try:
        v = float(x)
        if math.isnan(v) or math.isinf(v):
            return 0.0
        return round(v, n)
    except (TypeError, ValueError):
        return 0.0


MAX_SCORING_ROWS = 40000   # cap for responsiveness on the full 6.3M PaySim file


def build_payload() -> dict:
    full_df, source = load_data()
    full_total = len(full_df)
    has_fraud = "isFraud" in full_df.columns
    full_fraud = int(full_df["isFraud"].sum()) if has_fraud else 0

    # Score a REPRESENTATIVE random subsample (preserves the true fraud ratio)
    # so the model runs in seconds on the 6.3M-row file. Headline counts/value
    # come from the FULL data; model-derived figures are scaled up by `scale`.
    if full_total > MAX_SCORING_ROWS:
        df = full_df.sample(MAX_SCORING_ROWS, random_state=config.RANDOM_SEED).reset_index(drop=True)
    else:
        df = full_df.reset_index(drop=True)
    scored, mode = score_transactions(df)
    scale = full_total / max(len(scored), 1)

    p = scored["fraud_probability"]
    high_mask = p >= config.HIGH_THRESHOLD
    scored["_hr"] = high_mask.astype(int)

    # ---- KPIs: headline counts/value from FULL data; risk extrapolated ----
    kpis = {
        "totalTransactions": full_total,
        "fraudTransactions": full_fraud,
        "fraudPercentage": _r(100 * full_fraud / full_total if full_total else 0, 3),
        "totalValue": _r(float(full_df["amount"].sum()) if "amount" in full_df else 0, 2),
        "amountAtRisk": _r(business_rules.estimate_amount_at_risk(scored) * scale, 2),
        "highRiskTransactions": int(round(int(high_mask.sum()) * scale)),
        "highRiskCustomers": int(round(scored.loc[high_mask, "nameOrig"].nunique() * scale))
        if "nameOrig" in scored else int(round(int(high_mask.sum()) * scale)),
        "avgScore": _r(p.mean(), 4),
        "reviewRate": _r(100 * p.between(config.LOW_THRESHOLD, config.HIGH_THRESHOLD).mean(), 2),
    }

    # per-group high-risk RATES from the scored sample (applied to full counts)
    type_hr = scored.groupby("type")["_hr"].mean() if "type" in scored else None
    bins = [0, 1000, 10000, 50000, 200000, float("inf")]
    labels = ["0-1K", "1K-10K", "10K-50K", "50K-200K", "200K+"]
    band_hr = scored.groupby(pd.cut(scored["amount"], bins=bins, labels=labels),
                             observed=True)["_hr"].mean()

    # ---- by transaction type (counts from FULL, risk rate from sample) ---
    by_type = []
    if "type" in full_df.columns:
        for t, grp in full_df.groupby("type"):
            tot = len(grp)
            fr = int(grp["isFraud"].sum()) if has_fraud else 0
            rate = float(type_hr.get(t, 0.0)) if type_hr is not None else 0.0
            by_type.append({
                "type": str(t), "total": tot, "fraud": fr,
                "fraudRatePct": _r(100 * fr / tot if tot else 0, 3),
                "highRisk": int(round(rate * tot)),
                "highRiskRatePct": _r(100 * rate, 2),
            })
        by_type.sort(key=lambda d: d["fraud"], reverse=True)

    # ---- by time step (volume+fraud from FULL, highRisk from sample) -----
    by_step = []
    if "step" in full_df.columns:
        fs = full_df.groupby("step").agg(
            transactions=("amount", "size"),
            fraud=("isFraud", "sum") if has_fraud else ("amount", "size")).reset_index()
        ss = scored.groupby("step")["_hr"].sum()
        by_step = [{"step": int(r.step), "transactions": int(r.transactions),
                    "fraud": int(r.fraud),
                    "highRisk": int(round(float(ss.get(int(r.step), 0)) * scale))}
                   for r in fs.itertuples()]

    # ---- by amount band (counts from FULL, risk rate from sample) --------
    full_band = pd.cut(full_df["amount"], bins=bins, labels=labels)
    by_amount = []
    for b, grp in full_df.groupby(full_band, observed=True):
        tot = len(grp)
        rate = float(band_hr.get(b, 0.0))
        by_amount.append({"band": str(b), "total": tot,
                          "highRisk": int(round(rate * tot)),
                          "highRiskRatePct": _r(100 * rate, 2)})

    # ---- fraud vs genuine + amount histogram (FULL data) -----------------
    fraud_vs = {"genuine": full_total - full_fraud, "fraud": full_fraud}
    cap = full_df["amount"].quantile(0.99) if full_total else 1
    capped = full_df.loc[full_df["amount"] <= cap, "amount"]
    hist = []
    if len(capped):
        counts, edges = np.histogram(capped, bins=40)
        hist = [{"x": _r((edges[i] + edges[i + 1]) / 2, 1), "count": int(counts[i])}
                for i in range(len(counts))]

    # ---- missing values (FULL data) -------------------------------------
    missing = [{"column": c, "missing": int(full_df[c].isnull().sum())}
               for c in full_df.columns]

    # ---- approximate feature importance (|corr| with score) -------------
    feat = engineer_features(scored)
    importance = []
    for col in config.FEATURE_COLUMNS:
        try:
            c = np.corrcoef(feat[col].astype(float), scored["fraud_probability"])[0, 1]
            importance.append({"feature": col, "importance": _r(abs(c) if not np.isnan(c) else 0, 4)})
        except Exception:
            importance.append({"feature": col, "importance": 0.0})
    importance.sort(key=lambda d: d["importance"], reverse=True)

    # ---- compact scored sample (for client-side tables/filters) ---------
    keep = [c for c in ["step", "type", "amount", "nameOrig", "nameDest",
                        "oldbalanceOrg", "newbalanceOrig", "oldbalanceDest",
                        "newbalanceDest", "isFraud", "fraud_probability",
                        "risk_label", "recommended_action"] if c in scored.columns]
    sample = scored[keep].copy()
    if len(sample) > MAX_SCORED_SAMPLE:
        # Keep high-risk rows (capped) + a random fill so tables stay useful.
        hr = sample[sample["fraud_probability"] >= config.HIGH_THRESHOLD]
        if len(hr) >= MAX_SCORED_SAMPLE:
            # More high-risk rows than the cap: sample them down.
            sample = hr.sample(MAX_SCORED_SAMPLE, random_state=config.RANDOM_SEED).sort_index()
        else:
            rest = sample[sample["fraud_probability"] < config.HIGH_THRESHOLD]
            n_fill = max(0, MAX_SCORED_SAMPLE - len(hr))
            fill = rest.sample(min(len(rest), n_fill), random_state=config.RANDOM_SEED)
            sample = pd.concat([hr, fill]).sort_index()
    for c in ["amount", "oldbalanceOrg", "newbalanceOrig", "oldbalanceDest",
              "newbalanceDest", "fraud_probability"]:
        if c in sample:
            sample[c] = sample[c].map(lambda v: _r(v, 4))
    scored_sample = sample.to_dict("records")

    # ---- alerts (high risk) ---------------------------------------------
    alerts_df = scored[high_mask].sort_values("fraud_probability", ascending=False).head(MAX_ALERTS)
    alert_keep = [c for c in ["nameOrig", "type", "amount", "fraud_probability",
                              "risk_label", "recommended_action"] if c in alerts_df.columns]
    alerts = alerts_df[alert_keep].copy()
    if "amount" in alerts:
        alerts["amount"] = alerts["amount"].map(lambda v: _r(v, 2))
    if "fraud_probability" in alerts:
        alerts["fraud_probability"] = alerts["fraud_probability"].map(lambda v: _r(v, 4))
    alerts = alerts.to_dict("records")

    # ---- per-customer sequences -----------------------------------------
    # For sequence display we want accounts WITH HISTORY. On the full PaySim
    # file a random sample mostly has single-transaction accounts, so we
    # additionally fetch the most-active accounts and score their real
    # transaction sequences.
    cust_src = scored
    if full_total > MAX_SCORING_ROWS and "nameOrig" in full_df.columns:
        vc = full_df["nameOrig"].value_counts()
        multi_ids = vc[vc >= 2].head(60).index
        if len(multi_ids):
            sub = full_df[full_df["nameOrig"].isin(multi_ids)]
            sub_scored, _ = score_transactions(sub)
            cust_src = pd.concat([sub_scored, scored], ignore_index=True)

    customers = {}
    if "nameOrig" in cust_src.columns:
        ranked = (cust_src.groupby("nameOrig")["fraud_probability"].max()
                  .sort_values(ascending=False))
        # mix of high-risk and normal customers
        chosen = list(ranked.head(MAX_CUSTOMERS // 2).index) + \
                 list(ranked.tail(MAX_CUSTOMERS // 2).index)
        for cid in dict.fromkeys(chosen):
            cdf = cust_src[cust_src["nameOrig"] == cid]
            if "step" in cdf:
                cdf = cdf.sort_values("step")
            seq = []
            for r in cdf.itertuples():
                seq.append({
                    "step": int(getattr(r, "step", 0)),
                    "type": str(getattr(r, "type", "")),
                    "amount": _r(getattr(r, "amount", 0), 2),
                    "oldbalanceOrg": _r(getattr(r, "oldbalanceOrg", 0), 2),
                    "newbalanceOrig": _r(getattr(r, "newbalanceOrig", 0), 2),
                    "fraud_probability": _r(getattr(r, "fraud_probability", 0), 4),
                    "risk_label": str(getattr(r, "risk_label", "")),
                })
            customers[str(cid)] = seq

    # ---- model metrics + comparison + curves ----------------------------
    metrics = read_json(config.METRICS_PATH, default={}) or {}
    curves = read_json(config.CURVES_PATH, default={}) or {}
    artifacts = read_json(config.ARTIFACTS_PATH, default={}) or {}
    comparison = []
    if config.MODEL_COMPARISON_PATH.exists():
        try:
            comparison = pd.read_csv(config.MODEL_COMPARISON_PATH).to_dict("records")
        except Exception:
            comparison = []

    primary = artifacts.get("primary") or metrics.get("primary") or "lstm"
    return {
        "meta": {
            "mode": mode,                  # "model" or "demo"
            "source": source,              # "real" or "sample"
            "primary": primary,            # primary model name
            "status": metrics.get("status", "NOT_TRAINED"),
            "sequenceLength": config.SEQUENCE_LENGTH,
            "lowThreshold": config.LOW_THRESHOLD,
            "highThreshold": config.HIGH_THRESHOLD,
            "nFeatures": artifacts.get("n_features"),
            "fullRows": full_total,
            "scoredRows": int(len(scored)),
            "sampled": full_total > MAX_SCORING_ROWS,
            "note": "Demo data / demo scoring" if (mode == "demo" or source != "real")
                    else "Trained model on real PaySim data",
        },
        "curves": curves,
        "kpis": kpis,
        "byStep": by_step,
        "byType": by_type,
        "byAmountBand": by_amount,
        "fraudVsGenuine": fraud_vs,
        "amountHistogram": hist,
        "missingByColumn": missing,
        "featureImportance": importance,
        "scoredSample": scored_sample,
        "alerts": alerts,
        "customers": customers,
        "metrics": metrics,
        "modelComparison": comparison,
        "columns": [
            {"column": "step", "description": "Time step (1 = 1 hour)"},
            {"column": "type", "description": "PAYMENT / TRANSFER / CASH_OUT / DEBIT / CASH_IN"},
            {"column": "amount", "description": "Transaction amount"},
            {"column": "nameOrig", "description": "Sender (origin) customer ID"},
            {"column": "oldbalanceOrg", "description": "Sender balance before"},
            {"column": "newbalanceOrig", "description": "Sender balance after"},
            {"column": "nameDest", "description": "Receiver (destination) ID"},
            {"column": "oldbalanceDest", "description": "Receiver balance before"},
            {"column": "newbalanceDest", "description": "Receiver balance after"},
            {"column": "isFraud", "description": "1 = fraud, 0 = genuine (label)"},
            {"column": "isFlaggedFraud", "description": "1 = flagged by a naive rule"},
        ],
    }


def write_snapshot(payload: dict) -> str:
    """Write a payload to the static snapshot the React app loads first."""
    import json

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, separators=(",", ":"))
    return str(OUT_PATH)


def main() -> str:
    payload = build_payload()
    write_snapshot(payload)
    size_kb = OUT_PATH.stat().st_size / 1024
    log(f"Wrote dashboard data -> {OUT_PATH} ({size_kb:.0f} KB)")
    log(f"mode={payload['meta']['mode']} source={payload['meta']['source']} "
        f"rows={payload['kpis']['totalTransactions']}")
    return str(OUT_PATH)


if __name__ == "__main__":
    main()
