"""
config.py
=========
Central configuration for FraudShield AI.

Everything that other modules might need to agree on lives here:
folder paths, file names, model hyper-parameters, feature lists and
the fraud risk thresholds. We use only RELATIVE paths (built from the
project root) so nothing breaks when the project is copied to another
computer.
"""

from pathlib import Path

# ---------------------------------------------------------------------------
# Project paths (all relative to this file's location)
# ---------------------------------------------------------------------------
# config.py lives in <project_root>/src/, so the project root is one level up.
PROJECT_ROOT = Path(__file__).resolve().parents[1]

DATA_DIR = PROJECT_ROOT / "data"
MODELS_DIR = PROJECT_ROOT / "models"
REPORTS_DIR = PROJECT_ROOT / "reports"
NOTEBOOKS_DIR = PROJECT_ROOT / "notebooks"

# Real PaySim dataset (user drops it here). If missing we fall back to sample.
REAL_DATA_PATH = DATA_DIR / "paysim.csv"
SAMPLE_DATA_PATH = DATA_DIR / "sample_transactions.csv"

# Saved model / artifact paths
# DL models are implemented in PyTorch (.pt checkpoints) for rock-solid
# Apple-Silicon / Python 3.13 support (TensorFlow segfaults on this stack).
LSTM_MODEL_PATH = MODELS_DIR / "lstm_fraud_model.pt"
DENSE_MODEL_PATH = MODELS_DIR / "dense_nn_baseline.pt"
GRU_MODEL_PATH = MODELS_DIR / "gru_fraud_model.pt"
CNN_MODEL_PATH = MODELS_DIR / "cnn_fraud_model.pt"
AUTOENCODER_MODEL_PATH = MODELS_DIR / "autoencoder_fraud_model.pt"
SCALER_PATH = MODELS_DIR / "scaler.pkl"
FEATURE_COLUMNS_PATH = MODELS_DIR / "feature_columns.pkl"
# Extra inference artifacts (autoencoder anomaly threshold, primary model name).
ARTIFACTS_PATH = MODELS_DIR / "inference_artifacts.json"

# Reports
METRICS_PATH = REPORTS_DIR / "metrics.json"
MODEL_COMPARISON_PATH = REPORTS_DIR / "model_comparison.csv"
CURVES_PATH = REPORTS_DIR / "curves.json"          # ROC/PR/threshold/history points

# ---------------------------------------------------------------------------
# Dataset schema (PaySim columns)
# ---------------------------------------------------------------------------
RAW_COLUMNS = [
    "step",
    "type",
    "amount",
    "nameOrig",
    "oldbalanceOrg",
    "newbalanceOrig",
    "nameDest",
    "oldbalanceDest",
    "newbalanceDest",
    "isFraud",
    "isFlaggedFraud",
]

TRANSACTION_TYPES = ["PAYMENT", "TRANSFER", "CASH_OUT", "DEBIT", "CASH_IN"]

# ---------------------------------------------------------------------------
# Feature engineering output columns
# ---------------------------------------------------------------------------
# Engineered numeric features that feed the models.
FEATURE_COLUMNS = [
    "amount",
    "oldbalanceOrg",
    "newbalanceOrig",
    "oldbalanceDest",
    "newbalanceDest",
    "origin_balance_change",
    "destination_balance_change",
    "amount_to_balance_ratio",
    "zero_balance_flag",
    "high_amount_flag",
    "transaction_count_by_customer",
    "type_encoded",
    # Balance-consistency errors — among the strongest known PaySim fraud
    # signals (fraud leaves the double-entry bookkeeping inconsistent).
    "errorBalanceOrig",   # newbalanceOrig + amount - oldbalanceOrg
    "errorBalanceDest",   # oldbalanceDest + amount - newbalanceDest
]

# In real PaySim, fraud occurs ONLY in these two transaction types. Scoping to
# them focuses the model and matches reality. Set SCOPE_TO_FRAUD_TYPES=False to
# train on every type.
FRAUD_TYPES = ["TRANSFER", "CASH_OUT"]
SCOPE_TO_FRAUD_TYPES = False   # notebook can flip this on for the real dataset

# ---------------------------------------------------------------------------
# Sequence / model hyper-parameters
# ---------------------------------------------------------------------------
SEQUENCE_LENGTH = 10          # number of past transactions fed to the LSTM
RANDOM_SEED = 42
TEST_SIZE = 0.2               # fraction held out for testing
HIGH_AMOUNT_THRESHOLD = 200_000   # PaySim amounts are in money units

# Training
EPOCHS = 15
BATCH_SIZE = 256
LSTM_UNITS = 64
DROPOUT_RATE = 0.3
DENSE_UNITS = 32
LEARNING_RATE = 1e-3

# Imbalance handling: focal loss focuses learning on the rare, hard fraud cases.
USE_FOCAL_LOSS = True
FOCAL_GAMMA = 2.0
# CNN
CNN_FILTERS = 64
CNN_KERNEL = 3
# Autoencoder (unsupervised anomaly detector trained on genuine traffic only)
AE_LATENT_DIM = 8
AE_HIDDEN = 32
# Pick the AE anomaly threshold at this percentile of genuine reconstruction error.
AE_THRESHOLD_PERCENTILE = 99.0

# ---------------------------------------------------------------------------
# Fraud risk thresholds (business rules)
# ---------------------------------------------------------------------------
# Probability ranges mapped to a risk band, a business action and a colour
# (the colour is used by the Streamlit dashboard for risk badges).
RISK_BANDS = {
    "LOW": {
        "min": 0.00,
        "max": 0.30,
        "label": "Low Risk",
        "action": "Approve",
        "color": "#16a34a",   # green
    },
    "MEDIUM": {
        "min": 0.31,
        "max": 0.70,
        "label": "Medium Risk",
        "action": "Manual Review / OTP",
        "color": "#f59e0b",   # amber
    },
    "HIGH": {
        "min": 0.71,
        "max": 1.00,
        "label": "High Risk",
        "action": "Block / Alert Fraud Team",
        "color": "#dc2626",   # red
    },
}

LOW_THRESHOLD = 0.30
HIGH_THRESHOLD = 0.70

# ---------------------------------------------------------------------------
# Business impact default assumptions (used by the simulator page)
# ---------------------------------------------------------------------------
DEFAULT_AVG_FRAUD_LOSS = 1200.0     # average money lost per undetected fraud
DEFAULT_MANUAL_REVIEW_COST = 8.0    # cost to manually review one flagged txn


def ensure_dirs():
    """Create the standard output folders if they do not exist yet."""
    for d in (DATA_DIR, MODELS_DIR, REPORTS_DIR):
        d.mkdir(parents=True, exist_ok=True)
