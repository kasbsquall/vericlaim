"""ClaimIngester (CAP agent, $0.05 USDC) — Track: Data & Verification.

Takes raw text (an insured's email / scanned form) -> parses it into VeriClaim's structured
claim JSON via an LLM -> hires VeriClaim over CAP and returns the resolution. A real A2A
counterparty: it discovers, pays, and consumes VeriClaim.

Run from vericlaim/:
  python helper_agents/claim_ingester/main.py --simulate   # local, no CAP (calls VeriClaim in-proc)
  python helper_agents/claim_ingester/main.py --serve       # CAP provider (needs keys + service id)
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
from pathlib import Path
from uuid import uuid4

VERICLAIM_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(VERICLAIM_ROOT))

from helper_agents.common import (  # noqa: E402
    VERICLAIM_SERVICE_ID,
    hire_service,
    llm_json,
    serve_provider,
)

logger = logging.getLogger("vericlaim.claim_ingester")
SDK_KEY = os.getenv("CLAIM_INGESTER_SDK_KEY", "")

PARSE_SYSTEM = """You convert a raw insurance-claim dispute (email, form, or note) into a strict
JSON object for an adjudication engine. Output ONLY the JSON, no prose. Schema:
{
  "claim_number": string,
  "policy_id": string,
  "policy": {"policy_type": string, "insured_name": string, "insurance_company": string,
             "coverage_limit": number, "deductible": number},
  "incident_type": string,
  "incident_description": string,
  "original_denial_reason": string,
  "amount_requested": number,
  "supporting_docs": [{"type": string, "ref": string, "summary": string}]
}
Rules: use values stated in the text; if the deductible is unknown use 0; infer incident_type
(e.g. "collision", "theft"); keep summaries short. Never invent clause numbers."""

SAMPLE_TEXT = """From: David Chen
Subject: Appeal — denial of claim CLM-2024-04471 (policy CPP-2024-8821, Crestview Mutual)

To whom it may concern,

I'm formally disputing the denial of my collision claim CLM-2024-04471 under my Crestview Mutual
"Auto Preferred" policy CPP-2024-8821 (Auto / Collision + Comprehensive; $50,000 limit; $0
deductible applies to this claim).

On Oct 15, 2024 I struck a guardrail on I-95 North near Fort Lauderdale at about 35 mph. The front
end and engine compartment were severely damaged, and the engine seized AFTER the impact. The
repair is $12,000.

You denied the entire claim under §7.3 (Mechanical Failure Exclusion), claiming the mechanical
failure preceded the collision. That is wrong, and I have proof:
- Police report FHP-2024-10153: confirms the vehicle was in motion and lost control upon guardrail
  contact BEFORE the engine ceased operation.
- Certified mechanic report BM-AUTO-2024-089: the engine seized due to catastrophic impact damage
  to the oil pan and crankshaft — consistent with a high-force collision, NOT a pre-existing fault.

This is a collision-caused failure. Please re-review the claim in full.

— David Chen"""


def _validate_claim(claim: dict) -> dict:
    """Fail fast at the boundary: a malformed LLM parse must not silently degrade to a $0 verdict."""
    if not isinstance(claim, dict):
        raise ValueError("parsed claim is not a JSON object")
    if not str(claim.get("claim_number") or "").strip():
        raise ValueError("parsed claim is missing 'claim_number'")
    try:
        amount = float(claim.get("amount_requested") or 0)
    except (TypeError, ValueError):
        amount = 0.0
    if amount <= 0:
        raise ValueError("parsed claim has no positive 'amount_requested'")
    return claim


async def parse_claim(raw_text: str) -> dict:
    """Raw dispute text -> structured claim JSON VeriClaim accepts (validated)."""
    claim = await llm_json(PARSE_SYSTEM, f"Raw claim text:\n{raw_text}\n\nReturn the claim JSON.")
    return _validate_claim(claim)


async def _verify_in_process(claim: dict) -> dict:
    """Call VeriClaim's debate directly (no CAP) — used by --simulate."""
    sys.path.insert(0, str(VERICLAIM_ROOT / "agent"))
    from cap_handler import process_order  # noqa: PLC0415

    return await process_order(
        claim, cap_call_id=f"INGESTER-SIM-{uuid4().hex[:8]}", caller_wallet="0xCLAIM_INGESTER"
    )


async def _handler(requirements: dict) -> dict:
    """CAP provider handler: {"raw_text": ...} -> parse -> hire VeriClaim -> return resolution."""
    raw = requirements.get("raw_text") or requirements.get("text") or json.dumps(requirements)
    claim = await parse_claim(raw)
    resolution = await hire_service(SDK_KEY, VERICLAIM_SERVICE_ID, claim)
    return {"claim": claim, "resolution": resolution}


async def _simulate() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
    print("Parsing raw claim text with the LLM...")
    claim = await parse_claim(SAMPLE_TEXT)
    print("Structured claim:\n", json.dumps(claim, indent=2))
    print("\nHiring VeriClaim (in-process for the sim)...")
    resolution = await _verify_in_process(claim)
    print("\nResolution:", resolution["decision"], "| amount:", resolution["approved_amount"])
    print("Cited clauses:", resolution["cited_clauses"], "| audit:", resolution["audit_hash"][:16], "...")


if __name__ == "__main__":
    if "--serve" in sys.argv:
        logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
        asyncio.run(serve_provider(SDK_KEY, _handler, label="ClaimIngester"))
    else:
        asyncio.run(_simulate())
