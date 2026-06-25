"""
train_dense_nn.py
=================
Backwards-compatible wrapper for the Dense baseline (now PyTorch, via
`dl_models`). See train_lstm.py for the rationale (TensorFlow segfaults on this
stack). Prefer `src/train_all.py` or `src/dl_models.py` directly.
"""

from __future__ import annotations

try:
    from . import config
    from . import dl_models as dl
except ImportError:  # pragma: no cover
    import sys
    from pathlib import Path
    sys.path.append(str(Path(__file__).resolve().parents[1]))
    from src import config
    from src import dl_models as dl


def train_dense(X_tr, y_tr, len_tr, X_val, y_val, len_val, epochs=config.EPOCHS):
    """Train the Dense (flatten) baseline. Returns (model, history)."""
    return dl.train_classifier("dense_nn", X_tr, y_tr, len_tr, X_val, y_val, len_val, epochs=epochs)
