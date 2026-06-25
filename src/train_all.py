"""
train_all.py
============
The single end-to-end training pipeline for FraudShield AI.

    load -> clean -> features -> scale -> masked sequences -> stratified split
    -> train {Dense, LSTM, GRU, CNN, Autoencoder} -> evaluate -> save artifacts

Saved artifacts (everything the dashboard / API needs):
    models/*.pt                       trained PyTorch models
    models/scaler.pkl                 fitted StandardScaler
    models/feature_columns.pkl        feature order
    models/inference_artifacts.json   primary model name + AE threshold
    reports/metrics.json              per-model metrics
    reports/model_comparison.csv      comparison table
    reports/curves.json               ROC / PR / threshold / history / score-dist

Run standalone (uses sample data unless data/paysim.csv exists):
    python src/train_all.py
"""

from __future__ import annotations

from typing import Dict

import numpy as np
import pandas as pd

try:
    from . import config
    from . import dl_models as dl
    from . import evaluate_model as ev
    from .data_loader import load_data
    from .feature_engineering import engineer_features
    from .preprocessing import clean_data, fit_scaler, save_scaler
    from .sequence_builder import build_padded_sequences, stratified_split
    from .utils import log, write_json, set_seeds
except ImportError:  # pragma: no cover
    import sys
    from pathlib import Path
    sys.path.append(str(Path(__file__).resolve().parents[1]))
    from src import config
    from src import dl_models as dl
    from src import evaluate_model as ev
    from src.data_loader import load_data
    from src.feature_engineering import engineer_features
    from src.preprocessing import clean_data, fit_scaler, save_scaler
    from src.sequence_builder import build_padded_sequences, stratified_split
    from src.utils import log, write_json, set_seeds

# Cap training rows so the full 6.3M-row PaySim file trains in seconds and fits
# in memory (we keep ALL fraud and fill with genuine). Sample data is unaffected.
TRAIN_MAX_ROWS = 150000

SUPERVISED = ["dense_nn", "lstm", "gru", "cnn"]
MODEL_PATHS = {
    "dense_nn": config.DENSE_MODEL_PATH,
    "lstm": config.LSTM_MODEL_PATH,
    "gru": config.GRU_MODEL_PATH,
    "cnn": config.CNN_MODEL_PATH,
    "autoencoder": config.AUTOENCODER_MODEL_PATH,
}
DISPLAY = {"dense_nn": "Dense NN (baseline)", "lstm": "LSTM", "gru": "GRU",
           "cnn": "1D-CNN", "autoencoder": "Autoencoder"}


def prepare(df: pd.DataFrame, max_samples: int | None = None,
            max_rows: int | None = TRAIN_MAX_ROWS):
    """Clean -> (cap rows) -> features -> scale -> masked padded sequences -> split."""
    df = clean_data(df)
    if config.SCOPE_TO_FRAUD_TYPES:
        df = df[df["type"].isin(config.FRAUD_TYPES)]

    # Cap very large datasets BEFORE building sequences (memory + speed).
    # Keep every fraud row, fill the rest with genuine, then restore per-account
    # time order so sequences are still meaningful.
    if max_rows and len(df) > max_rows and "isFraud" in df.columns:
        fraud = df[df["isFraud"] == 1]
        n_gen = max(0, max_rows - len(fraud))
        genuine = df[df["isFraud"] == 0].sample(
            min((df["isFraud"] == 0).sum(), n_gen), random_state=config.RANDOM_SEED)
        df = pd.concat([fraud, genuine])
        sort_cols = [c for c in ["nameOrig", "step"] if c in df.columns]
        if sort_cols:
            df = df.sort_values(sort_cols)
        log(f"Capped training data to {len(df):,} rows "
            f"({len(fraud):,} fraud kept) for tractable training.")

    df = df.reset_index(drop=True)

    scaler, X_scaled = fit_scaler(df)
    X_scaled = X_scaled.reset_index(drop=True)

    X, y, lengths, idx = build_padded_sequences(
        X_scaled, df["isFraud"], df["nameOrig"], df["step"],
        sequence_length=config.SEQUENCE_LENGTH, max_samples=max_samples,
    )
    return scaler, X, y, lengths, idx


