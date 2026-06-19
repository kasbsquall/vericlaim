"""PolicyExtractor (CAP agent, $0.05 USDC) — Track: Research & Intelligence.

Takes raw policy text -> extracts structured clauses via an LLM -> embeds them into pgvector
(policy_clauses) so VeriClaim can RAG over a policy it hasn't seen. A real A2A counterparty that
prepares the ground for a VeriClaim audit.

Run from vericlaim/:
  python helper_agents/policy_extractor/main.py --simulate   # extract + embed a sample policy
  python helper_agents/policy_extractor/main.py --serve        # CAP provider
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
from pathlib import Path

VERICLAIM_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(VERICLAIM_ROOT))

from helper_agents.common import llm_json, serve_provider  # noqa: E402

logger = logging.getLogger("vericlaim.policy_extractor")
SDK_KEY = os.getenv("POLICY_EXTRACTOR_SDK_KEY", "")

EXTRACT_SYSTEM = """You extract structured clauses from an insurance policy. Output ONLY JSON:
{"clauses": [{"clause_number": string, "clause_title": string, "clause_text": string,
              "clause_type": "coverage"|"exclusion"|"condition"|"exception"}]}
Quote clause_text close to verbatim. Keep clause_number as written (e.g. "§7.3"). No prose."""

SAMPLE_POLICY = """CRESTVIEW MUTUAL — AUTO PREFERRED (excerpt)
§2.1 Collision Coverage. Collision coverage applies to direct physical damage to the insured
vehicle from contact with another vehicle, object, or road surface, up to the policy limit after
deductible.
§7.3 Mechanical Failure Exclusion. Mechanical or electrical failure, wear and tear, or gradual
deterioration of any component is excluded from collision and comprehensive coverage.
§12.1 Collision-Caused Mechanical Failure Exception. Notwithstanding §7.3, mechanical failure
directly and proximately caused by a covered collision — as evidenced by police report or
certified mechanic report — is eligible for coverage under §2.1."""


async def extract_clauses(policy_text: str) -> list[dict]:
    """Policy text -> list of structured clause dicts."""
    data = await llm_json(EXTRACT_SYSTEM, f"Policy text:\n{policy_text}\n\nReturn the clauses JSON.")
    return data.get("clauses", [])


async def embed_and_store(clauses: list[dict], policy_type: str) -> int:
    """Embed clause texts and upsert them into policy_clauses (pgvector). Returns count stored."""
    sys.path.insert(0, str(VERICLAIM_ROOT / "agent"))
    from database.connection import AsyncSessionLocal  # noqa: PLC0415
    from database.models import PolicyClause  # noqa: PLC0415
    from rag.embedder import embed_batch  # noqa: PLC0415

    if not clauses:
        return 0
    embeddings = embed_batch([c["clause_text"] for c in clauses])
    async with AsyncSessionLocal() as session:
        session.add_all(
            PolicyClause(
                policy_type=policy_type,
                clause_number=c.get("clause_number"),
                clause_title=c.get("clause_title"),
                clause_text=c["clause_text"],
                clause_type=c.get("clause_type"),
                embedding=emb,
            )
            for c, emb in zip(clauses, embeddings)
        )
        await session.commit()
    return len(clauses)


async def _handler(requirements: dict) -> dict:
    """CAP provider handler: {"policy_text": ..., "policy_type": ...} -> embed clauses."""
    policy_text = requirements.get("policy_text")
    if not policy_text:
        return {"error": "missing required field 'policy_text'", "clauses_added": 0}
    clauses = await extract_clauses(policy_text)
    stored = await embed_and_store(clauses, requirements.get("policy_type", "Custom"))
    return {"clauses_added": stored, "clause_numbers": [c.get("clause_number") for c in clauses]}


async def _simulate() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
    print("Extracting clauses with the LLM...")
    clauses = await extract_clauses(SAMPLE_POLICY)
    print(f"Extracted {len(clauses)} clauses:", json.dumps(clauses, indent=2))
    print("\nEmbedding + storing into pgvector...")
    n = await embed_and_store(clauses, policy_type="Auto / Collision + Comprehensive (extracted)")
    print(f"Stored {n} clauses.")


if __name__ == "__main__":
    if "--serve" in sys.argv:
        logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
        asyncio.run(serve_provider(SDK_KEY, _handler, label="PolicyExtractor"))
    else:
        asyncio.run(_simulate())
