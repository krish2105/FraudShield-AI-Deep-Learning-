"""
utils.py
========
Small helper functions shared across the project: reproducible seeds,
safe JSON read/write, currency formatting and a tiny logger.

Kept deliberately simple and dependency-light so it imports cleanly even
when TensorFlow is not installed.
"""

from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any

import numpy as np

from . import config


def set_seeds(seed: int = config.RANDOM_SEED) -> None:
    """Set random seeds for reproducibility (python + numpy + torch)."""
    random.seed(seed)
    np.random.seed(seed)
    try:
        import torch  # imported lazily so utils works without torch
        torch.manual_seed(seed)
    except Exception:
        # torch not installed - fine for pure-data (non-training) code paths.
        pass


def log(message: str) -> None:
    """Very small console logger with a consistent prefix."""
    print(f"[FraudShield] {message}")


def read_json(path: str | Path, default: Any = None) -> Any:
    """Read a JSON file. Returns `default` if the file is missing/invalid."""
    path = Path(path)
    if not path.exists():
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return default


def write_json(path: str | Path, data: Any) -> None:
    """Write a dictionary to a JSON file (creating parent folders)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)


def format_currency(value: float, symbol: str = "$") -> str:
    """Format a number as a readable currency string, e.g. $1.2M / $3.4K."""
    try:
        value = float(value)
    except (TypeError, ValueError):
        return f"{symbol}0"
    abs_v = abs(value)
    if abs_v >= 1_000_000_000:
        return f"{symbol}{value / 1_000_000_000:.2f}B"
    if abs_v >= 1_000_000:
        return f"{symbol}{value / 1_000_000:.2f}M"
    if abs_v >= 1_000:
        return f"{symbol}{value / 1_000:.1f}K"
    return f"{symbol}{value:,.0f}"


def safe_div(numerator: float, denominator: float, default: float = 0.0) -> float:
    """Divide two numbers, returning `default` when the denominator is 0."""
    try:
        if denominator == 0:
            return default
        return numerator / denominator
    except (TypeError, ZeroDivisionError):
        return default
