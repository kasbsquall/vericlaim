"""Unit tests for case-driven on-chain recruitment (recruit.py), with the on-chain hire, the
corpus check, the debate, and persistence all mocked — so the recruitment gating + wiring is
verified deterministically without CROO, a DB, or an LLM.
"""
import asyncio
from unittest.mock import AsyncMock

import cap_handler
import recruit
from debate_engine import DebateResult


def _result() -> DebateResult:
    return DebateResult(
        decision="APPROVED", approved_amount=4000.0, legal_reasoning="DECISION: APPROVED",
        cited_clauses=["§9"], audit_hash="ab" * 32, transcript=[], agents_involved=["Blake", "Sam"],
    )


def _claim(**over):
    base = {
        "claim_number": "CLM-X",
        "policy": {"policy_type": "Acme v2 (unseen)", "deductible": 0.0},
        "policy_document": "ACME v2 §1 ... §9 burst-pipe water covered notwithstanding §3.",
        "incident_type": "water_damage", "amount_requested": 4000.0,
        "original_denial_reason": "Denied under §3.",
    }
    base.update(over)
    return base


def _mock_core(monkeypatch):
    monkeypatch.setattr(cap_handler, "run_debate", AsyncMock(return_value=_result()))
    monkeypatch.setattr(cap_handler, "_persist", AsyncMock())


def _enable(monkeypatch, *, corpus_has=False):
    monkeypatch.setattr(recruit, "COMPOSE_ENABLED", True)
    monkeypatch.setattr(recruit, "POLICY_EXTRACTOR_SERVICE_ID", "svc-pe")
    monkeypatch.setattr(recruit, "REPORT_EXPORTER_SERVICE_ID", "svc-re")
    monkeypatch.setattr(recruit, "_corpus_has", AsyncMock(return_value=corpus_has))

    async def fake_hire(sdk_key, service_id, requirements, *, timeout=240):
        if service_id == "svc-pe":
            return {"clauses_added": 3}, {"order_id": "ord-PE", "negotiation_id": "neg-PE"}
        return {"filename": "v.pdf"}, {"order_id": "ord-RE", "negotiation_id": "neg-RE"}

    monkeypatch.setattr(recruit, "hire_service_traced", fake_hire)


def test_compose_off_by_default_no_recruitment(monkeypatch):
    _mock_core(monkeypatch)
    monkeypatch.setattr(recruit, "COMPOSE_ENABLED", False)
    out = asyncio.run(cap_handler.process_order(_claim(deliver_pdf=True)))
    assert "recruited_agents" not in out


def test_recruits_both_when_the_case_demands(monkeypatch):
    _mock_core(monkeypatch)
    _enable(monkeypatch, corpus_has=False)
    out = asyncio.run(cap_handler.process_order(_claim(deliver_pdf=True)))
    agents = [r["agent"] for r in out["recruited_agents"]]
    assert agents == ["PolicyExtractor", "ReportExporter"]
    assert out["recruited_agents"][0]["order_id"] == "ord-PE"


def test_skips_policy_extractor_when_corpus_already_has_it(monkeypatch):
    _mock_core(monkeypatch)
    _enable(monkeypatch, corpus_has=True)
    out = asyncio.run(cap_handler.process_order(_claim(deliver_pdf=True)))
    agents = [r["agent"] for r in out.get("recruited_agents", [])]
    assert "PolicyExtractor" not in agents
    assert agents == ["ReportExporter"]


def test_skips_report_exporter_without_deliver_pdf(monkeypatch):
    _mock_core(monkeypatch)
    _enable(monkeypatch, corpus_has=False)
    out = asyncio.run(cap_handler.process_order(_claim()))  # no deliver_pdf
    assert [r["agent"] for r in out["recruited_agents"]] == ["PolicyExtractor"]


def test_failed_hire_is_best_effort(monkeypatch):
    _mock_core(monkeypatch)
    _enable(monkeypatch, corpus_has=False)
    monkeypatch.setattr(recruit, "hire_service_traced", AsyncMock(side_effect=RuntimeError("chain down")))
    out = asyncio.run(cap_handler.process_order(_claim(deliver_pdf=True)))
    assert out["decision"] == "APPROVED"          # adjudication still succeeds
    assert "recruited_agents" not in out          # failed hires record nothing
