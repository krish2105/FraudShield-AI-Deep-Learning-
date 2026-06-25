"""
sequence_builder.py
===================
Turns a flat table of transactions into 3D sequences for the LSTM/RNN.

The core idea (the heart of this project):
    Instead of judging ONE transaction in isolation, we look at a customer's
    last N transactions in order, then ask: is the NEXT transaction fraud?

    Customer C1:  T1 -> T2 -> T3 -> ... -> T10   (input window)
                                              T11  (predict: fraud?)

Output shapes:
    X : (n_samples, SEQUENCE_LENGTH, n_features)
    y : (n_samples,)   fraud label of the transaction AFTER each window
"""

from __future__ import annotations

from pathlib import Path
from typing import Tuple

import numpy as np
import pandas as pd

try:
    from . import config
except ImportError:  # pragma: no cover
    import sys

    sys.path.append(str(Path(__file__).resolve().parents[1]))
    from src import config


def build_sequences(
    feature_df: pd.DataFrame,
    labels: pd.Series,
    groups: pd.Series,
    order: pd.Series,
    sequence_length: int = config.SEQUENCE_LENGTH,
) -> Tuple[np.ndarray, np.ndarray]:
    """Create rolling per-customer sequences.

    Parameters
    ----------
    feature_df : scaled feature matrix (columns = config.FEATURE_COLUMNS)
    labels     : fraud label (0/1) aligned with feature_df rows
    groups     : customer id per row (e.g. nameOrig) - sequences never cross
                 customer boundaries
    order      : sort key within a customer (e.g. step) so time order holds
    sequence_length : window size (default 10)

    Returns
    -------
    X : (samples, sequence_length, n_features)
    y : (samples,)  label of the transaction immediately after each window
    """
    work = feature_df.copy()
    work["_label"] = labels.values
    work["_group"] = groups.values
    work["_order"] = order.values

    # Sort so each customer's transactions are in time order.
    work = work.sort_values(["_group", "_order"]).reset_index(drop=True)

    feature_cols = list(feature_df.columns)
    X_list, y_list = [], []

    # Slide a window of length L within each customer; label = next txn.
    for _, grp in work.groupby("_group", sort=False):
        if len(grp) <= sequence_length:
            continue  # not enough history to form one full window + target
        feats = grp[feature_cols].to_numpy(dtype="float32")
        labs = grp["_label"].to_numpy()
        for i in range(len(grp) - sequence_length):
            X_list.append(feats[i:i + sequence_length])
            y_list.append(labs[i + sequence_length])  # the NEXT transaction

    if not X_list:
        # Degenerate case (very small data): return empty arrays gracefully.
        n_features = len(feature_cols)
        return (np.empty((0, sequence_length, n_features), dtype="float32"),
                np.empty((0,), dtype="int64"))

    X = np.stack(X_list).astype("float32")
    y = np.array(y_list, dtype="int64")
    return X, y


