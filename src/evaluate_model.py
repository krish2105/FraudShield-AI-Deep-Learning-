"""
evaluate_model.py
=================
Computes the evaluation metrics used throughout the project and saves them
to reports/metrics.json and reports/model_comparison.csv.

Metrics: accuracy, precision, recall, F1, ROC-AUC, PR-AUC, confusion matrix.

Why recall matters most here: missing a REAL fraud (a false negative) is
far more expensive than reviewing a genuine transaction by mistake.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict

import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_auc_score,
    roc_curve,
)

try:
    from . import config
    from .utils import write_json, log
except ImportError:  # pragma: no cover
    import sys

    sys.path.append(str(Path(__file__).resolve().parents[1]))
    from src import config
    from src.utils import write_json, log


def compute_metrics(y_true, y_prob, threshold: float = 0.5) -> Dict:
    """Compute the standard classification metrics from probabilities."""
    y_true = np.asarray(y_true).astype(int)
    y_prob = np.asarray(y_prob).astype(float).ravel()
    y_pred = (y_prob >= threshold).astype(int)

    # ROC-AUC / PR-AUC need both classes present; guard against single-class.
    has_both = len(np.unique(y_true)) > 1
    metrics = {
        "accuracy": round(float(accuracy_score(y_true, y_pred)), 4),
        "precision": round(float(precision_score(y_true, y_pred, zero_division=0)), 4),
        "recall": round(float(recall_score(y_true, y_pred, zero_division=0)), 4),
        "f1": round(float(f1_score(y_true, y_pred, zero_division=0)), 4),
        "roc_auc": round(float(roc_auc_score(y_true, y_prob)), 4) if has_both else None,
        "pr_auc": round(float(average_precision_score(y_true, y_prob)), 4) if has_both else None,
        "confusion_matrix": confusion_matrix(y_true, y_pred).tolist(),
        "threshold": threshold,
        "n_samples": int(len(y_true)),
        "n_fraud": int(y_true.sum()),
    }
    return metrics


def _downsample(xs, ys, n=80):
    """Reduce a curve to ~n evenly spaced points (smaller JSON, smooth charts)."""
    xs = np.asarray(xs); ys = np.asarray(ys)
    if len(xs) <= n:
        return xs, ys
    idx = np.linspace(0, len(xs) - 1, n).astype(int)
    return xs[idx], ys[idx]


def roc_pr_points(y_true, y_prob) -> Dict:
    """ROC and Precision-Recall curve points (downsampled) for charts."""
    y_true = np.asarray(y_true).astype(int)
    y_prob = np.asarray(y_prob).astype(float).ravel()
    if len(np.unique(y_true)) < 2:
        return {"roc": [], "pr": [], "roc_auc": None, "pr_auc": None}
    fpr, tpr, _ = roc_curve(y_true, y_prob)
    prec, rec, _ = precision_recall_curve(y_true, y_prob)
    fpr_d, tpr_d = _downsample(fpr, tpr)
    rec_d, prec_d = _downsample(rec, prec)
    return {
        "roc": [{"fpr": round(float(a), 4), "tpr": round(float(b), 4)}
                for a, b in zip(fpr_d, tpr_d)],
        "pr": [{"recall": round(float(a), 4), "precision": round(float(b), 4)}
               for a, b in zip(rec_d, prec_d)],
        "roc_auc": round(float(roc_auc_score(y_true, y_prob)), 4),
        "pr_auc": round(float(average_precision_score(y_true, y_prob)), 4),
    }


def threshold_sweep(y_true, y_prob, n_points: int = 41) -> list:
    """Precision / recall / F1 at thresholds from 0..1 (for the sweep chart)."""
    y_true = np.asarray(y_true).astype(int)
    y_prob = np.asarray(y_prob).astype(float).ravel()
    out = []
    for t in np.linspace(0, 1, n_points):
        pred = (y_prob >= t).astype(int)
        out.append({
            "threshold": round(float(t), 3),
            "precision": round(float(precision_score(y_true, pred, zero_division=0)), 4),
            "recall": round(float(recall_score(y_true, pred, zero_division=0)), 4),
            "f1": round(float(f1_score(y_true, pred, zero_division=0)), 4),
        })
    return out


def score_distribution(y_true, y_prob, bins: int = 20) -> list:
    """Histogram of fraud scores split by genuine vs fraud (separability chart)."""
    y_true = np.asarray(y_true).astype(int)
    y_prob = np.asarray(y_prob).astype(float).ravel()
    edges = np.linspace(0, 1, bins + 1)
    g, _ = np.histogram(y_prob[y_true == 0], bins=edges)
    f, _ = np.histogram(y_prob[y_true == 1], bins=edges)
    return [{"score": round(float((edges[i] + edges[i + 1]) / 2), 3),
             "genuine": int(g[i]), "fraud": int(f[i])} for i in range(bins)]


def save_curves(payload: Dict) -> None:
    """Persist ROC/PR/threshold/history/score-distribution data for the UI."""
    config.ensure_dirs()
    write_json(config.CURVES_PATH, payload)
    log(f"Saved evaluation curves -> {config.CURVES_PATH}")


def save_metrics(all_metrics: Dict, data_source: str = "sample") -> None:
    """Save a metrics dictionary to reports/metrics.json with a data note."""
    config.ensure_dirs()
    payload = dict(all_metrics)
    payload["data_source"] = data_source
    if data_source != "real":
        payload["note"] = (
            "Metrics computed on SYNTHETIC sample data - DEMO ONLY. "
            "Update after running on the real PaySim dataset."
        )
    write_json(config.METRICS_PATH, payload)
    log(f"Saved metrics -> {config.METRICS_PATH}")


def save_comparison(rows: list[dict]) -> None:
    """Save a model comparison table to reports/model_comparison.csv.

    Each row should be a dict like:
        {"model": "LSTM", "accuracy": .., "precision": .., "recall": .., ...}
    """
    config.ensure_dirs()
    df = pd.DataFrame(rows)
    df.to_csv(config.MODEL_COMPARISON_PATH, index=False)
    log(f"Saved model comparison -> {config.MODEL_COMPARISON_PATH}")
