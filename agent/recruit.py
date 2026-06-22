"""Case-driven, on-chain agent recruitment — VeriClaim as a BUYER of specialist CAP agents.

A fixed pipeline isn't the CROO thesis; a *composing* agent is. When a claim needs a capability
VeriClaim doesn't have in-house, it HIRES a specialist on CROO, on-chain, mid-adjudication — a real
A2A DAG driven by the case, not a hard-wired chain:

  • the policy isn't in the RAG corpus and the claim ships its text (`policy_document`)
        -> hire PolicyExtractor to ingest + embed it, so the panel can reason over it
  • the caller asked for a filed report (`deliver_pdf`)
        -> hire ReportExporter to render the verdict into a submittable PDF

Every hire is OPT-IN (`VERICLAIM_COMPOSE=1`) and BEST-EFFORT: an unconfigured or failed hire never
breaks the adjudication — VeriClaim records the attempt and proceeds with what it has. Default OFF,
so the eval, the tests, and the live provider are unchanged unless composition is explicitly enabled.
"""
from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

from sqlalchemy import select

from config import settings
from database.connection import AsyncSessionLocal
from database.models import PolicyClause

# helper_agents/ lives at the repo root (sibling of agent/); put it on the path for the buyer layer.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from helper_agents.common import hire_service_traced  # noqa: E402

logger = logging.getLogger("vericlaim.recruit")

COMPOSE_ENABLED = os.getenv("VERICLAIM_COMPOSE", "0") == "1"
POLICY_EXTRACTOR_SERVICE_ID = os.getenv("POLICY_EXTRACTOR_SERVICE_ID", "")
REPORT_EXPORTER_SERVICE_ID = os.getenv("REPORT_EXPORTER_SERVICE_ID", "")

_HIRE_TIMEOUT = 240


async def _corpus_has(policy_type: str | None) -> bool:
    """True if the RAG corpus already holds clauses for this policy_type."""
    if not policy_type:
        return False
    async with AsyncSessionLocal() as session:
        return bool(
            await session.scalar(
                select(PolicyClause.id).where(PolicyClause.policy_type == policy_type).limit(1)
            )
        )


def _policy_document(payload: dict) -> str | None:
    policy = payload.get("policy") or {}
    return payload.get("policy_document") or policy.get("policy_document")


async def recruit_policy_extractor(payload: dict) -> dict | None:
    """If the claim cites a policy VeriClaim hasn't seen and ships its text, hire PolicyExtractor
    on-chain to ingest it into the corpus BEFORE the debate. Returns a trace dict, or None."""
    if not (COMPOSE_ENABLED and POLICY_EXTRACTOR_SERVICE_ID):
        return None
    policy_text = _policy_document(payload)
    if not policy_text:
        return None
    policy_type = (payload.get("policy") or {}).get("policy_type", "Custom")
    if await _corpus_has(policy_type):
        return None  # already grounded for this insurer — no hire needed
    try:
        result, trace = await hire_service_traced(
            settings.croo_sdk_key, POLICY_EXTRACTOR_SERVICE_ID,
            {"policy_text": policy_text, "policy_type": policy_type}, timeout=_HIRE_TIMEOUT,
        )
        logger.info(
            "Recruited PolicyExtractor on-chain (order %s): +%s clauses for %r",
            trace["order_id"], result.get("clauses_added"), policy_type,
        )
        return {
            "agent": "PolicyExtractor", "reason": f"policy '{policy_type}' not in corpus",
            "order_id": trace["order_id"], "clauses_added": result.get("clauses_added", 0),
        }
    except Exception:
        logger.exception("PolicyExtractor recruitment failed — proceeding without it")
        return None


async def recruit_report_exporter(payload: dict, response: dict) -> dict | None:
    """If the caller asked for a filed report, hire ReportExporter on-chain to render the verdict
    into a PDF. Returns a trace dict, or None."""
    if not (COMPOSE_ENABLED and REPORT_EXPORTER_SERVICE_ID):
        return None
    if not payload.get("deliver_pdf"):
        return None
    try:
        result, trace = await hire_service_traced(
            settings.croo_sdk_key, REPORT_EXPORTER_SERVICE_ID, response, timeout=_HIRE_TIMEOUT,
        )
        logger.info("Recruited ReportExporter on-chain (order %s): %s", trace["order_id"], result.get("filename"))
        return {
            "agent": "ReportExporter", "reason": "caller requested a filed PDF",
            "order_id": trace["order_id"], "filename": result.get("filename"),
        }
    except Exception:
        logger.exception("ReportExporter recruitment failed — proceeding without it")
        return None
