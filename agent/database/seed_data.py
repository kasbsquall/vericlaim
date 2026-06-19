"""Seed the demo data for VeriClaim.

Idempotent — re-runnable. Applies schema.sql, wipes existing rows, then inserts the
Crestview Mutual policy clauses (with embeddings) into policy_clauses. Unlike Recourse,
VeriClaim has no claims/policies tables — a claim arrives as CAP *input* — so the David
Chen demo claim is emitted as a sample payload (sample_claim.json) for driving the demo.

Run from the vericlaim/ directory:
    python agent/database/seed_data.py
"""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

# Allow `python agent/database/seed_data.py` from vericlaim/ to resolve `config`, `database`, `rag`.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text  # noqa: E402

from database.connection import AsyncSessionLocal, engine  # noqa: E402
from database.models import PolicyClause  # noqa: E402
from rag.embedder import embed_batch  # noqa: E402

SCHEMA_FILE = Path(__file__).resolve().parent / "schema.sql"
SAMPLE_CLAIM_FILE = Path(__file__).resolve().parent / "sample_claim.json"

POLICY_TYPE = "Auto / Collision + Comprehensive"

# Crestview Mutual "Auto Preferred" clauses — the §7.3 exclusion vs §12.1 exception the
# panel debates. Ported verbatim from Recourse's seed_data.py.
CLAUSES: list[dict] = [
    {
        "clause_number": "§2.1",
        "clause_title": "Collision Coverage",
        "clause_type": "coverage",
        "clause_text": (
            "Collision coverage applies to direct physical damage to the insured "
            "vehicle resulting from contact with another vehicle, object, or road "
            "surface, up to the policy limit after deductible."
        ),
    },
    {
        "clause_number": "§5.2",
        "clause_title": "Comprehensive Coverage",
        "clause_type": "coverage",
        "clause_text": (
            "Comprehensive coverage applies to non-collision losses including theft, "
            "vandalism, fire, flood, and falling objects."
        ),
    },
    {
        "clause_number": "§7.3",
        "clause_title": "Mechanical Failure Exclusion",
        "clause_type": "exclusion",
        "clause_text": (
            "Mechanical failure, electrical failure, wear and tear, or gradual "
            "deterioration of any vehicle component is expressly excluded from both "
            "collision and comprehensive coverage, regardless of when such failure "
            "manifests."
        ),
    },
    {
        "clause_number": "§7.4",
        "clause_title": "General Exclusions",
        "clause_type": "exclusion",
        "clause_text": (
            "Intentional damage, racing, or use of the vehicle for commercial "
            "purposes not disclosed at policy inception are excluded."
        ),
    },
    {
        "clause_number": "§9.1",
        "clause_title": "Claim Filing Conditions",
        "clause_type": "condition",
        "clause_text": (
            "Insured must file a claim within 30 days of the loss event. Supporting "
            "documentation including police reports, photographs, and repair estimates "
            "must be submitted within 60 days."
        ),
    },
    {
        "clause_number": "§12.1",
        "clause_title": "Collision-Caused Mechanical Failure Exception",
        "clause_type": "exception",
        "clause_text": (
            "Notwithstanding §7.3, mechanical or electrical failure that is directly "
            "and proximately caused by a covered collision event — as evidenced by "
            "police report, independent adjuster assessment, or certified mechanic "
            "report — shall be considered eligible for coverage under §2.1."
        ),
    },
]

# David Chen demo claim — the CAP call *input* (not a DB row). Matches the payload schema
# VeriClaim's debate engine consumes. The `policy` block carries the financials the engine
# needs (no policies table here); deductible 0 so the payout equals the requested $12,000,
# matching the demo narrative's "APPROVED — $12,000".
DEMO_CLAIM: dict = {
    "claim_number": "CLM-2024-04471",
    "policy_id": "CPP-2024-8821",
    "policy": {
        "policy_type": POLICY_TYPE,
        "insured_name": "David Chen",
        "insurance_company": "Crestview Mutual Insurance",
        "coverage_limit": 50000.00,
        "deductible": 0.00,
    },
    "incident_type": "collision",
    "incident_description": (
        "Vehicle struck guardrail at approximately 35 mph on I-95 North near Fort Lauderdale, FL. "
        "Airbags deployed. Front-end and engine compartment sustained severe damage. Engine seized "
        "following impact. Police report FHP-2024-10153 documents the accident. Witness statement "
        "from Marcus T. (FHP report page 2) confirms the vehicle lost control upon guardrail "
        "contact before the engine ceased operation."
    ),
    "original_denial_reason": (
        "Claim denied per §7.3 — Mechanical Failure Exclusion. Adjuster assessment indicates "
        "mechanical failure preceded the collision event."
    ),
    "amount_requested": 12000.00,
    "supporting_docs": [
        {
            "type": "police_report",
            "ref": "FHP-2024-10153",
            "summary": (
                "Collision with guardrail on I-95. Witness confirms vehicle was in motion when "
                "guardrail contact occurred. Engine failure documented post-impact."
            ),
        },
        {
            "type": "mechanic_report",
            "ref": "BM-AUTO-2024-089",
            "summary": (
                "Engine seized due to catastrophic impact damage to oil pan and crankshaft. "
                "Failure consistent with high-force collision, not pre-existing mechanical issue."
            ),
        },
        {
            "type": "photos",
            "ref": "CLM-2024-04471-imgs",
            "summary": "4 photos showing front-end crushing consistent with 35 mph guardrail impact.",
        },
    ],
}


async def apply_schema() -> None:
    """Run schema.sql statement-by-statement (asyncpg can't batch-execute)."""
    sql = SCHEMA_FILE.read_text(encoding="utf-8")
    statements = [s.strip() for s in sql.split(";") if s.strip()]
    async with engine.begin() as conn:
        for stmt in statements:
            await conn.exec_driver_sql(stmt)
    print(f"  schema applied ({len(statements)} statements)")


async def wipe() -> None:
    async with engine.begin() as conn:
        await conn.execute(
            text("TRUNCATE verifications, policy_clauses RESTART IDENTITY CASCADE")
        )
    print("  existing data wiped")


async def seed() -> None:
    print("Embedding clauses (loads the model on first run, may take a moment)...")
    embeddings = embed_batch([c["clause_text"] for c in CLAUSES])
    print(f"  {len(embeddings)} embeddings generated ({len(embeddings[0])} dims)")

    async with AsyncSessionLocal() as session:
        session.add_all(
            PolicyClause(
                policy_type=POLICY_TYPE,
                clause_number=c["clause_number"],
                clause_title=c["clause_title"],
                clause_text=c["clause_text"],
                clause_type=c["clause_type"],
                embedding=emb,
            )
            for c, emb in zip(CLAUSES, embeddings)
        )
        await session.commit()
        print(f"  inserted: {len(CLAUSES)} policy clauses ({POLICY_TYPE})")

    SAMPLE_CLAIM_FILE.write_text(json.dumps(DEMO_CLAIM, indent=2), encoding="utf-8")
    print(f"  wrote demo claim payload -> {SAMPLE_CLAIM_FILE.name}")


async def main() -> None:
    print("=== VeriClaim seed ===")
    await apply_schema()
    await wipe()
    await seed()
    await engine.dispose()
    print("Done. Clause corpus ready; sample_claim.json is the David Chen demo CAP input.")


if __name__ == "__main__":
    asyncio.run(main())
