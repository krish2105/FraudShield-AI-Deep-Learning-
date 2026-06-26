"""
API integration tests using FastAPI's TestClient (Phase 7).
These exercise the real app object in-process — no running server needed.
Run with:  pytest -q
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    from fastapi.testclient import TestClient
    from api.main import app
    client = TestClient(app)
    _HAVE = True
except Exception:  # pragma: no cover
    _HAVE = False

pytestmark = pytest.mark.skipif(not _HAVE, reason="fastapi TestClient / httpx unavailable")

SUSPICIOUS = {
    "step": 5, "type": "TRANSFER", "amount": 90000.0, "nameOrig": "C9999999",
    "oldbalanceOrg": 90000.0, "newbalanceOrig": 0.0, "nameDest": "C8888888",
    "oldbalanceDest": 0.0, "newbalanceDest": 0.0, "isFraud": 0,
}


def test_health():
    r = client.get("/api/health")
    assert r.status_code == 200 and r.json()["ok"] is True


def test_status_shape():
    r = client.get("/api/status")
    assert r.status_code == 200
    assert {"mode", "primary", "thresholds"}.issubset(r.json())


def test_score_returns_probability_and_request_id():
    r = client.post("/api/score", json={"transaction": SUSPICIOUS})
    assert r.status_code == 200
    body = r.json()
    assert 0.0 <= body["probability"] <= 1.0
    assert "request_id" in body
    assert r.headers.get("X-Request-ID")


def test_v1_alias_works():
    r = client.post("/api/v1/score", json={"transaction": SUSPICIOUS})
    assert r.status_code == 200 and "probability" in r.json()


def test_explain_endpoint():
    r = client.post("/api/explain", json={"transaction": SUSPICIOUS})
    assert r.status_code == 200 and r.json()["reasons"]


def test_batch_validation_rejects_empty():
    r = client.post("/api/score/batch", json={"transactions": []})
    assert r.status_code == 422  # pydantic min_length


def test_metrics_endpoint_optional():
    r = client.get("/metrics")
    assert r.status_code in (200, 503)
