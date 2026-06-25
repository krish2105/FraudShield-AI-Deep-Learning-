"""
predict.py
==========
Inference for the dashboard and API.

Uses the trained PyTorch primary model (+ saved scaler) over masked,
variable-length sequences. If the model or scaler is missing, it falls back to
the transparent rule-based `demo_score` and reports `mode="demo"` so the UI can
warn the user.

Public entry points:
    score_transactions(df) -> (df + fraud columns, mode)
    score_one(dict)        -> dict with probability + risk band   (live scoring)
"""

from __future__ import annotations

from pathlib import Path
from typing import Tuple

import numpy as np
import pandas as pd

try:
    from . import config
    from . import business_rules
    from .feature_engineering import engineer_features
    from .preprocessing import load_scaler, transform_with_scaler
    from .sequence_builder import build_padded_sequences
    from .utils import log, read_json
except ImportError:  # pragma: no cover
    import sys
    sys.path.append(str(Path(__file__).resolve().parents[1]))
    from src import config
    from src import business_rules
    from src.feature_engineering import engineer_features
    from src.preprocessing import load_scaler, transform_with_scaler
    from src.sequence_builder import build_padded_sequences
    from src.utils import log, read_json


def _primary_model_path() -> Path:
    """Path of the trained primary model (from inference_artifacts.json)."""
    art = read_json(config.ARTIFACTS_PATH, default={}) or {}
    primary = art.get("primary", "lstm")
    return {
        "lstm": config.LSTM_MODEL_PATH,
        "gru": config.GRU_MODEL_PATH,
        "cnn": config.CNN_MODEL_PATH,
        "dense_nn": config.DENSE_MODEL_PATH,
    }.get(primary, config.LSTM_MODEL_PATH)


def model_available() -> bool:
    """True only if BOTH a trained primary model and the scaler exist."""
    return _primary_model_path().exists() and config.SCALER_PATH.exists()


def _load():
    """Load (model, scaler) or (None, None). torch imported lazily."""
    scaler = load_scaler()
    path = _primary_model_path()
    if scaler is None or not path.exists():
        return None, None
    try:
        from . import dl_models as dl
    except ImportError:  # pragma: no cover
        from src import dl_models as dl
    model, _ = dl.load_model(path)
    return model, scaler


def score_transactions(df: pd.DataFrame) -> Tuple[pd.DataFrame, str]:
    """Score a transaction table; attach risk columns. Returns (df, mode)."""
    out = df.copy().reset_index(drop=True)
    model, scaler = _load()

    # ---- DEMO MODE -------------------------------------------------------
    if model is None or scaler is None:
        out["fraud_probability"] = business_rules.demo_score(out)
        return business_rules.add_risk_columns(out), "demo"

    # ---- MODEL MODE ------------------------------------------------------
    try:
        from . import dl_models as dl
    except ImportError:  # pragma: no cover
        from src import dl_models as dl
    try:
        X_scaled = transform_with_scaler(out, scaler).reset_index(drop=True)
        groups = out.get("nameOrig", pd.Series(range(len(out))))
        order = out.get("step", pd.Series(range(len(out))))
        X, _, lengths, idx = build_padded_sequences(
            X_scaled, out.get("isFraud", pd.Series(np.zeros(len(out)))),
            groups, order, sequence_length=config.SEQUENCE_LENGTH)

        probs = np.full(len(out), np.nan)
        if len(X):
            preds = dl.predict_proba(model, X, lengths)
            for i, p in zip(idx, preds):
                probs[i] = float(p)
        # any rows without a sequence prediction -> demo score (safety net)
        if np.isnan(probs).any():
            demo = business_rules.demo_score(out)
            probs = np.where(np.isnan(probs), demo, probs)

        out["fraud_probability"] = np.clip(probs, 0, 1)
        return business_rules.add_risk_columns(out), "model"

    except Exception as exc:  # any failure -> safe demo fallback
        log(f"Model scoring failed ({exc}); using demo mode.")
        out["fraud_probability"] = business_rules.demo_score(out)
        return business_rules.add_risk_columns(out), "demo"


def score_one(txn: dict, history: list[dict] | None = None) -> dict:
    """Score a SINGLE transaction (optionally with prior history) for live use.

    `txn`     : one transaction dict (PaySim columns).
    `history` : optional list of the same customer's earlier transactions,
                oldest first, to give the sequence model context.
    Returns {probability, risk_label, recommended_action, band, mode}.
    """
    rows = (history or []) + [txn]
    df = pd.DataFrame(rows)
    scored, mode = score_transactions(df)
    last = scored.iloc[-1]
    band = business_rules.risk_band(last["fraud_probability"])
    return {
        "probability": round(float(last["fraud_probability"]), 4),
        "risk_label": band["label"],
        "recommended_action": band["action"],
        "band": band["band"],
        "color": band["color"],
        "mode": mode,
    }


if __name__ == "__main__":
    from src.data_loader import load_data
    frame, _ = load_data()
    scored, mode = score_transactions(frame.head(500))
    log(f"Scored in mode='{mode}'")
    print(scored[["amount", "type", "fraud_probability", "risk_label"]].head())
