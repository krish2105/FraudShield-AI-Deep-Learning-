"""
dl_models.py
============
The deep-learning toolkit for FraudShield AI — implemented in **PyTorch**.

Why PyTorch: on this stack (Apple Silicon, Python 3.13, NumPy 2.x) TensorFlow
segfaults on import. PyTorch is rock-solid here, so the models actually train.
The architectures ("LSTM/RNN") are unchanged — only the framework underneath.

Models (each matched to a fraud sub-use-case):
    DenseBaseline   - flattens the sequence, ignores order (honest benchmark)
    LSTMClassifier  - masked, packed LSTM (the hero sequence model)
    GRUClassifier   - lighter recurrent variant
    CNN1DClassifier - 1D-CNN over time (local "spike-then-drain" motifs)
    SequenceAutoencoder - unsupervised anomaly detector (novel-fraud catcher)

All supervised models share the masked many-to-one sequence tensor
(X: [N, seq_len, n_features], lengths: [N]) and output a fraud probability.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Tuple

import numpy as np
import torch
import torch.nn as nn
from torch.nn.utils.rnn import pack_padded_sequence
from sklearn.metrics import average_precision_score, recall_score

try:
    from . import config
    from .utils import log, set_seeds
except ImportError:  # pragma: no cover
    import sys
    sys.path.append(str(Path(__file__).resolve().parents[1]))
    from src import config
    from src.utils import log, set_seeds


def get_device() -> torch.device:
    """CPU by default — small data, fully deterministic, no MPS edge cases."""
    return torch.device("cpu")


# ---------------------------------------------------------------------------
# Loss
# ---------------------------------------------------------------------------
class FocalLoss(nn.Module):
    """Binary focal loss — down-weights easy negatives so the rare fraud class
    drives learning. pos_weight further boosts the positive class."""

    def __init__(self, gamma: float = config.FOCAL_GAMMA, pos_weight: float = 1.0):
        super().__init__()
        self.gamma = gamma
        self.pos_weight = pos_weight

    def forward(self, logits, targets):
        p = torch.sigmoid(logits)
        eps = 1e-6
        p = p.clamp(eps, 1 - eps)
        # focal weighting
        loss_pos = -self.pos_weight * (1 - p) ** self.gamma * targets * torch.log(p)
        loss_neg = -p ** self.gamma * (1 - targets) * torch.log(1 - p)
        return (loss_pos + loss_neg).mean()


# ---------------------------------------------------------------------------
# Model definitions
# ---------------------------------------------------------------------------
class DenseBaseline(nn.Module):
    """Flatten the whole sequence and classify — ignores time order."""

    def __init__(self, seq_len: int, n_features: int):
        super().__init__()
        self.net = nn.Sequential(
            nn.Flatten(),
            nn.Linear(seq_len * n_features, 64), nn.ReLU(),
            nn.Dropout(config.DROPOUT_RATE),
            nn.Linear(64, config.DENSE_UNITS), nn.ReLU(),
            nn.Linear(config.DENSE_UNITS, 1),
        )

    def forward(self, x, lengths=None):
        return self.net(x).squeeze(-1)


class _RNNClassifier(nn.Module):
    """Shared masked recurrent classifier (LSTM or GRU)."""

    def __init__(self, seq_len, n_features, cell="lstm"):
        super().__init__()
        rnn_cls = nn.LSTM if cell == "lstm" else nn.GRU
        self.cell = cell
        self.rnn = rnn_cls(n_features, config.LSTM_UNITS, batch_first=True)
        self.head = nn.Sequential(
            nn.Dropout(config.DROPOUT_RATE),
            nn.Linear(config.LSTM_UNITS, config.DENSE_UNITS), nn.ReLU(),
            nn.Linear(config.DENSE_UNITS, 1),
        )

    def forward(self, x, lengths):
        # Pack so padding is ignored; h is the state after the LAST real step.
        lengths = lengths.cpu().clamp(min=1)
        packed = pack_padded_sequence(x, lengths, batch_first=True, enforce_sorted=False)
        if self.cell == "lstm":
            _, (h, _) = self.rnn(packed)
        else:
            _, h = self.rnn(packed)
        return self.head(h[-1]).squeeze(-1)


class LSTMClassifier(_RNNClassifier):
    def __init__(self, seq_len, n_features):
        super().__init__(seq_len, n_features, cell="lstm")


class GRUClassifier(_RNNClassifier):
    def __init__(self, seq_len, n_features):
        super().__init__(seq_len, n_features, cell="gru")


class CNN1DClassifier(nn.Module):
    """1D convolution over time — detects short local patterns in the window."""

    def __init__(self, seq_len, n_features):
        super().__init__()
        self.conv1 = nn.Conv1d(n_features, config.CNN_FILTERS, config.CNN_KERNEL, padding=1)
        self.conv2 = nn.Conv1d(config.CNN_FILTERS, config.CNN_FILTERS, config.CNN_KERNEL, padding=1)
        self.act = nn.ReLU()
        self.drop = nn.Dropout(config.DROPOUT_RATE)
        self.head = nn.Sequential(
            nn.Linear(config.CNN_FILTERS, config.DENSE_UNITS), nn.ReLU(),
            nn.Linear(config.DENSE_UNITS, 1),
        )

    def forward(self, x, lengths):
        # x: [B, seq, feat] -> [B, feat, seq]
        z = x.transpose(1, 2)
        z = self.act(self.conv1(z))
        z = self.drop(self.act(self.conv2(z)))           # [B, C, seq]
        # masked mean over the real timesteps only
        seq = x.size(1)
        ar = torch.arange(seq, device=x.device).unsqueeze(0)       # [1, seq]
        mask = (ar < lengths.unsqueeze(1)).float().unsqueeze(1)    # [B,1,seq]
        summed = (z * mask).sum(dim=2)
        pooled = summed / mask.sum(dim=2).clamp(min=1)             # [B, C]
        return self.head(pooled).squeeze(-1)


class SequenceAutoencoder(nn.Module):
    """Tabular autoencoder on the CURRENT transaction's feature vector.

    Trained on genuine traffic only; a large reconstruction error flags an
    anomaly (possible novel fraud). Returns the reconstruction, not a class.
    """

    def __init__(self, seq_len, n_features):
        super().__init__()
        self.n_features = n_features
        self.encoder = nn.Sequential(
            nn.Linear(n_features, config.AE_HIDDEN), nn.ReLU(),
            nn.Linear(config.AE_HIDDEN, config.AE_LATENT_DIM), nn.ReLU(),
        )
        self.decoder = nn.Sequential(
            nn.Linear(config.AE_LATENT_DIM, config.AE_HIDDEN), nn.ReLU(),
            nn.Linear(config.AE_HIDDEN, n_features),
        )

    @staticmethod
    def current_step(x, lengths):
        """Pick each window's last REAL timestep (the transaction being scored)."""
        idx = (lengths - 1).clamp(min=0).view(-1, 1, 1).expand(-1, 1, x.size(2))
        return x.gather(1, idx).squeeze(1)               # [B, feat]

    def forward(self, x, lengths):
        cur = self.current_step(x, lengths)
        z = self.encoder(cur)
        recon = self.decoder(z)
        return recon, cur


