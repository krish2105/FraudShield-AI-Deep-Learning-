"""
preprocessing.py
================
Cleans the data and scales the numeric features.

Steps:
    1. handle missing values
    2. (categorical encoding already done in feature_engineering)
    3. scale numeric features with StandardScaler

The fitted scaler is saved to models/scaler.pkl so the dashboard and
predict.py apply EXACTLY the same transformation at inference time.
"""

from __future__ import annotations

from pathlib import Path
from typing import Tuple

import joblib
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler

try:
    from . import config
    from .feature_engineering import engineer_features
    from .utils import log
except ImportError:  # pragma: no cover
    import sys

    sys.path.append(str(Path(__file__).resolve().parents[1]))
    from src import config
    from src.feature_engineering import engineer_features
    from src.utils import log


def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    """Basic cleaning: drop exact duplicates and fill missing numerics."""
    out = df.copy()
    out = out.drop_duplicates()
    # Fill any remaining numeric NaNs with 0 (safe for this domain).
    num_cols = out.select_dtypes(include=[np.number]).columns
    out[num_cols] = out[num_cols].fillna(0)
    return out


def fit_scaler(df: pd.DataFrame) -> Tuple[StandardScaler, pd.DataFrame]:
    """Engineer features, fit a StandardScaler and return (scaler, scaled_df).

    `scaled_df` keeps the same columns (config.FEATURE_COLUMNS) but scaled.
    """
    engineered = engineer_features(df)
    X = engineered[config.FEATURE_COLUMNS].astype(float)

    scaler = StandardScaler()
    scaled = scaler.fit_transform(X)
    scaled_df = pd.DataFrame(scaled, columns=config.FEATURE_COLUMNS,
                             index=engineered.index)
    return scaler, scaled_df


def transform_with_scaler(df: pd.DataFrame, scaler: StandardScaler) -> pd.DataFrame:
    """Apply an already-fitted scaler to new data (inference path)."""
    engineered = engineer_features(df)
    X = engineered[config.FEATURE_COLUMNS].astype(float)
    scaled = scaler.transform(X)
    return pd.DataFrame(scaled, columns=config.FEATURE_COLUMNS, index=engineered.index)


def save_scaler(scaler: StandardScaler, path: Path = config.SCALER_PATH) -> None:
    """Persist the scaler and the feature column order to disk."""
    config.ensure_dirs()
    joblib.dump(scaler, path)
    joblib.dump(config.FEATURE_COLUMNS, config.FEATURE_COLUMNS_PATH)
    log(f"Saved scaler -> {path}")
    log(f"Saved feature columns -> {config.FEATURE_COLUMNS_PATH}")


def load_scaler(path: Path = config.SCALER_PATH):
    """Load a previously saved scaler, or None if it does not exist."""
    if Path(path).exists():
        return joblib.load(path)
    return None