def train_all(epochs: int = config.EPOCHS, max_samples: int | None = None) -> Dict:
    """Run the full pipeline and persist everything. Returns a summary dict."""
    set_seeds()
    df, source = load_data()
    log(f"Training on data source = {source}")

    scaler, X, y, lengths, idx = prepare(df, max_samples=max_samples)
    if len(X) == 0 or y.sum() == 0:
        raise RuntimeError("Not enough data / no fraud examples to train on.")

    (X_tr, X_te), (len_tr, len_te), (y_tr, y_te) = stratified_split(
        X, lengths, y=y, test_size=config.TEST_SIZE)
    log(f"Sequences: total={len(X)}  train={len(X_tr)}  test={len(X_te)}  "
        f"fraud(test)={int(y_te.sum())}  seq_len={X.shape[1]}  feats={X.shape[2]}")

    metrics: Dict = {}
    curves: Dict = {"models": {}}
    comparison = []

    # ---- supervised models ----------------------------------------------
    for name in SUPERVISED:
        model, history = dl.train_classifier(
            name, X_tr, y_tr, len_tr, X_te, y_te, len_te, epochs=epochs)
        prob = dl.predict_proba(model, X_te, len_te)
        m = ev.compute_metrics(y_te, prob)
        metrics[name] = m
        rp = ev.roc_pr_points(y_te, prob)
        curves["models"][name] = {
            **rp,
            "threshold": ev.threshold_sweep(y_te, prob),
            "score_dist": ev.score_distribution(y_te, prob),
            "history": history,
        }
        comparison.append({"model": DISPLAY[name],
                           **{k: m[k] for k in ["accuracy", "precision", "recall",
                                                "f1", "roc_auc", "pr_auc"]}})
        dl.save_model(model, name, MODEL_PATHS[name], X.shape[1], X.shape[2])

    # ---- autoencoder (unsupervised) -------------------------------------
    ae, ae_hist = dl.train_autoencoder(X_tr, y_tr, len_tr, X_te, y_te, len_te, epochs=epochs)
    err_tr = dl.reconstruction_error(ae, X_tr, len_tr)
    err_te = dl.reconstruction_error(ae, X_te, len_te)
    genuine_err = err_tr[np.asarray(y_tr) == 0]
    ae_threshold = float(np.percentile(genuine_err, config.AE_THRESHOLD_PERCENTILE)) \
        if len(genuine_err) else float(np.percentile(err_tr, 99))
    # treat reconstruction error as the anomaly score
    ae_metrics = ev.compute_metrics(y_te, (err_te >= ae_threshold).astype(float),
                                    threshold=0.5)
    ae_rp = ev.roc_pr_points(y_te, err_te)            # ranking quality of the error
    metrics["autoencoder"] = {**ae_metrics, "roc_auc": ae_rp["roc_auc"],
                              "pr_auc": ae_rp["pr_auc"]}
    # reconstruction-error distribution (genuine vs fraud)
    emax = float(np.percentile(err_te, 99)) or 1.0
    edges = np.linspace(0, emax, 21)
    g_hist, _ = np.histogram(err_te[np.asarray(y_te) == 0], bins=edges)
    f_hist, _ = np.histogram(err_te[np.asarray(y_te) == 1], bins=edges)
    curves["autoencoder"] = {
        "history": ae_hist,
        "threshold": round(ae_threshold, 5),
        "recon_dist": [{"error": round(float((edges[i] + edges[i + 1]) / 2), 5),
                        "genuine": int(g_hist[i]), "fraud": int(f_hist[i])}
                       for i in range(len(edges) - 1)],
        **ae_rp,
    }
    comparison.append({"model": DISPLAY["autoencoder"],
                       **{k: metrics["autoencoder"][k] for k in
                          ["accuracy", "precision", "recall", "f1", "roc_auc", "pr_auc"]}})
    dl.save_model(ae, "autoencoder", MODEL_PATHS["autoencoder"], X.shape[1], X.shape[2])

    # ---- pick the primary model (best PR-AUC; LSTM wins ties) -----------
    def pr(n):
        v = metrics[n].get("pr_auc")
        return v if isinstance(v, (int, float)) else -1
    primary = max(SUPERVISED, key=lambda n: (pr(n), n == "lstm"))
    curves["primary"] = primary
    curves["confusion_matrix"] = metrics[primary].get("confusion_matrix")

    # ---- persist --------------------------------------------------------
    save_scaler(scaler)
    metrics["status"] = "TRAINED"
    metrics["primary"] = primary
    metrics["data_source"] = source
    metrics["note"] = ("Trained on REAL PaySim data." if source == "real" else
                       "Trained on SYNTHETIC sample data — demo only. Re-run on the "
                       "real PaySim dataset for final numbers.")
    ev.save_metrics(metrics, data_source=source)
    ev.save_comparison(comparison)
    ev.save_curves(curves)
    write_json(config.ARTIFACTS_PATH, {
        "primary": primary,
        "ae_threshold": ae_threshold,
        "seq_len": int(X.shape[1]),
        "n_features": int(X.shape[2]),
        "data_source": source,
        "status": "TRAINED",
    })

    log(f"Done. Primary model = {primary} "
        f"(PR-AUC={metrics[primary].get('pr_auc')}, recall={metrics[primary].get('recall')})")
    return {"primary": primary, "source": source, "metrics": metrics,
            "n_test": int(len(X_te))}


if __name__ == "__main__":
    train_all()