MODEL_REGISTRY = {
    "dense_nn": DenseBaseline,
    "lstm": LSTMClassifier,
    "gru": GRUClassifier,
    "cnn": CNN1DClassifier,
    "autoencoder": SequenceAutoencoder,
}


# ---------------------------------------------------------------------------
# Training
# ---------------------------------------------------------------------------
def _tensors(X, y, lengths, device):
    return (torch.tensor(X, dtype=torch.float32, device=device),
            torch.tensor(y, dtype=torch.float32, device=device),
            torch.tensor(lengths, dtype=torch.long, device=device))


def _pos_weight(y) -> float:
    y = np.asarray(y)
    n_pos = max(int(y.sum()), 1)
    n_neg = max(len(y) - n_pos, 1)
    return float(n_neg / n_pos)


def train_classifier(name: str, X_tr, y_tr, len_tr, X_val, y_val, len_val,
                     epochs: int = config.EPOCHS, lr: float = config.LEARNING_RATE,
                     batch_size: int = config.BATCH_SIZE) -> Tuple[nn.Module, Dict]:
    """Train one supervised model. Returns (model, history)."""
    set_seeds()
    device = get_device()
    seq_len, n_features = X_tr.shape[1], X_tr.shape[2]
    model = MODEL_REGISTRY[name](seq_len, n_features).to(device)

    pw = _pos_weight(y_tr)
    if config.USE_FOCAL_LOSS:
        criterion = FocalLoss(pos_weight=min(pw, 25.0))
    else:
        criterion = nn.BCEWithLogitsLoss(
            pos_weight=torch.tensor(min(pw, 25.0), device=device))
    opt = torch.optim.Adam(model.parameters(), lr=lr)

    Xt, yt, lt = _tensors(X_tr, y_tr, len_tr, device)
    Xv, yv, lv = _tensors(X_val, y_val, len_val, device)
    n = len(Xt)
    history = {"train_loss": [], "val_loss": [], "val_pr_auc": [], "val_recall": []}

    log(f"Training {name} ({sum(p.numel() for p in model.parameters()):,} params, "
        f"pos_weight={pw:.1f})...")
    for epoch in range(epochs):
        model.train()
        perm = torch.randperm(n)
        ep_loss = 0.0
        for i in range(0, n, batch_size):
            b = perm[i:i + batch_size]
            opt.zero_grad()
            logits = model(Xt[b], lt[b])
            loss = criterion(logits, yt[b])
            loss.backward()
            opt.step()
            ep_loss += loss.item() * len(b)
        # validation
        model.eval()
        with torch.no_grad():
            vlogits = model(Xv, lv)
            vloss = criterion(vlogits, yv).item()
            vprob = torch.sigmoid(vlogits).cpu().numpy()
        yv_np = np.asarray(y_val)
        pr = average_precision_score(yv_np, vprob) if yv_np.sum() and (yv_np == 0).any() else 0.0
        rec = recall_score(yv_np, (vprob >= 0.5).astype(int), zero_division=0)
        history["train_loss"].append(round(ep_loss / n, 5))
        history["val_loss"].append(round(vloss, 5))
        history["val_pr_auc"].append(round(float(pr), 5))
        history["val_recall"].append(round(float(rec), 5))

    model.eval()
    return model.to("cpu"), history


