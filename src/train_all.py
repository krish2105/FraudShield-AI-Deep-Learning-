"""
train_all.py
============
The single end-to-end training pipeline for FraudShield AI.

    load -> clean -> cap -> TEMPORAL split (past->future) -> fit scaler on train
    -> masked sequences -> train {Dense, LSTM, GRU, CNN, Autoencoder}
    -> calibrate probabilities -> evaluate (fraud-appropriate metrics) -> save

Phase-1 upgrades over the original pipeline:
  * **Temporal split** (train on the past, test on the future) instead of a
    random/stratified split — the only honest way to evaluate fraud detection.
  * **Probability calibration** (isotonic, on a held-out calibration slice) so
    the 0.30 / 0.70 risk bands are meaningful.
  * **Fraud-appropriate metrics**: recall@precision90, precision@recall90,
    best-F1 threshold, calibration curve, and a reliability note that flags
    when the test set is too small to trust.

Saved artifacts (everything the dashboard / API needs):
    models/*.pt                       trained PyTorch models
    models/scaler.pkl                 fitted StandardScaler (train-only fit)
    models/calibrator.pkl             isotonic calibrator for the primary model
    models/feature_columns.pkl        feature order
    models/inference_artifacts.json   primary model + AE threshold + split info
    reports/metrics.json              per-model metrics (calibrated)
    reports/model_comparison.csv      comparison table
    reports/curves.json               ROC / PR / threshold / calibration / history

Run standalone (uses data/paysim.csv if present, else the sample):
    python src/train_all.py
"""

from __future__ import annotations

from typing import Dict, Tuple

import numpy as np
import pandas as pd

try:
    from . import config
    from . import dl_models as dl
    from . import evaluate_model as ev
    from . import calibration as cal
    from .data_loader import load_data
    from .preprocessing import clean_data, fit_scaler, transform_with_scaler, save_scaler
    from .sequence_builder import build_padded_sequences, stratified_split
    from .utils import log, write_json, set_seeds
except ImportError:  # pragma: no cover
    import sys
    from pathlib import Path
    sys.path.append(str(Path(__file__).resolve().parents[1]))
    from src import config
    from src import dl_models as dl
    from src import evaluate_model as ev
    from src import calibration as cal
    from src.data_loader import load_data
    from src.preprocessing import clean_data, fit_scaler, transform_with_scaler, save_scaler
    from src.sequence_builder import build_padded_sequences, stratified_split
    from src.utils import log, write_json, set_seeds

# Cap training rows so a multi-million-row file trains in minutes and fits in
# memory (we keep ALL fraud and fill with genuine). Sample data is unaffected.
TRAIN_MAX_ROWS = 150_000
CALIB_SIZE = 0.15            # fraction of the TRAIN block held out for calibration

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


def _cap(df: pd.DataFrame, max_rows: int | None) -> pd.DataFrame:
    """Keep every fraud row, fill the rest with genuine, to bound train cost."""
    if max_rows and len(df) > max_rows and "isFraud" in df.columns:
        fraud = df[df["isFraud"] == 1]
        n_gen = max(0, max_rows - len(fraud))
        genuine = df[df["isFraud"] == 0].sample(
            min((df["isFraud"] == 0).sum(), n_gen), random_state=config.RANDOM_SEED)
        df = pd.concat([fraud, genuine])
        log(f"Capped training data to {len(df):,} rows ({len(fraud):,} fraud kept).")
    return df


def _seqs(scaled: pd.DataFrame, df: pd.DataFrame):
    """Build masked padded sequences from a scaled feature frame + its raw df."""
    scaled = scaled.reset_index(drop=True)
    df = df.reset_index(drop=True)
    X, y, lengths, idx = build_padded_sequences(
        scaled, df["isFraud"], df["nameOrig"], df["step"],
        sequence_length=config.SEQUENCE_LENGTH)
    return X, y, lengths


