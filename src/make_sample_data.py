"""
make_sample_data.py
===================
Creates a REALISTIC but SYNTHETIC sample dataset that mimics the structure
of the PaySim Mobile Money Fraud dataset.

Why this file exists
--------------------
The real PaySim file (data/paysim.csv) is large and not shipped with this
project. So the notebook and the Streamlit dashboard can still run end to
end, this script generates a small demo dataset at:

    data/sample_transactions.csv

IMPORTANT: This sample data is FOR DEMO / TESTING ONLY. Any metrics produced
from it are placeholders. Download the real PaySim dataset, save it as
data/paysim.csv, and re-run the notebook for genuine results.

Run with:
    python src/make_sample_data.py
"""

from __future__ import annotations

import numpy as np
import pandas as pd

# Support running as a module (python -m src.make_sample_data) AND as a
# plain script (python src/make_sample_data.py).
try:
    from . import config
    from .utils import log
except ImportError:  # pragma: no cover - direct script execution
    import sys
    from pathlib import Path

    sys.path.append(str(Path(__file__).resolve().parents[1]))
    from src import config
    from src.utils import log


def generate_sample(n_customers: int = 250, max_txn_per_customer: int = 18,
                    seed: int = config.RANDOM_SEED) -> pd.DataFrame:
    """Generate a synthetic PaySim-like transaction table.

    We build per-customer transaction *sequences* so the data is suitable
    for sequence modelling. A small fraction of customers experience a
    fraud "attack" (sudden large transfer + cash-out that drains balance).
    """
    rng = np.random.default_rng(seed)
    rows = []

    for c in range(n_customers):
        cust = f"C{1000000 + c}"
        # Mimic real PaySim sparsity: ~40% of accounts make only 1-3
        # transactions (so the masked sequence model is genuinely exercised),
        # the rest have richer histories the LSTM can exploit.
        if rng.random() < 0.4:
            n_txn = int(rng.integers(1, 4))
        else:
            n_txn = int(rng.integers(6, max_txn_per_customer + 1))

        # Starting balance for this customer.
        balance = float(rng.uniform(2_000, 80_000))
        # ~8% of customers will be victims of a fraud burst.
        is_victim = rng.random() < 0.08
        # Pick a step at which the fraud burst begins (late in the sequence).
        fraud_start = int(rng.integers(max(n_txn - 3, 0), max(n_txn, 1))) if is_victim else -1

        for t in range(n_txn):
            step = t + 1  # 1-based time step (like PaySim hours)
            old_org = balance
            is_fraud = 0
            is_flagged = 0

            if is_victim and t >= fraud_start and old_org > 0:
                # FRAUD pattern: a full account sweep via TRANSFER or CASH_OUT.
                # The fraudster takes the WHOLE balance, so the sender account
                # is drained to zero (the classic, clearly-fraudulent pattern).
                ttype = rng.choice(["TRANSFER", "CASH_OUT"])
                amount = round(old_org, 2)
                new_org = 0.0
                # Real PaySim signature: the mule destination account's balance
                # does NOT update (stays 0), so the books don't balance —
                # this is what errorBalanceDest captures.
                old_dest = 0.0
                new_dest = 0.0
                is_fraud = 1
                # PaySim flags some large transfers via a simple rule.
                if amount > 200_000:
                    is_flagged = 1
                name_dest = f"C{rng.integers(8000000, 8999999)}"
            else:
                # NORMAL behaviour: moderate amounts, balance stays positive.
                ttype = rng.choice(
                    config.TRANSACTION_TYPES,
                    p=[0.34, 0.10, 0.18, 0.06, 0.32],  # PAYMENT/TRANSFER/CASH_OUT/DEBIT/CASH_IN
                )
                if ttype == "CASH_IN":
                    amount = round(float(rng.uniform(50, 8_000)), 2)
                    new_org = round(old_org + amount, 2)
                    old_dest = float(rng.uniform(0, 20_000))
                    new_dest = round(max(old_dest - amount, 0.0), 2)
                    name_dest = f"C{rng.integers(8000000, 8999999)}"
                else:
                    # Spend a fraction of the available balance (always valid
                    # even when the balance is small, so low < high).
                    cap = max(min(old_org, 6_000.0), 50.0)
                    amount = round(float(rng.uniform(20, cap)), 2)
                    amount = min(amount, old_org) if old_org > 0 else amount
                    new_org = round(max(old_org - amount, 0.0), 2)
                    # Merchants (M...) for PAYMENT, customers otherwise.
                    if ttype == "PAYMENT":
                        name_dest = f"M{rng.integers(1000000, 1999999)}"
                        old_dest = 0.0
                        new_dest = 0.0
                    else:
                        name_dest = f"C{rng.integers(8000000, 8999999)}"
                        old_dest = float(rng.uniform(0, 20_000))
                        new_dest = round(old_dest + amount, 2)

            rows.append({
                "step": step,
                "type": ttype,
                "amount": amount,
                "nameOrig": cust,
                "oldbalanceOrg": round(old_org, 2),
                "newbalanceOrig": round(new_org, 2),
                "nameDest": name_dest,
                "oldbalanceDest": round(old_dest, 2),
                "newbalanceDest": round(new_dest, 2),
                "isFraud": is_fraud,
                "isFlaggedFraud": is_flagged,
            })

            balance = new_org  # carry balance forward in the sequence

    df = pd.DataFrame(rows, columns=config.RAW_COLUMNS)
    return df


def main() -> str:
    """Generate and save the sample dataset. Returns the output path."""
    config.ensure_dirs()
    log("Generating synthetic PaySim-like sample data (DEMO ONLY)...")
    df = generate_sample()
    config.SAMPLE_DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(config.SAMPLE_DATA_PATH, index=False)
    fraud_rate = 100 * df["isFraud"].mean()
    log(f"Saved {len(df):,} rows to {config.SAMPLE_DATA_PATH}")
    log(f"Fraud rate in sample: {fraud_rate:.2f}%  (demo data only)")
    return str(config.SAMPLE_DATA_PATH)


if __name__ == "__main__":
    main()
