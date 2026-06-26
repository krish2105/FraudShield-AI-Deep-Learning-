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
import time
import uuid
import threading
from contextlib import asynccontextmanager
from pathlib import Path

import pandas as pd
from fastapi import FastAPI, UploadFile, File, HTTPException, Header, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src import config                                   # noqa: E402
from src.settings import settings                        # noqa: E402
from src import db                                       # noqa: E402
from src.data_loader import load_data, basic_overview    # noqa: E402
from src.predict import score_one, score_transactions, model_available  # noqa: E402
from src.export_dashboard_data import build_payload, write_snapshot  # noqa: E402
from src.utils import read_json, log                     # noqa: E402

# --- Observability (Prometheus). Degrades gracefully if not installed. -------
try:
    from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
    _SCORE_COUNT = Counter("fraudshield_scores_total", "Scores served", ["mode", "band"])
    _REQ_LATENCY = Histogram("fraudshield_request_seconds", "Request latency", ["endpoint"])
    _HAVE_PROM = True
except Exception:  # pragma: no cover
    _HAVE_PROM = False

@asynccontextmanager
async def _lifespan(app: FastAPI):
    try:
        db.init_db()
    except Exception as exc:  # never let DB issues stop the API from serving
        log(f"DB init failed ({exc}); continuing without persistence.")
    # Pre-warm the dashboard payload in the background so the FIRST request is
    # instant (no cold-build lag during a live demo).
    def _prewarm():
        try:
            _payload()
            log("Dashboard payload pre-warmed.")
        except Exception as exc:  # pragma: no cover
            log(f"Dashboard pre-warm skipped ({exc}).")
    threading.Thread(target=_prewarm, daemon=True).start()
    log(f"FraudShield API up. auth_required={settings.auth_required} "
        f"persist_scores={settings.persist_scores}")
    yield


app = FastAPI(title="FraudShield AI API", version="2.0.0", lifespan=_lifespan)
app.add_middleware(
    CORSMiddleware, allow_origins=settings.cors_list,
    allow_methods=["*"], allow_headers=["*"],
)


@app.middleware("http")
async def _observability(request: Request, call_next):
    """Attach a request id, time the request, and feed Prometheus."""
    rid = request.headers.get("X-Request-ID") or uuid.uuid4().hex[:16]
    request.state.request_id = rid
    start = time.perf_counter()
    response = await call_next(request)
    elapsed = time.perf_counter() - start
    response.headers["X-Request-ID"] = rid
    response.headers["X-Response-Time-ms"] = f"{elapsed * 1000:.1f}"
    if _HAVE_PROM:
        try:
            _REQ_LATENCY.labels(endpoint=request.url.path).observe(elapsed)
        except Exception:
            pass
    return response


def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
    """Dependency: enforce X-API-Key only when an API key is configured.
    With no key set (the default for the local demo) this is a no-op."""
    if settings.auth_required and x_api_key != settings.api_key:
        raise HTTPException(401, "Invalid or missing X-API-Key.")

# ---------------------------------------------------------------------------
# In-memory cache + training state (so the heavy payload isn't rebuilt per call)
# ---------------------------------------------------------------------------
_STATE = {"payload": None, "training": False, "last_train": None, "message": ""}
_LOCK = threading.Lock()

REQUIRED_COLUMNS = [
    "step", "type", "amount", "nameOrig", "oldbalanceOrg", "newbalanceOrig",
    "nameDest", "oldbalanceDest", "newbalanceDest", "isFraud",
]