def train_autoencoder(X_tr, y_tr, len_tr, X_val, y_val, len_val,
                      epochs: int = config.EPOCHS, lr: float = config.LEARNING_RATE,
                      batch_size: int = config.BATCH_SIZE) -> Tuple[nn.Module, Dict]:
    """Train the autoencoder on GENUINE transactions only."""
    set_seeds()
    device = get_device()
    seq_len, n_features = X_tr.shape[1], X_tr.shape[2]
    model = SequenceAutoencoder(seq_len, n_features).to(device)

    # genuine-only training data
    genuine = np.asarray(y_tr) == 0
    Xt, _, lt = _tensors(X_tr[genuine], y_tr[genuine], len_tr[genuine], device)
    Xv, _, lv = _tensors(X_val, y_val, len_val, device)
    criterion = nn.MSELoss()
    opt = torch.optim.Adam(model.parameters(), lr=lr)
    n = len(Xt)
    history = {"train_loss": [], "val_loss": []}

    log(f"Training autoencoder on {n:,} genuine transactions...")
    for epoch in range(epochs):
        model.train()
        perm = torch.randperm(n)
        ep = 0.0
        for i in range(0, n, batch_size):
            b = perm[i:i + batch_size]
            opt.zero_grad()
            recon, cur = model(Xt[b], lt[b])
            loss = criterion(recon, cur)
            loss.backward()
            opt.step()
            ep += loss.item() * len(b)
        model.eval()
        with torch.no_grad():
            recon, cur = model(Xv, lv)
            vloss = criterion(recon, cur).item()
        history["train_loss"].append(round(ep / max(n, 1), 6))
        history["val_loss"].append(round(vloss, 6))

    model.eval()
    return model.to("cpu"), history


# ---------------------------------------------------------------------------
# Inference
# ---------------------------------------------------------------------------
@torch.no_grad()
def predict_proba(model: nn.Module, X, lengths, batch_size: int = 1024) -> np.ndarray:
    """Fraud probabilities for a supervised model."""
    model.eval()
    device = get_device()
    model = model.to(device)
    probs = []
    X = np.asarray(X, dtype="float32")
    lengths = np.asarray(lengths)
    for i in range(0, len(X), batch_size):
        xb = torch.tensor(X[i:i + batch_size], dtype=torch.float32, device=device)
        lb = torch.tensor(lengths[i:i + batch_size], dtype=torch.long, device=device)
        logits = model(xb, lb)
        probs.append(torch.sigmoid(logits).cpu().numpy())
    return np.concatenate(probs) if probs else np.array([])


@torch.no_grad()
def reconstruction_error(model: SequenceAutoencoder, X, lengths,
                         batch_size: int = 1024) -> np.ndarray:
    """Per-row reconstruction error (anomaly score) for the autoencoder."""
    model.eval()
    device = get_device()
    model = model.to(device)
    errs = []
    X = np.asarray(X, dtype="float32")
    lengths = np.asarray(lengths)
    for i in range(0, len(X), batch_size):
        xb = torch.tensor(X[i:i + batch_size], dtype=torch.float32, device=device)
        lb = torch.tensor(lengths[i:i + batch_size], dtype=torch.long, device=device)
        recon, cur = model(xb, lb)
        errs.append(((recon - cur) ** 2).mean(dim=1).cpu().numpy())
    return np.concatenate(errs) if errs else np.array([])


# ---------------------------------------------------------------------------
# Save / load
# ---------------------------------------------------------------------------
def save_model(model: nn.Module, name: str, path: Path, seq_len: int, n_features: int):
    config.ensure_dirs()
    torch.save({"name": name, "seq_len": seq_len, "n_features": n_features,
                "state_dict": model.state_dict()}, path)
    log(f"Saved {name} -> {path}")


def load_model(path: Path):
    """Load a saved model; returns (model, name) or (None, None) on failure."""
    if not Path(path).exists():
        return None, None
    try:
        ckpt = torch.load(path, map_location="cpu", weights_only=False)
        model = MODEL_REGISTRY[ckpt["name"]](ckpt["seq_len"], ckpt["n_features"])
        model.load_state_dict(ckpt["state_dict"])
        model.eval()
        return model, ckpt["name"]
    except Exception as exc:  # pragma: no cover
        log(f"Could not load model {path}: {exc}")
        return None, None
