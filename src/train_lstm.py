"""
train_lstm.py
=============
Backwards-compatible thin wrappers around the PyTorch toolkit in `dl_models`.

Historically this module used TensorFlow/Keras. The project now uses PyTorch
(TensorFlow segfaults on this Apple-Silicon / Python 3.13 stack). These helpers
keep the old import surface working and delegate to `dl_models`.

Prefer `src/train_all.py` for the full pipeline, or `src/dl_models.py` directly.
"""

from __future__ import annotations

import numpy as np

try:
    from . import config
    from . import dl_models as dl
except ImportError:  # pragma: no cover
    import sys
    from pathlib import Path
    sys.path.append(str(Path(__file__).resolve().parents[1]))
    from src import config
    from src import dl_models as dl


def compute_class_weights(y) -> dict:
    """{class: weight} dict that up-weights the rare fraud class."""
    y = np.asarray(y).astype(int)
    n, n_pos = len(y), int(y.sum())
    n_neg = n - n_pos
    if n_pos == 0 or n_neg == 0:
        return {0: 1.0, 1: 1.0}
    return {0: n / (2.0 * n_neg), 1: n / (2.0 * n_pos)}


def train_lstm(X_tr, y_tr, len_tr, X_val, y_val, len_val, epochs=config.EPOCHS):
    """Train the LSTM. Returns (model, history)."""
    return dl.train_classifier("lstm", X_tr, y_tr, len_tr, X_val, y_val, len_val, epochs=epochs)


def train_gru(X_tr, y_tr, len_tr, X_val, y_val, len_val, epochs=config.EPOCHS):
    """Train the GRU. Returns (model, history)."""
    return dl.train_classifier("gru", X_tr, y_tr, len_tr, X_val, y_val, len_val, epochs=epochs)


def train_cnn(X_tr, y_tr, len_tr, X_val, y_val, len_val, epochs=config.EPOCHS):
    """Train the 1D-CNN. Returns (model, history)."""
    return dl.train_classifier("cnn", X_tr, y_tr, len_tr, X_val, y_val, len_val, epochs=epochs)
