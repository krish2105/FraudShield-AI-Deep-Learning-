"""
data_loader.py
==============
Loads transaction data for the project.

Loading priority:
    1. data/paysim.csv          (the REAL dataset, if the user added it)
    2. data/sample_transactions.csv  (synthetic demo data)
    3. generate the sample on the fly if neither exists

This guarantees the notebook and dashboard ALWAYS have data to work with.
"""

from __future__ import annotations

from pathlib import Path
from typing import Tuple

import pandas as pd

try:
    from . import config
    from .utils import log
    from .make_sample_data import main as make_sample
except ImportError:  # pragma: no cover - direct script execution
    import sys

    sys.path.append(str(Path(__file__).resolve().parents[1]))
    from src import config
    from src.utils import log
    from src.make_sample_data import main as make_sample


def load_data(prefer_real: bool = True) -> Tuple[pd.DataFrame, str]:
    """Load the transaction dataset.

    Returns
    -------
    (df, source)
        df     : the loaded DataFrame
        source : one of "real", "sample" describing where the data came from
    """
    # 1. Real PaySim dataset.
    if prefer_real and config.REAL_DATA_PATH.exists():
        log(f"Loading REAL dataset: {config.REAL_DATA_PATH}")
        df = pd.read_csv(config.REAL_DATA_PATH)
        return df, "real"

    # 2. Existing sample dataset.
    if config.SAMPLE_DATA_PATH.exists():
        log(f"Real dataset not found. Loading SAMPLE (demo only): "
            f"{config.SAMPLE_DATA_PATH}")
        df = pd.read_csv(config.SAMPLE_DATA_PATH)
        return df, "sample"

    # 3. Nothing on disk - generate the sample now.
    log("No dataset found. Generating sample data...")
    make_sample()
    df = pd.read_csv(config.SAMPLE_DATA_PATH)
    return df, "sample"


def basic_overview(df: pd.DataFrame) -> dict:
    """Return a small dictionary summarising the dataframe (for EDA/UI)."""
    fraud_count = int(df["isFraud"].sum()) if "isFraud" in df.columns else 0
    total = len(df)
    return {
        "rows": total,
        "columns": list(df.columns),
        "n_columns": df.shape[1],
        "null_values": int(df.isnull().sum().sum()),
        "duplicate_rows": int(df.duplicated().sum()),
        "fraud_count": fraud_count,
        "non_fraud_count": total - fraud_count,
        "fraud_percentage": round(100 * fraud_count / total, 4) if total else 0.0,
    }


if __name__ == "__main__":
    frame, src = load_data()
    log(f"Loaded {len(frame):,} rows from source='{src}'")
    print(frame.head())
    print(basic_overview(frame))