def prepare_temporal(df: pd.DataFrame, max_rows: int | None = TRAIN_MAX_ROWS,
                     test_size: float = config.TEST_SIZE):
    """Clean -> cap -> TEMPORAL split -> fit scaler on the train block only ->
    build sequences for fit / calibration / test blocks.

    Returns (scaler, fit, calib, test) where each split is (X, y, lengths),
    plus a bool `temporal` indicating whether a true time split was usable.
    """
    df = clean_data(df)
    if config.SCOPE_TO_FRAUD_TYPES:
        df = df[df["type"].isin(config.FRAUD_TYPES)]
    df = _cap(df, max_rows)

    # Order globally by time so the split is genuinely past -> future.
    df = df.sort_values("step").reset_index(drop=True)
    n = len(df)
    cut_test = max(1, int(n * (1 - test_size)))
    train_df = df.iloc[:cut_test]
    test_df = df.iloc[cut_test:]

    # Hold out the tail of TRAIN for calibration (still strictly before test).
    cut_cal = max(1, int(len(train_df) * (1 - CALIB_SIZE)))
    fit_df = train_df.iloc[:cut_cal]
    cal_df = train_df.iloc[cut_cal:]

    # Fit the scaler on the FIT block only (no leakage from calib/test).
    scaler, X_fit_scaled = fit_scaler(fit_df)
    X_cal_scaled = transform_with_scaler(cal_df, scaler)
    X_te_scaled = transform_with_scaler(test_df, scaler)

    fit = _seqs(X_fit_scaled, fit_df)
    calib = _seqs(X_cal_scaled, cal_df)
    test = _seqs(X_te_scaled, test_df)

    temporal = test[1].sum() > 0 and fit[1].sum() > 0 and calib[1].sum() > 0
    return scaler, fit, calib, test, temporal


def prepare_stratified(df: pd.DataFrame, max_rows: int | None = TRAIN_MAX_ROWS):
    """Fallback for tiny data: stratified split so fraud appears in every block.
    Used automatically when a temporal split would leave a block fraud-free."""
    df = clean_data(df)
    if config.SCOPE_TO_FRAUD_TYPES:
        df = df[df["type"].isin(config.FRAUD_TYPES)]
    df = _cap(df, max_rows)
    sort_cols = [c for c in ["nameOrig", "step"] if c in df.columns]
    df = df.sort_values(sort_cols).reset_index(drop=True)

    scaler, X_scaled = fit_scaler(df)
    X, y, lengths, _ = build_padded_sequences(
        X_scaled.reset_index(drop=True), df["isFraud"], df["nameOrig"], df["step"],
        sequence_length=config.SEQUENCE_LENGTH)
    # split into fit / calib / test
    (X_tr, X_te), (l_tr, l_te), (y_tr, y_te) = stratified_split(
        X, lengths, y=y, test_size=config.TEST_SIZE)
    (X_fit, X_cal), (l_fit, l_cal), (y_fit, y_cal) = stratified_split(
        X_tr, l_tr, y=y_tr, test_size=CALIB_SIZE)
    return scaler, (X_fit, y_fit, l_fit), (X_cal, y_cal, l_cal), (X_te, y_te, l_te), False


