"""Does the adversarial debate actually decide better than a single LLM?

Runs the same claims through (a) VeriClaim's 5/6-agent adversarial debate and (b) one strong
single-LLM adjudicator (GPT-4o, one shot), and prints the decisions side by side. The interesting
cases are denials that are *technically stated but wrong* — where a naive single call tends to
uphold the insurer's denial, while the adversarial panel (devil's advocate + RAG-grounded policy
analyst, + the SIU agent on fraud) surfaces the exception and overturns it.

Run from vericlaim/ (DB up):  .venv/Scripts/python eval/run_eval.py
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import sys
import time
from pathlib import Path
from uuid import uuid4

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "agent"))
from dotenv import load_dotenv

load_dotenv(ROOT / ".env")
from cap_handler import process_order  # noqa: E402
from debate_engine import _retrieval_query  # noqa: E402
from rag.retriever import search_clauses  # noqa: E402
from database.connection import AsyncSessionLocal  # noqa: E402

AIMLAPI_KEY = os.getenv("AIMLAPI_API_KEY", "")
AIMLAPI_BASE = os.getenv("AIMLAPI_BASE_URL", "https://api.aimlapi.com/v1")
AIMLAPI_MODEL = os.getenv("AIMLAPI_MODEL", "gpt-4o")

SINGLE_SYSTEM = (
    "You are a senior insurance claim adjudicator. Read the full claim JSON, including the "
    "original_denial_reason and supporting_docs. Decide whether the insurer's denial should STAND "
    "or be OVERTURNED, and the payable amount. Return ONLY JSON: "
    '{"decision":"APPROVED|DENIED|PARTIAL","approved_amount":number,"cited_clauses":["section x.y"],'
    '"reasoning":"one short paragraph"}'
)

CLAIMS = [
    ("Collision — denial cites §7.3 exclusion; §12.1 collision-exception applies", "sample_claim.json", "APPROVED"),
    ("Theft — denial alleges undisclosed rideshare (fraud), unsupported by evidence", "sample_claim_fraud.json", "APPROVED"),
    ("Mechanical failure — genuine wear-and-tear, no collision; §7.3 applies, no exception", "sample_claim_denied.json", "DENIED"),
    ("Commercial-use denial (§7.4) — overturned ONLY by the §12.3 de-minimis exception that lives in the policy corpus (RAG-required)", "sample_claim_rag_only.json", "APPROVED"),
]


async def single_llm(claim: dict) -> dict:
    async with httpx.AsyncClient(timeout=120) as c:
        r = await c.post(
            f"{AIMLAPI_BASE.rstrip('/')}/chat/completions",
            headers={"Authorization": f"Bearer {AIMLAPI_KEY}"},
            json={
                "model": AIMLAPI_MODEL,
                "temperature": 0,
                "messages": [
                    {"role": "system", "content": SINGLE_SYSTEM},
                    {"role": "user", "content": "Claim:\n" + json.dumps(claim, indent=2)},
                ],
            },
        )
        r.raise_for_status()
        txt = r.json()["choices"][0]["message"]["content"]
    m = re.search(r"\{.*\}", txt, re.DOTALL)
    return json.loads(m.group(0)) if m else {"decision": "UNCLEAR", "approved_amount": None, "cited_clauses": []}


async def single_llm_rag(claim: dict) -> dict:
    """Ablation arm: a single GPT-4o call GIVEN the same clauses Morgan's RAG retrieves — isolates
    how much of VeriClaim's edge is the retrieval vs the multi-agent debate itself."""
    policy_type = (claim.get("policy") or {}).get("policy_type")
    async with AsyncSessionLocal() as session:
        clauses = await search_clauses(session, _retrieval_query(claim), policy_type=policy_type, limit=5)
    corpus = "\n".join(
        f"{c['clause_number']} {c['clause_title']}: {c['clause_text']}" for c in clauses
    ) or "(no clauses retrieved)"
    async with httpx.AsyncClient(timeout=120) as c:
        r = await c.post(
            f"{AIMLAPI_BASE.rstrip('/')}/chat/completions",
            headers={"Authorization": f"Bearer {AIMLAPI_KEY}"},
            json={
                "model": AIMLAPI_MODEL,
                "temperature": 0,
                "messages": [
                    {"role": "system", "content": SINGLE_SYSTEM},
                    {"role": "user", "content": f"RETRIEVED POLICY CLAUSES:\n{corpus}\n\nClaim:\n" + json.dumps(claim, indent=2)},
                ],
            },
        )
        r.raise_for_status()
        txt = r.json()["choices"][0]["message"]["content"]
    m = re.search(r"\{.*\}", txt, re.DOTALL)
    return json.loads(m.group(0)) if m else {"decision": "UNCLEAR", "approved_amount": None, "cited_clauses": []}


async def main() -> None:
    results = []
    for title, fname, expected in CLAIMS:
        claim = json.loads((ROOT / "agent" / "database" / fname).read_text(encoding="utf-8"))
        debate = await process_order(claim, cap_call_id="EVAL-" + uuid4().hex[:8], caller_wallet="0xEVAL")
        single = await single_llm(claim)
        single_rag = await single_llm_rag(claim)
        print(f"\n=== {title}\n    (expected: {expected}) ===")
        print(f"  VeriClaim debate ({len(debate['agents_involved'])} agents): "
              f"{debate['decision']}  ${debate['approved_amount']}  clauses={debate['cited_clauses']}")
        print(f"  Single GPT-4o (no RAG):          "
              f"{single.get('decision')}  ${single.get('approved_amount')}  clauses={single.get('cited_clauses')}")
        print(f"  Single GPT-4o (+retrieved RAG):  "
              f"{single_rag.get('decision')}  ${single_rag.get('approved_amount')}  clauses={single_rag.get('cited_clauses')}")
        results.append({
            "case": title, "expected": expected,
            "debate": {"decision": debate["decision"], "amount": debate["approved_amount"],
                       "clauses": debate["cited_clauses"], "agents": debate["agents_involved"]},
            "single_llm": {"decision": single.get("decision"), "amount": single.get("approved_amount"),
                           "clauses": single.get("cited_clauses")},
            "single_llm_rag": {"decision": single_rag.get("decision"), "amount": single_rag.get("approved_amount"),
                               "clauses": single_rag.get("cited_clauses")},
        })
    out = ROOT / "eval" / "results.json"
    out.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    n = len(results)
    d_correct = sum(1 for r in results if r["debate"]["decision"] == r["expected"])
    s_correct = sum(1 for r in results if r["single_llm"]["decision"] == r["expected"])
    sr_correct = sum(1 for r in results if r["single_llm_rag"]["decision"] == r["expected"])
    print(f"\nCorrect decisions — VeriClaim debate: {d_correct}/{n}  ·  single GPT-4o (no RAG): {s_correct}/{n}  ·  single GPT-4o (+RAG): {sr_correct}/{n}")
    print(f"saved {out}")


if __name__ == "__main__":
    asyncio.run(main())
