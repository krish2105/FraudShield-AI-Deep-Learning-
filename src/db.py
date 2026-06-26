"""
db.py
=====
Persistence + audit layer (Phase 2).

Every fraud score and analyst decision is written to a database so the system
is **auditable** — a hard requirement for any real fraud/AML system. Defaults to
a local SQLite file (zero setup, perfect for the demo); point
`FRAUDSHIELD_DATABASE_URL` at Postgres for production with no code changes.

Tables
------
score_audit   : one row per scored transaction (immutable audit trail)
case_decision : analyst verdicts that close the feedback loop (future training labels)

Usage
-----
    from src.db import init_db, record_score
    init_db()
    record_score(request_id, txn, result)
"""

from __future__ import annotations

import json
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

from sqlalchemy import (Boolean, Column, DateTime, Float, Integer, String, Text,
                        create_engine, func, select)
from sqlalchemy.orm import declarative_base, sessionmaker, Session

try:
    from .settings import settings
    from .utils import log
except ImportError:  # pragma: no cover
    import sys
    sys.path.append(str(Path(__file__).resolve().parents[1]))
    from src.settings import settings
    from src.utils import log

Base = declarative_base()
_engine = None
_SessionLocal = None


def _now() -> datetime:
    return datetime.now(timezone.utc)


class ScoreAudit(Base):
    __tablename__ = "score_audit"
    id = Column(Integer, primary_key=True, autoincrement=True)
    request_id = Column(String(64), index=True)
    created_at = Column(DateTime, default=_now, index=True)
    name_orig = Column(String(64), index=True)
    name_dest = Column(String(64))
    txn_type = Column(String(16))
    amount = Column(Float)
    probability = Column(Float, index=True)
    risk_band = Column(String(16), index=True)
    recommended_action = Column(String(64))
    mode = Column(String(16))             # "model" or "demo"
    transaction_json = Column(Text)        # full input for replay/debugging


class CaseDecision(Base):
    __tablename__ = "case_decision"
    id = Column(Integer, primary_key=True, autoincrement=True)
    request_id = Column(String(64), index=True)
    created_at = Column(DateTime, default=_now, index=True)
    analyst = Column(String(64))
    verdict = Column(String(16))           # "fraud" | "genuine"
    notes = Column(Text)
    used_for_training = Column(Boolean, default=False)


def init_db() -> None:
    """Create the engine + tables (idempotent)."""
    global _engine, _SessionLocal
    if _engine is not None:
        return
    url = settings.database_url
    kwargs = {"connect_args": {"check_same_thread": False}} if url.startswith("sqlite") else {}
    _engine = create_engine(url, future=True, **kwargs)
    _SessionLocal = sessionmaker(bind=_engine, expire_on_commit=False, class_=Session)
    Base.metadata.create_all(_engine)
    log(f"Audit DB ready -> {url}")


@contextmanager
def session_scope() -> Iterator[Session]:
    if _SessionLocal is None:
        init_db()
    s = _SessionLocal()
    try:
        yield s
        s.commit()
    except Exception:
        s.rollback()
        raise
    finally:
        s.close()


def record_score(request_id: str, txn: dict, result: dict) -> None:
    """Persist one scored transaction to the immutable audit trail."""
    if not settings.persist_scores:
        return
    try:
        with session_scope() as s:
            s.add(ScoreAudit(
                request_id=request_id,
                name_orig=str(txn.get("nameOrig", "")),
                name_dest=str(txn.get("nameDest", "")),
                txn_type=str(txn.get("type", "")),
                amount=float(txn.get("amount", 0) or 0),
                probability=float(result.get("probability", 0) or 0),
                risk_band=str(result.get("band", "")),
                recommended_action=str(result.get("recommended_action", "")),
                mode=str(result.get("mode", "")),
                transaction_json=json.dumps(txn, default=str),
            ))
    except Exception as exc:  # never let auditing break scoring
        log(f"Could not persist score audit: {exc}")


def record_decision(request_id: str, analyst: str, verdict: str, notes: str = "") -> None:
    with session_scope() as s:
        s.add(CaseDecision(request_id=request_id, analyst=analyst,
                           verdict=verdict, notes=notes))


def audit_summary() -> dict:
    """Lightweight stats for a /audit endpoint and dashboards."""
    try:
        with session_scope() as s:
            total = s.scalar(select(func.count()).select_from(ScoreAudit)) or 0
            high = s.scalar(select(func.count()).select_from(ScoreAudit)
                            .where(ScoreAudit.risk_band == "HIGH")) or 0
            recent = s.execute(
                select(ScoreAudit).order_by(ScoreAudit.created_at.desc()).limit(10)
            ).scalars().all()
            return {
                "total_scored": int(total),
                "high_risk": int(high),
                "recent": [{
                    "request_id": r.request_id,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                    "type": r.txn_type, "amount": r.amount,
                    "probability": r.probability, "risk_band": r.risk_band,
                    "action": r.recommended_action, "mode": r.mode,
                } for r in recent],
            }
    except Exception as exc:  # pragma: no cover
        return {"total_scored": 0, "high_risk": 0, "recent": [], "error": str(exc)}
