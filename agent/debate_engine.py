"""The 5-agent adversarial debate, run in-process WITHOUT Band.

Adapts Recourse's services/orchestrator.py: the agents coordinate through accumulated context
threaded forward by hand, instead of through Band rooms over WebSocket.

    Case File -> Blake -> Morgan(+RAG) -> Alex -> Sam(+financials) -> DebateResult

Reused from the orchestrator: Sam's resolution parser (DECISION / APPROVED AMOUNT / §clause
regexes) and the SHA-256 audit hash.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation

from agents import alex, blake, coordinator, morgan, quinn, sam
from database.connection import AsyncSessionLocal
from utils.audit import hash_resolution

# Sam's structured resolution parsing (ported verbatim from the orchestrator).
_DECISION_RE = re.compile(r"DECISION:\s*\**\s*(APPROVED|DENIED|PARTIAL)", re.IGNORECASE)
_AMOUNT_RE = re.compile(r"APPROVED AMOUNT:\s*\**\s*\$?([\d,]+(?:\.\d{1,2})?)", re.IGNORECASE)
_CLAUSE_RE = re.compile(r"§\s?(\d+\.\d+)")


def _strip_fences(text: str) -> str:
    """Drop a leading ```lang fence and trailing ``` some models wrap around the block, so the
    resolution parser sees plain text (otherwise a fenced reply parses as UNCLEAR)."""
    t = text.strip()
    if t.startswith("```"):
        t = t.split("\n", 1)[-1]
        if t.rstrip().endswith("```"):
            t = t.rstrip()[:-3]
    return t.strip()


def _parse_resolution(text: str) -> dict:
    decision = (m.group(1).upper() if (m := _DECISION_RE.search(text)) else "UNCLEAR")
    amount = None
    if (m := _AMOUNT_RE.search(text)):
        try:
            amount = Decimal(m.group(1).replace(",", ""))
        except InvalidOperation:
            amount = None
    clauses = sorted({f"§{c}" for c in _CLAUSE_RE.findall(text)})
    return {"decision": decision, "approved_amount": amount, "cited_clauses": clauses}


@dataclass
class DebateResult:
    """The full outcome of one verification — what CAP returns to the caller."""

    decision: str
    approved_amount: float | None
    legal_reasoning: str
    cited_clauses: list[str]
    audit_hash: str
    transcript: list[dict] = field(default_factory=list)  # [{slug, agent, content}, ...]
    agents_involved: list[str] = field(default_factory=list)

    @property
    def transcript_summary(self) -> str:
        return " | ".join(
            f"{t['agent']}: {t['content'][:140].strip()}…"
            if len(t["content"]) > 140 else f"{t['agent']}: {t['content'].strip()}"
            for t in self.transcript
            if t["slug"] != "coordinator"
        )


def _retrieval_query(payload: dict) -> str:
    """What Morgan searches the clause corpus for: the denial grounds + the incident."""
    return " ".join(
        str(payload.get(k, ""))
        for k in ("original_denial_reason", "incident_type", "incident_description")
    ).strip()


# Dynamic SIU recruitment triggers — kept specific so they fire only on fraud/misrepresentation
# denials, not ordinary coverage disputes (the David Chen collision never trips them; a denial
# alleging "undisclosed commercial / rideshare use" does).
_FRAUD_TRIGGERS = (
    "rideshare", "undisclosed", "commercial purpose", "commercial use", "staged",
    "false statement", "material misstatement", "misrepresentation", "concealment", "fraud",
)


def _alleges_fraud(payload: dict) -> bool:
    """True when the denial alleges fraud/misrepresentation — recruits Quinn (SIU) into the debate."""
    blob = " ".join(
        str(payload.get(k, "")) for k in ("original_denial_reason", "incident_description")
    ).lower()
    return any(t in blob for t in _FRAUD_TRIGGERS)


async def run_debate(payload: dict) -> DebateResult:
    """Drive the full adjudication for a CAP claim payload and return the result."""
    policy = payload.get("policy") or {}
    financials = {
        "amount_requested": payload.get("amount_requested", 0.0),
        "deductible": policy.get("deductible", 0.0),
    }
    policy_type = policy.get("policy_type")

    brief = coordinator.build_case_brief(payload)
    context: list[tuple[str, str]] = [("Case File", brief)]
    # (slug, display, content) — ordered transcript for persistence + hashing.
    transcript: list[dict] = [{"slug": "coordinator", "agent": "Coordinator", "content": brief}]

    async with AsyncSessionLocal() as session:
        blake_text = await blake.run(context)
        context.append(("Blake", blake_text))
        transcript.append({"slug": "blake", "agent": "Blake", "content": blake_text})

        morgan_text = await morgan.run(
            session, context, _retrieval_query(payload), policy_type=policy_type
        )
        context.append(("Morgan", morgan_text))
        transcript.append({"slug": "morgan", "agent": "Morgan", "content": morgan_text})

    alex_text = await alex.run(context)
    context.append(("Alex", alex_text))
    transcript.append({"slug": "alex", "agent": "Alex", "content": alex_text})

    # Dynamic 6th agent: recruit Quinn (SIU) into the debate ONLY when fraud/misrepresentation is
    # alleged. Otherwise the standing 5-agent panel is unchanged.
    if _alleges_fraud(payload):
        quinn_text = await quinn.run(context)
        context.append(("Quinn", quinn_text))
        transcript.append({"slug": "quinn", "agent": "Quinn", "content": quinn_text})

    sam_text = _strip_fences(await sam.run(context, financials))
    context.append(("Sam", sam_text))
    transcript.append({"slug": "sam", "agent": "Sam", "content": sam_text})

    parsed = _parse_resolution(sam_text)
    approved_amount = (
        float(parsed["approved_amount"]) if parsed["approved_amount"] is not None else None
    )
    audit = hash_resolution(
        payload,
        [(t["slug"], t["content"]) for t in transcript],
        parsed["decision"],
        approved_amount,
    )

    return DebateResult(
        decision=parsed["decision"],
        approved_amount=approved_amount,
        legal_reasoning=sam_text,
        cited_clauses=parsed["cited_clauses"],
        audit_hash=audit["sha256"],
        transcript=transcript,
        agents_involved=[t["agent"] for t in transcript if t["slug"] != "coordinator"],
    )


if __name__ == "__main__":
    # Manual end-to-end check against the seeded demo claim.
    import asyncio
    import json
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    sample = Path(__file__).resolve().parent / "database" / "sample_claim.json"

    async def _main() -> None:
        payload = json.loads(sample.read_text(encoding="utf-8"))
        result = await run_debate(payload)
        print("\n================ DEBATE TRANSCRIPT ================")
        for t in result.transcript:
            print(f"\n--- {t['agent']} ---\n{t['content']}")
        print("\n================ RESULT ================")
        print(f"Decision:        {result.decision}")
        print(f"Approved amount: {result.approved_amount}")
        print(f"Cited clauses:   {result.cited_clauses}")
        print(f"Audit SHA-256:   {result.audit_hash}")

    asyncio.run(_main())
