"""
api/main.py
===========
FraudShield AI backend — a thin FastAPI layer over the existing `src/` pipeline.

It makes the dashboard a real prototype (not slideware):

    GET  /api/status      -> mode/source/primary, row counts, training state
    GET  /api/dashboard   -> full dashboard payload (live aggregates + curves)
    POST /api/score       -> live scoring of a single transaction (+ history)
    POST /api/score/batch -> score a list of transactions
    POST /api/dataset     -> upload a real PaySim CSV, validate, refresh
    POST /api/train       -> (re)train all models in the background

In production it also serves the built React app (web/dist) at "/".

Run:
    uvicorn api.main:app --reload --port 8000      (from the project root)
"""

from __future__ import annotations

import io
import sys
import threading
from pathlib import Path

import pandas as pd
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src import config                                   # noqa: E402
from src.data_loader import load_data, basic_overview    # noqa: E402
from src.predict import score_one, score_transactions, model_available  # noqa: E402
from src.export_dashboard_data import build_payload, write_snapshot  # noqa: E402
from src.utils import read_json, log                     # noqa: E402

app = FastAPI(title="FraudShield AI API", version="1.0.0")
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# In-memory cache + training state (so the heavy payload isn't rebuilt per call)
# ---------------------------------------------------------------------------
_STATE = {"payload": None, "training": False, "last_train": None, "message": ""}
_LOCK = threading.Lock()

REQUIRED_COLUMNS = [
    "step", "type", "amount", "nameOrig", "oldbalanceOrg", "newbalanceOrig",
    "nameDest", "oldbalanceDest", "newbalanceDest", "isFraud",
]


def _payload(force: bool = False):
    """Build (and cache) the dashboard payload, and keep the static snapshot
    in sync so a plain browser refresh always shows the latest data."""
    with _LOCK:
        if _STATE["payload"] is None or force:
            _STATE["payload"] = build_payload()
            try:
                write_snapshot(_STATE["payload"])   # self-heal the snapshot
            except Exception as exc:                # pragma: no cover
                log(f"Could not write snapshot: {exc}")
        return _STATE["payload"]


def _invalidate():
    with _LOCK:
        _STATE["payload"] = None


# ---------------------------------------------------------------------------
# Status
# ---------------------------------------------------------------------------
@app.get("/api/status")
def status():
    art = read_json(config.ARTIFACTS_PATH, default={}) or {}
    metrics = read_json(config.METRICS_PATH, default={}) or {}
    real = config.REAL_DATA_PATH.exists()
    return {
        "modelAvailable": model_available(),
        "mode": "model" if model_available() else "demo",
        "source": "real" if real else "sample",
        "primary": art.get("primary") or metrics.get("primary") or "lstm",
        "status": metrics.get("status", "NOT_TRAINED"),
        "realDatasetPresent": real,
        "training": _STATE["training"],
        "message": _STATE["message"],
        "thresholds": {"low": config.LOW_THRESHOLD, "high": config.HIGH_THRESHOLD},
    }


# ---------------------------------------------------------------------------
# Dashboard data
# ---------------------------------------------------------------------------
@app.get("/api/dashboard")
def dashboard(refresh: bool = False):
    try:
        return _payload(force=refresh)
    except Exception as exc:  # pragma: no cover
        raise HTTPException(500, f"Failed to build dashboard: {exc}")


# ---------------------------------------------------------------------------
# Live scoring
# ---------------------------------------------------------------------------
class ScoreRequest(BaseModel):
    transaction: dict
    history: list[dict] | None = None


@app.post("/api/score")
def score(req: ScoreRequest):
    try:
        return score_one(req.transaction, req.history)
    except Exception as exc:
        raise HTTPException(400, f"Scoring failed: {exc}")


class BatchRequest(BaseModel):
    transactions: list[dict]


@app.post("/api/score/batch")
def score_batch(req: BatchRequest):
    if not req.transactions:
        raise HTTPException(400, "No transactions supplied.")
    df = pd.DataFrame(req.transactions)
    scored, mode = score_transactions(df)
    cols = [c for c in ["step", "type", "amount", "nameOrig", "nameDest",
                        "fraud_probability", "risk_label", "recommended_action"]
            if c in scored.columns]
    return {"mode": mode, "rows": scored[cols].to_dict("records")}


# ---------------------------------------------------------------------------
# Dataset upload (connect the real PaySim file)
# ---------------------------------------------------------------------------
@app.post("/api/dataset")
async def upload_dataset(file: UploadFile = File(...)):
    raw = await file.read()
    try:
        df = pd.read_csv(io.BytesIO(raw))
    except Exception as exc:
        raise HTTPException(400, f"Could not read CSV: {exc}")

    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise HTTPException(
            400, f"CSV is missing required PaySim columns: {', '.join(missing)}")

    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(config.REAL_DATA_PATH, index=False)
    _invalidate()
    fraud = int(df["isFraud"].sum()) if "isFraud" in df else 0
    log(f"Real dataset uploaded: {len(df):,} rows -> {config.REAL_DATA_PATH}")
    return {
        "ok": True,
        "rows": int(len(df)),
        "fraud": fraud,
        "fraudPct": round(100 * fraud / len(df), 4) if len(df) else 0,
        "message": (f"Loaded {len(df):,} rows. The dashboard now uses your dataset. "
                    "It is scored with the current model — click 'Train on current "
                    "data' so the model matches this dataset."),
        "modelMatchesData": False,
    }


# ---------------------------------------------------------------------------
# Training (background)
# ---------------------------------------------------------------------------
def _run_training(epochs: int):
    try:
        with _LOCK:
            _STATE["training"] = True
            _STATE["message"] = "Training models…"
        from src.train_all import train_all
        summary = train_all(epochs=epochs)
        _invalidate()
        with _LOCK:
            _STATE["message"] = (f"Training complete. Primary model: "
                                 f"{summary['primary']} on {summary['source']} data.")
    except Exception as exc:  # pragma: no cover
        with _LOCK:
            _STATE["message"] = f"Training failed: {exc}"
    finally:
        with _LOCK:
            _STATE["training"] = False


@app.post("/api/train")
def train(epochs: int = config.EPOCHS):
    if _STATE["training"]:
        return {"ok": False, "message": "Training already in progress."}
    threading.Thread(target=_run_training, args=(epochs,), daemon=True).start()
    return {"ok": True, "message": "Training started in the background."}


@app.get("/api/health")
def health():
    return {"ok": True, "service": "FraudShield AI API"}


# ---------------------------------------------------------------------------
# Serve the built React app (if present) at "/"
# ---------------------------------------------------------------------------
_DIST = PROJECT_ROOT / "web" / "dist"
if _DIST.exists():
    app.mount("/", StaticFiles(directory=str(_DIST), html=True), name="web")