def _sanitize(obj):
    """Recursively replace NaN/Inf with None so the payload is JSON-compliant.
    (Large datasets can produce NaN in correlations; strict JSON rejects them.)"""
    import math
    if isinstance(obj, float):
        return None if (math.isnan(obj) or math.isinf(obj)) else obj
    if isinstance(obj, dict):
        return {k: _sanitize(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_sanitize(v) for v in obj]
    return obj


def _payload(force: bool = False):
    """Build (and cache) the dashboard payload, and keep the static snapshot
    in sync so a plain browser refresh always shows the latest data."""
    with _LOCK:
        if _STATE["payload"] is None or force:
            _STATE["payload"] = _sanitize(build_payload())
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
def score(req: ScoreRequest, request: Request, _: None = Depends(require_api_key)):
    try:
        result = score_one(req.transaction, req.history)
    except Exception as exc:
        raise HTTPException(400, f"Scoring failed: {exc}")
    rid = getattr(request.state, "request_id", uuid.uuid4().hex[:16])
    result["request_id"] = rid
    db.record_score(rid, req.transaction, result)          # immutable audit trail
    if _HAVE_PROM:
        try:
            _SCORE_COUNT.labels(mode=result.get("mode", "?"),
                                band=result.get("band", "?")).inc()
        except Exception:
            pass
    return result


@app.post("/api/explain")
def explain(req: ScoreRequest, _: None = Depends(require_api_key)):
    """Plain-English reason codes for why a transaction is risky (Phase 7)."""
    from src.explain import explain_transaction
    return explain_transaction(req.transaction)


class BatchRequest(BaseModel):
    transactions: list[dict] = Field(..., min_length=1, max_length=50_000)


@app.post("/api/score/batch")
def score_batch(req: BatchRequest, _: None = Depends(require_api_key)):
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
async def upload_dataset(file: UploadFile = File(...),
                         _: None = Depends(require_api_key)):
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
def train(epochs: int = config.EPOCHS, _: None = Depends(require_api_key)):
    if _STATE["training"]:
        return {"ok": False, "message": "Training already in progress."}
    threading.Thread(target=_run_training, args=(epochs,), daemon=True).start()
    return {"ok": True, "message": "Training started in the background."}


@app.get("/api/health")
def health():
    return {"ok": True, "service": "FraudShield AI API", "version": app.version}


# ---------------------------------------------------------------------------
# Audit trail (Phase 2/5) — proves every decision is recorded
# ---------------------------------------------------------------------------
@app.get("/api/audit")
def audit(_: None = Depends(require_api_key)):
    return db.audit_summary()


class DecisionRequest(BaseModel):
    request_id: str
    analyst: str = "analyst"
    verdict: str = Field(..., pattern="^(fraud|genuine)$")
    notes: str = ""


@app.post("/api/decision")
def decision(req: DecisionRequest, _: None = Depends(require_api_key)):
    """Record an analyst verdict — closes the feedback loop for future training."""
    db.record_decision(req.request_id, req.analyst, req.verdict, req.notes)
    return {"ok": True, "message": "Decision recorded."}


# ---------------------------------------------------------------------------
# Observability (Phase 5) — Prometheus scrape endpoint
# ---------------------------------------------------------------------------
@app.get("/metrics")
def metrics():
    if not _HAVE_PROM:
        raise HTTPException(503, "prometheus_client not installed.")
    return PlainTextResponse(generate_latest(), media_type=CONTENT_TYPE_LATEST)


# ---------------------------------------------------------------------------
# Versioned API (Phase 4) — /api/v1/* aliases the stable endpoints
# ---------------------------------------------------------------------------
from fastapi import APIRouter  # noqa: E402

v1 = APIRouter(prefix="/api/v1", tags=["v1"])
v1.add_api_route("/status", status, methods=["GET"])
v1.add_api_route("/dashboard", dashboard, methods=["GET"])
v1.add_api_route("/score", score, methods=["POST"])
v1.add_api_route("/score/batch", score_batch, methods=["POST"])
v1.add_api_route("/explain", explain, methods=["POST"])
v1.add_api_route("/dataset", upload_dataset, methods=["POST"])
v1.add_api_route("/train", train, methods=["POST"])
v1.add_api_route("/audit", audit, methods=["GET"])
v1.add_api_route("/decision", decision, methods=["POST"])
v1.add_api_route("/health", health, methods=["GET"])
app.include_router(v1)


# ---------------------------------------------------------------------------
# Serve the built React app (if present) at "/"
# ---------------------------------------------------------------------------
_DIST = PROJECT_ROOT / "web" / "dist"
if _DIST.exists():
    app.mount("/", StaticFiles(directory=str(_DIST), html=True), name="web")
