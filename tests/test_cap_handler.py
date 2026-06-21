"""Integration tests for the CAP order lifecycle (the riskiest provider code), with the SDK,
DB, and LLMs all mocked — so the order-processing + idempotency logic is verified deterministically
without a live debate or database.
"""
import asyncio
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

from sqlalchemy.exc import IntegrityError

import cap_handler
from debate_engine import DebateResult


def _result() -> DebateResult:
    return DebateResult(
        decision="APPROVED",
        approved_amount=12000.0,
        legal_reasoning="--- DECISION: APPROVED ... under §12.1",
        cited_clauses=["§12.1", "§7.3"],
        audit_hash="deadbeef" * 8,
        transcript=[{"slug": "blake", "agent": "Blake", "content": "coverage analysis"}],
        agents_involved=["Blake", "Morgan", "Alex", "Sam"],
    )


def test_build_response_shape():
    r = cap_handler._build_response(_result())
    assert r["decision"] == "APPROVED"
    assert r["approved_amount"] == 12000.0
    assert r["cited_clauses"] == ["§12.1", "§7.3"]
    assert r["audit_hash"] == "deadbeef" * 8
    assert r["agents_involved"] == ["Blake", "Morgan", "Alex", "Sam"]
    assert "reasoning" in r and "debate_transcript" in r


def test_process_order_runs_debate_once_persists_and_responds(monkeypatch):
    run_mock = AsyncMock(return_value=_result())
    persist_mock = AsyncMock()
    monkeypatch.setattr(cap_handler, "run_debate", run_mock)
    monkeypatch.setattr(cap_handler, "_persist", persist_mock)

    out = asyncio.run(
        cap_handler.process_order({"claim_number": "CLM-1"}, cap_call_id="ord_1", caller_wallet="0xABC")
    )

    run_mock.assert_awaited_once()  # the debate runs exactly once per order
    persist_mock.assert_awaited_once()
    kw = persist_mock.await_args.kwargs
    assert kw["cap_call_id"] == "ord_1"
    assert kw["caller_wallet"] == "0xABC"
    assert kw["payment_usdc"] == cap_handler.HACKATHON_PRICE_USDC
    assert out["decision"] == "APPROVED" and out["approved_amount"] == 12000.0


def test_persist_is_idempotent_on_duplicate_order(monkeypatch):
    """A re-delivered/duplicate cap_call_id hits the UNIQUE constraint -> IntegrityError, which
    must be swallowed (rollback) so a provider retry never crashes or double-charges."""
    session = MagicMock()
    session.add = MagicMock()
    session.commit = AsyncMock(side_effect=IntegrityError("INSERT", {}, Exception("duplicate key")))
    session.rollback = AsyncMock()

    class _Ctx:
        async def __aenter__(self):
            return session

        async def __aexit__(self, *exc):
            return False

    monkeypatch.setattr(cap_handler, "AsyncSessionLocal", lambda: _Ctx())

    # Must NOT raise.
    asyncio.run(
        cap_handler._persist(
            {"claim_number": "CLM-1"}, _result(),
            cap_call_id="dup_order", caller_wallet="0x", payment_usdc=Decimal("0.10"),
        )
    )
    session.add.assert_called_once()
    session.rollback.assert_awaited_once()
