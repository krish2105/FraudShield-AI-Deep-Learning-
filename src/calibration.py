"""
calibration.py
==============
Probability calibration (Phase 1).

A model's raw sigmoid output is not necessarily a true probability — a score of
0.7 should mean "70% of such transactions are fraud", but uncalibrated models
are often over/under-confident. The risk bands (0.30 / 0.70) are only meaningful
if the score is calibrated.

We fit an **isotonic regression** calibrator on a held-out calibration slice
(never the test set) and persist it so inference applies the SAME mapping.
"""

from __future__ import annotations

from pathlib import Path

import joblib
import numpy as np
from sklearn.isotonic import IsotonicRegression

try:
    from . import config
    from .utils import log
except ImportError:  # pragma: no cover
    import sys
    sys.path.append(str(Path(__file__).resolve().parents[1]))
    from src import config
    from src.utils import log

CALIBRATOR_PATH = config.MODELS_DIR / "calibrator.pkl"


def fit_calibrator(y_true, y_prob) -> IsotonicRegression | None:
    """Fit isotonic calibration; returns None if a single class is present."""
    y_true = np.asarray(y_true).astype(float).ravel()
    y_prob = np.asarray(y_prob).astype(float).ravel()
    if len(np.unique(y_true)) < 2:
        return None
    iso = IsotonicRegression(out_of_bounds="clip", y_min=0.0, y_max=1.0)
    iso.fit(y_prob, y_true)
    return iso


def apply_calibrator(cal: IsotonicRegression | None, y_prob) -> np.ndarray:
    y_prob = np.asarray(y_prob).astype(float).ravel()
    if cal is None:
        return y_prob
    return np.clip(cal.predict(y_prob), 0.0, 1.0)


def save_calibrator(cal: IsotonicRegression | None, path: Path = CALIBRATOR_PATH) -> None:
    config.ensure_dirs()
    if cal is None:
        if Path(path).exists():
            Path(path).unlink()
        return
    joblib.dump(cal, path)
    log(f"Saved probability calibrator -> {path}")


def load_calibrator(path: Path = CALIBRATOR_PATH):
    return joblib.load(path) if Path(path).exists() else None
