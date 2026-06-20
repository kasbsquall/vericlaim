"""VeriClaim demo dashboard API (FastAPI).

Serves the single-file dashboard and a JSON feed of the verifications table so the demo can
show the audit history. The CAP provider runs separately (`python agent/cap_handler.py`).

Run from vericlaim/:  .venv/Scripts/python agent/main.py   (serves on 127.0.0.1:8800)
"""
from __future__ import annotations

import sys
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # agent/ for top-level imports

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy import desc, select

from database.connection import AsyncSessionLocal
from database.models import Verification

DASHBOARD = Path(__file__).resolve().parent.parent / "dashboard" / "index.html"
HACKATHON_PRICE_USDC = 0.10

app = FastAPI(title="VeriClaim", description="Adversarial insurance claim audit on CROO")


def _num(value: Decimal | None) -> float | None:
    return float(value) if isinstance(value, Decimal) else value


def _serialize(v: Verification) -> dict:
    # Data minimization: the public feed exposes only audit metadata, never the full
    # debate transcript or claim input (both carry claimant PII — names, incident details).
    transcript = v.debate_transcript or []
    agents = [t.get("agent") for t in transcript if t.get("slug") != "coordinator"]
    return {
        "cap_call_id": v.cap_call_id,
        "caller_wallet": v.caller_wallet,
        "payment_usdc": _num(v.payment_usdc),
        "decision": v.decision,
        "approved_amount": _num(v.approved_amount),
        "cited_clauses": v.cited_clauses or [],
        "audit_hash": v.audit_hash,
        "status": v.status,
        "agents_involved": agents,
        "created_at": v.created_at.isoformat() if v.created_at else None,
    }


@app.get("/api/health")
async def health() -> dict:
    return {"status": "ok", "service": "VeriClaim", "price_usdc": HACKATHON_PRICE_USDC}


@app.get("/api/verifications")
async def verifications() -> JSONResponse:
    async with AsyncSessionLocal() as session:
        rows = (
            await session.execute(
                select(Verification).order_by(desc(Verification.created_at)).limit(100)
            )
        ).scalars().all()
    return JSONResponse([_serialize(r) for r in rows])


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(DASHBOARD)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8800)
