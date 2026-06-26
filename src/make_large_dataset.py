"""
make_large_dataset.py
=====================
Generate a LARGE, realistic, synthetic PaySim-style dataset so the whole
project can be trained and evaluated at scale — even when the real ~6.3M-row
PaySim file is not available (it requires Kaggle credentials; see
src/download_paysim.py).

This is still SYNTHETIC data and is labelled as such everywhere. But unlike the
tiny 2k sample, it is large enough that a temporal train/test split contains
hundreds of fraud cases, so the reported metrics are meaningful rather than an
artifact of a handful of easy rows.

Design choices that mirror real PaySim
--------------------------------------
* Fraud occurs only in TRANSFER / CASH_OUT and drains the origin to zero.
* Realistic low fraud prevalence (~0.6%), so the imbalance the LSTM must handle
  is genuine.
* Account sparsity: ~40% of accounts have 1–3 transactions (exercises the
  masked variable-length sequence model honestly).
* The mule destination's balance does not update on fraud, leaving the
  double-entry books inconsistent — the errorBalanceOrig/Dest signal.
* A global, monotonically increasing `step` (hour) so a temporal split is
  "train on the past, test on the future".

Run:
    python src/make_large_dataset.py                 # ~500k rows -> data/paysim.csv
    python src/make_large_dataset.py 1000000         # custom row target
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

try:
    from . import config
    from .utils import log
except ImportError:  # pragma: no cover
    sys.path.append(str(Path(__file__).resolve().parents[1]))
    from src import config
    from src.utils import log

TARGET_ROWS = 500_000
FRAUD_VICTIM_RATE = 0.012      # fraction of accounts that suffer a fraud burst
SEED = config.RANDOM_SEED


def generate_large(target_rows: int = TARGET_ROWS, seed: int = SEED) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rows = []
    global_step = 0
    # Average ~8 txns/account -> estimate the customer count for the target size.
    n_customers = max(1000, int(target_rows / 8))

    for c in range(n_customers):
        if len(rows) >= target_rows:
            break
        cust = f"C{1000000 + c}"
        if rng.random() < 0.40:
            n_txn = int(rng.integers(1, 4))
        else:
            n_txn = int(rng.integers(6, 19))

        balance = float(rng.uniform(2_000, 120_000))
        is_victim = rng.random() < FRAUD_VICTIM_RATE
        fraud_start = int(rng.integers(max(n_txn - 3, 0), max(n_txn, 1))) if is_victim else -1

        for t in range(n_txn):
            global_step += 1
            step = global_step               # global, increasing -> temporal split
            old_org = balance
            is_fraud = 0
            is_flagged = 0

            if is_victim and t >= fraud_start and old_org > 0:
                ttype = rng.choice(["TRANSFER", "CASH_OUT"])
                amount = round(old_org, 2)
                new_org = 0.0
                old_dest = 0.0
                new_dest = 0.0                # mule balance does NOT update
                is_fraud = 1
                if amount > config.HIGH_AMOUNT_THRESHOLD:
                    is_flagged = 1
                name_dest = f"C{rng.integers(8000000, 8999999)}"
            else:
                ttype = rng.choice(
                    config.TRANSACTION_TYPES,
                    p=[0.34, 0.10, 0.18, 0.06, 0.32],
                )
                if ttype == "CASH_IN":
                    amount = round(float(rng.uniform(50, 8_000)), 2)
                    new_org = round(old_org + amount, 2)
                    old_dest = float(rng.uniform(0, 20_000))
                    new_dest = round(max(old_dest - amount, 0.0), 2)
                    name_dest = f"C{rng.integers(8000000, 8999999)}"
                else:
                    cap = max(min(old_org, 6_000.0), 50.0)
                    amount = round(float(rng.uniform(20, cap)), 2)
                    amount = min(amount, old_org) if old_org > 0 else amount
                    new_org = round(max(old_org - amount, 0.0), 2)
                    if ttype == "PAYMENT":
                        name_dest = f"M{rng.integers(1000000, 1999999)}"
                        old_dest = 0.0
                        new_dest = 0.0
                    else:
                        name_dest = f"C{rng.integers(8000000, 8999999)}"
                        old_dest = float(rng.uniform(0, 20_000))
                        new_dest = round(old_dest + amount, 2)

            rows.append((step, ttype, amount, cust, round(old_org, 2),
                         round(new_org, 2), name_dest, round(old_dest, 2),
                         round(new_dest, 2), is_fraud, is_flagged))
            balance = new_org

        if c % 5000 == 0 and c:
            log(f"  …generated {len(rows):,} rows ({c:,} accounts)")

    df = pd.DataFrame(rows, columns=config.RAW_COLUMNS)
    return df


def main(target_rows: int = TARGET_ROWS) -> str:
    config.ensure_dirs()
    log(f"Generating LARGE synthetic PaySim-style dataset (~{target_rows:,} rows)…")
    df = generate_large(target_rows)
    out = config.REAL_DATA_PATH       # install as the 'real' slot so training uses it
    df.to_csv(out, index=False)
    fraud = int(df["isFraud"].sum())
    log(f"Saved {len(df):,} rows -> {out}")
    log(f"Fraud: {fraud:,} cases ({100*fraud/len(df):.3f}%) | accounts: "
        f"{df['nameOrig'].nunique():,} | steps: {df['step'].min()}–{df['step'].max()}")
    log("NOTE: synthetic data. For genuine results use the real PaySim file "
        "(python src/download_paysim.py).")
    return str(out)


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else TARGET_ROWS
    main(n)
