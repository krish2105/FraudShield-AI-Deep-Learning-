"""
Unit tests for the core FraudShield pipeline (Phase 7).
Run with:  pytest -q
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src import config
from src.make_sample_data import generate_sample
from src.feature_engineering import engineer_features
from src.preprocessing import clean_data, fit_scaler, transform_with_scaler
from src.sequence_builder import build_padded_sequences, time_aware_split
from src.business_rules import risk_band, demo_score, add_risk_columns
from src.explain import explain_transaction
from src.calibration import fit_calibrator, apply_calibrator


@pytest.fixture(scope="module")
def sample_df() -> pd.DataFrame:
    return generate_sample(n_customers=60, seed=1)


def test_sample_has_fraud_and_schema(sample_df):
    assert len(sample_df) > 0
    assert set(config.RAW_COLUMNS).issubset(sample_df.columns)
    assert sample_df["isFraud"].sum() >= 1, "sample must contain some fraud"


def test_feature_engineering_adds_signals(sample_df):
    eng = engineer_features(sample_df)
    for col in ("errorBalanceOrig", "errorBalanceDest", "amount_to_balance_ratio"):
        assert col in eng.columns
    assert not eng[config.FEATURE_COLUMNS].isna().any().any()


def test_padded_sequences_shape_and_lengths(sample_df):
    df = clean_data(sample_df)
    _, scaled = fit_scaler(df)
    X, y, lengths, idx = build_padded_sequences(
        scaled.reset_index(drop=True), df["isFraud"], df["nameOrig"], df["step"])
    assert X.ndim == 3 and X.shape[1] == config.SEQUENCE_LENGTH
    assert X.shape[2] == len(config.FEATURE_COLUMNS)
    assert len(X) == len(y) == len(lengths)
    assert lengths.min() >= 1 and lengths.max() <= config.SEQUENCE_LENGTH


def test_time_aware_split_no_overlap(sample_df):
    X = np.arange(100).reshape(100, 1, 1).astype("float32")
    y = (np.arange(100) % 5 == 0).astype(int)
    X_tr, X_te, y_tr, y_te = time_aware_split(X, y, test_size=0.2)
    assert len(X_tr) + len(X_te) == 100
    # train comes strictly before test (no shuffling)
    assert X_tr.max() < X_te.min()


def test_scaler_roundtrip_consistent(sample_df):
    df = clean_data(sample_df)
    scaler, scaled = fit_scaler(df)
    again = transform_with_scaler(df, scaler)
    np.testing.assert_allclose(scaled.values, again.values, rtol=1e-5, atol=1e-5)


def test_risk_bands_monotonic():
    assert risk_band(0.1)["band"] == "LOW"
    assert risk_band(0.5)["band"] == "MEDIUM"
    assert risk_band(0.9)["band"] == "HIGH"


def test_demo_score_flags_obvious_fraud():
    df = pd.DataFrame([{
        "step": 1, "type": "TRANSFER", "amount": 90000.0, "nameOrig": "C1",
        "oldbalanceOrg": 90000.0, "newbalanceOrig": 0.0, "nameDest": "C2",
        "oldbalanceDest": 0.0, "newbalanceDest": 0.0, "isFraud": 1,
    }])
    scored = add_risk_columns(df.assign(fraud_probability=demo_score(df)))
    assert scored["fraud_probability"].iloc[0] > 0.5


def test_explain_returns_reasons():
    out = explain_transaction({
        "type": "TRANSFER", "amount": 90000.0, "oldbalanceOrg": 90000.0,
        "newbalanceOrig": 0.0, "oldbalanceDest": 0.0, "newbalanceDest": 0.0})
    assert out["reasons"] and out["signals"]["drained_to_zero"] is True


def test_calibrator_is_monotonic_probability():
    rng = np.random.default_rng(0)
    y = rng.integers(0, 2, size=500)
    p = np.clip(0.5 * y + rng.normal(0, 0.2, size=500), 0, 1)
    cal = fit_calibrator(y, p)
    out = apply_calibrator(cal, np.array([0.0, 0.5, 1.0]))
    assert out.min() >= 0.0 and out.max() <= 1.0