def build_padded_sequences(
    feature_df: pd.DataFrame,
    labels: pd.Series,
    groups: pd.Series,
    order: pd.Series,
    sequence_length: int = config.SEQUENCE_LENGTH,
    max_samples: int | None = None,
    seed: int = config.RANDOM_SEED,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Masked, variable-length, many-to-one sequences (PaySim-real framing).

    For EACH transaction we build a window of up to `sequence_length` of the
    account's own transactions ENDING AT (and including) the current one, in
    chronological order, right-padded with zeros. We also return the true
    length of each window so a PyTorch model can pack/mask the padding.

    This is the realistic framing: at decision time we have the current
    transaction's features plus whatever history exists. Accounts with a single
    transaction yield a length-1 sequence (the model degrades gracefully to a
    per-transaction classifier); accounts with history gain sequence memory.

    Returns
    -------
    X        : (n, sequence_length, n_features)  zero-padded windows
    y        : (n,)                              label of the CURRENT txn
    lengths  : (n,)                              real timesteps per window (>=1)
    idx      : (n,)                              original row index per sample
    """
    work = feature_df.copy()
    work["_label"] = labels.values
    work["_group"] = groups.values
    work["_order"] = order.values
    work["_orig_idx"] = feature_df.index.values
    work = work.sort_values(["_group", "_order"]).reset_index(drop=True)

    feature_cols = list(feature_df.columns)
    n_features = len(feature_cols)

    X_list, y_list, len_list, idx_list = [], [], [], []
    for _, grp in work.groupby("_group", sort=False):
        feats = grp[feature_cols].to_numpy(dtype="float32")
        labs = grp["_label"].to_numpy()
        idxs = grp["_orig_idx"].to_numpy()
        for i in range(len(grp)):
            start = max(0, i - sequence_length + 1)
            window = feats[start:i + 1]                  # oldest..current
            k = window.shape[0]
            padded = np.zeros((sequence_length, n_features), dtype="float32")
            padded[:k] = window                          # right-pad with zeros
            X_list.append(padded)
            y_list.append(labs[i])
            len_list.append(k)
            idx_list.append(idxs[i])

    if not X_list:
        return (np.empty((0, sequence_length, n_features), dtype="float32"),
                np.empty((0,), dtype="int64"),
                np.empty((0,), dtype="int64"),
                np.empty((0,), dtype="int64"))

    X = np.stack(X_list).astype("float32")
    y = np.array(y_list, dtype="int64")
    lengths = np.array(len_list, dtype="int64")
    idx = np.array(idx_list, dtype="int64")

    # Optional subsample (keeps all fraud, fills with genuine) for big data.
    if max_samples is not None and len(X) > max_samples:
        rng = np.random.default_rng(seed)
        pos = np.where(y == 1)[0]
        neg = np.where(y == 0)[0]
        n_neg = max(0, max_samples - len(pos))
        keep_neg = rng.choice(neg, size=min(len(neg), n_neg), replace=False)
        keep = np.sort(np.concatenate([pos, keep_neg]))
        X, y, lengths, idx = X[keep], y[keep], lengths[keep], idx[keep]

    return X, y, lengths, idx


def time_aware_split(
    X: np.ndarray, y: np.ndarray, test_size: float = config.TEST_SIZE
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Split sequences keeping time order (no shuffling) to avoid leakage.

    The first (1 - test_size) of the sequences become the training set and
    the final test_size become the test set. Because sequences are built in
    customer/time order, this approximates a "train on past, test on future"
    setup.
    """
    n = len(X)
    if n == 0:
        return X, X, y, y
    split = int(n * (1 - test_size))
    split = max(1, min(split, n - 1))  # always keep at least 1 in each side
    return X[:split], X[split:], y[:split], y[split:]


def stratified_split(*arrays, y: np.ndarray, test_size: float = config.TEST_SIZE,
                     seed: int = config.RANDOM_SEED):
    """Stratified shuffle split that keeps the fraud ratio in both halves.

    Time-aware splitting is ideal but on small/sparse data a time split can put
    ALL fraud on one side. This stratified split guarantees fraud appears in
    both train and test so every metric/curve is well-defined. Returns, for
    each input array, a (train, test) tuple in order, plus (y_train, y_test).
    """
    y = np.asarray(y)
    n = len(y)
    rng = np.random.default_rng(seed)
    pos = rng.permutation(np.where(y == 1)[0])
    neg = rng.permutation(np.where(y == 0)[0])
    n_pos_test = max(1, int(round(len(pos) * test_size))) if len(pos) else 0
    n_neg_test = max(1, int(round(len(neg) * test_size))) if len(neg) else 0
    test_idx = np.concatenate([pos[:n_pos_test], neg[:n_neg_test]])
    train_idx = np.concatenate([pos[n_pos_test:], neg[n_neg_test:]])
    rng.shuffle(test_idx)
    rng.shuffle(train_idx)
    out = []
    for arr in arrays:
        arr = np.asarray(arr)
        out.append((arr[train_idx], arr[test_idx]))
    out.append((y[train_idx], y[test_idx]))
    return out
