"""
scripts/smoke_test.py
=====================
Bulletproof-the-demo smoke test (Phase 0).

Hits the running FastAPI service and asserts that every endpoint the
presentation relies on returns a sane response. Run this right before you
present — if it prints ALL CHECKS PASSED, the live demo will work.

    python scripts/smoke_test.py                 # checks http://localhost:8000
    API_URL=http://host:8000 python scripts/smoke_test.py

Exit code 0 = healthy, 1 = something is wrong (with a clear message).
"""

from __future__ import annotations

import os
import sys
import json
import urllib.request
import urllib.error

API = os.environ.get("API_URL", "http://localhost:8000").rstrip("/")
TIMEOUT = 30


def _call(method: str, path: str, body: dict | None = None) -> tuple[int, dict]:
    url = f"{API}{path}"
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    if data is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, {"error": e.read().decode()[:200]}
    except Exception as e:  # connection refused etc.
        print(f"  ✗ Could not reach {url}: {e}")
        print(f"\n  Is the API running?  ->  uvicorn api.main:app --port 8000")
        sys.exit(1)


PASS, FAIL = "  ✓", "  ✗"
failures = 0


def check(name: str, ok: bool, detail: str = "") -> None:
    global failures
    print(f"{PASS if ok else FAIL} {name}{(' — ' + detail) if detail else ''}")
    if not ok:
        failures += 1


def main() -> int:
    print(f"FraudShield AI smoke test against {API}\n")

    # 1. health
    st, body = _call("GET", "/api/health")
    check("GET /api/health", st == 200 and body.get("ok") is True)

    # 2. status
    st, status = _call("GET", "/api/status")
    check("GET /api/status", st == 200 and "mode" in status,
          f"mode={status.get('mode')} primary={status.get('primary')}")

    # 3. dashboard payload
    st, dash = _call("GET", "/api/dashboard")
    check("GET /api/dashboard", st == 200 and isinstance(dash, dict),
          f"{len(dash)} top-level keys")

    # 4. live scoring — a clearly suspicious full-balance sweep
    txn = {
        "step": 5, "type": "TRANSFER", "amount": 90000.0,
        "nameOrig": "C9999999", "oldbalanceOrg": 90000.0, "newbalanceOrig": 0.0,
        "nameDest": "C8888888", "oldbalanceDest": 0.0, "newbalanceDest": 0.0,
        "isFraud": 0,
    }
    st, score = _call("POST", "/api/score", {"transaction": txn})
    ok = st == 200 and "probability" in score and 0.0 <= score["probability"] <= 1.0
    check("POST /api/score", ok,
          f"p={score.get('probability')} band={score.get('risk_label')} mode={score.get('mode')}")

    # 5. batch scoring
    st, batch = _call("POST", "/api/score/batch", {"transactions": [txn, txn]})
    check("POST /api/score/batch", st == 200 and len(batch.get("rows", [])) == 2)

    print()
    if failures:
        print(f"  {failures} CHECK(S) FAILED — fix before presenting.")
        return 1
    print("  ALL CHECKS PASSED — the demo is ready. 🛡️")
    return 0


if __name__ == "__main__":
    sys.exit(main())