def train_all(epochs: int = config.EPOCHS) -> Dict:
    """Run the full pipeline and persist everything. Returns a summary dict."""
    set_seeds()
    df, source = load_data()
    log(f"Training on data source = {source}  ({len(df):,} raw rows)")

    scaler, fit, calib, test, temporal = prepare_temporal(df)
    if not temporal:
        log("Temporal split left a block without fraud — falling back to a "
            "stratified split so every metric is well-defined.")
        scaler, fit, calib, test, temporal = prepare_stratified(df)

    X_fit, y_fit, l_fit = fit
    X_cal, y_cal, l_cal = calib
    X_te, y_te, l_te = test
    if len(X_fit) == 0 or y_fit.sum() == 0 or len(X_te) == 0:
        raise RuntimeError("Not enough data / no fraud examples to train on.")

    split_kind = "temporal (past→future)" if temporal else "stratified (small-data fallback)"
    log(f"Split = {split_kind}  fit={len(X_fit):,}  calib={len(X_cal):,}  "
        f"test={len(X_te):,}  fraud(test)={int(y_te.sum())}  "
        f"seq_len={X_fit.shape[1]}  feats={X_fit.shape[2]}")

    seq_len, n_feats = X_fit.shape[1], X_fit.shape[2]
    metrics: Dict = {}
    curves: Dict = {"models": {}}
    comparison = []
    calibrators: Dict = {}

    # ---- supervised models ----------------------------------------------
    for name in SUPERVISED:
        model, history = dl.train_classifier(
            name, X_fit, y_fit, l_fit, X_cal, y_cal, l_cal, epochs=epochs)

        # Calibrate on the held-out calibration block, then score test.
        cal_prob = dl.predict_proba(model, X_cal, l_cal)
        calibrator = cal.fit_calibrator(y_cal, cal_prob)
        calibrators[name] = calibrator
        raw_prob = dl.predict_proba(model, X_te, l_te)
        prob = cal.apply_calibrator(calibrator, raw_prob)

        m = ev.compute_metrics(y_te, prob)
        m.update(ev.operating_points(y_te, prob))
        metrics[name] = m
        rp = ev.roc_pr_points(y_te, prob)
        curves["models"][name] = {
            **rp,
            "threshold": ev.threshold_sweep(y_te, prob),
            "score_dist": ev.score_distribution(y_te, prob),
            "calibration": ev.calibration_points(y_te, prob),
            "history": history,
        }
        comparison.append({"model": DISPLAY[name],
                           **{k: m[k] for k in ["accuracy", "precision", "recall",
                                                "f1", "roc_auc", "pr_auc"]},
                           "recall_at_p90": m.get("recall_at_p90")})
        dl.save_model(model, name, MODEL_PATHS[name], seq_len, n_feats)

    # ---- autoencoder (unsupervised) -------------------------------------
    ae, ae_hist = dl.train_autoencoder(X_fit, y_fit, l_fit, X_cal, y_cal, l_cal, epochs=epochs)
    err_fit = dl.reconstruction_error(ae, X_fit, l_fit)
    err_te = dl.reconstruction_error(ae, X_te, l_te)
    genuine_err = err_fit[np.asarray(y_fit) == 0]
    ae_threshold = float(np.percentile(genuine_err, config.AE_THRESHOLD_PERCENTILE)) \
        if len(genuine_err) else float(np.percentile(err_fit, 99))
    ae_metrics = ev.compute_metrics(y_te, (err_te >= ae_threshold).astype(float), threshold=0.5)
    ae_rp = ev.roc_pr_points(y_te, err_te)
    metrics["autoencoder"] = {**ae_metrics, "roc_auc": ae_rp["roc_auc"], "pr_auc": ae_rp["pr_auc"]}
    emax = float(np.percentile(err_te, 99)) or 1.0
    edges = np.linspace(0, emax, 21)
    g_hist, _ = np.histogram(err_te[np.asarray(y_te) == 0], bins=edges)
    f_hist, _ = np.histogram(err_te[np.asarray(y_te) == 1], bins=edges)
    curves["autoencoder"] = {
        "history": ae_hist, "threshold": round(ae_threshold, 5),
        "recon_dist": [{"error": round(float((edges[i] + edges[i + 1]) / 2), 5),
                        "genuine": int(g_hist[i]), "fraud": int(f_hist[i])}
                       for i in range(len(edges) - 1)],
        **ae_rp,
    }
    comparison.append({"model": DISPLAY["autoencoder"],
                       **{k: metrics["autoencoder"][k] for k in
                          ["accuracy", "precision", "recall", "f1", "roc_auc", "pr_auc"]}})
    dl.save_model(ae, "autoencoder", MODEL_PATHS["autoencoder"], seq_len, n_feats)

    # ---- pick the primary model (best PR-AUC; LSTM wins ties) -----------
    def pr(n):
        v = metrics[n].get("pr_auc")
        return v if isinstance(v, (int, float)) else -1
    primary = max(SUPERVISED, key=lambda n: (pr(n), n == "lstm"))
    curves["primary"] = primary
    curves["confusion_matrix"] = metrics[primary].get("confusion_matrix")

    # Persist the PRIMARY model's calibrator so inference uses the same mapping.
    cal.save_calibrator(calibrators.get(primary))

    # ---- reliability + persist -----------------------------------------
    rel = ev.reliability_note(int(len(X_te)), int(y_te.sum()))
    save_scaler(scaler)
    metrics["status"] = "TRAINED"
    metrics["primary"] = primary
    metrics["data_source"] = source
    metrics["split"] = split_kind
    metrics["calibrated"] = True
    metrics["reliability"] = rel
    metrics["note"] = ("Trained on REAL PaySim data." if source == "real" else
                       "Trained on SYNTHETIC data — for genuine results use the "
                       "real PaySim dataset (src/download_paysim.py).")
    ev.save_metrics(metrics, data_source=source)
    ev.save_comparison(comparison)
    ev.save_curves(curves)
    write_json(config.ARTIFACTS_PATH, {
        "primary": primary, "ae_threshold": ae_threshold,
        "seq_len": int(seq_len), "n_features": int(n_feats),
        "data_source": source, "status": "TRAINED",
        "split": split_kind, "calibrated": True,
    })

    # ---- experiment tracking (optional MLflow) -------------------------
    try:
        from . import tracking
    except ImportError:  # pragma: no cover
        from src import tracking
    tracking.log_training_run(
        params={"epochs": epochs, "seq_len": seq_len, "n_features": n_feats,
                "split": split_kind, "source": source, "max_rows": TRAIN_MAX_ROWS},
        metrics={k: metrics[k] for k in SUPERVISED + ["autoencoder"]},
        primary=primary)

    log(f"Done. Primary = {primary} | PR-AUC={metrics[primary].get('pr_auc')} | "
        f"recall={metrics[primary].get('recall')} | "
        f"recall@P90={metrics[primary].get('recall_at_p90')}")
    log(rel["message"])
    return {"primary": primary, "source": source, "metrics": metrics,
            "n_test": int(len(X_te)), "reliability": rel}


if __name__ == "__main__":
    train_all()
