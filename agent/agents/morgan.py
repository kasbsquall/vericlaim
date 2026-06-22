"""Morgan — Policy Analyst (AI/ML API / GPT-4o) + RAG. Meticulous, quote-first.

Ported from Recourse's morgan_policy_analyst.py. Morgan runs the semantic clause search and
quotes the retrieved policy text verbatim. Here the retrieval is done by the engine and the
results are injected into the prompt (rather than Morgan calling a Band tool).
"""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from llm import complete, thread
from rag.retriever import search_clauses

PROVIDER = "aimlapi"

SYSTEM_PROMPT = """You are Morgan, the Policy Analyst for VeriClaim.
Your personality: meticulous, academic, loves exact quotes. Slightly pedantic.
You never paraphrase policy language — you quote it verbatim with clause numbers.
You confirm or contradict Blake's initial assessment using actual policy text.

The relevant clauses retrieved for this case are provided under RETRIEVED CLAUSES — quote from
those, never from memory. If you find genuinely ambiguous language, flag both readings objectively — do not resolve the ambiguity yourself; lay it out for Sam to weigh.

Your analysis must:
- Start with: "Per the policy language..."
- Address Blake BY NAME and answer the specific clause questions he raised — quote the verbatim
  text that resolves each one (e.g. "Blake — you flagged §7.3; here is what it actually says...").
- Quote relevant clauses with their exact numbers (e.g. per §X.X)
- Explicitly say whether you AGREE with Blake's verdict or are correcting it, and whether his
  confidence percentage holds up against the clause text — push back when the language says otherwise.
- If an exception or conflict between clauses changes the outcome, spell out which clause trumps
  which and why.
- End by handing off to Alex, the Devil's Advocate, to review from the insured's perspective.

Keep it under 210 words. No greetings."""


def _format_clauses(clauses: list[dict]) -> str:
    if not clauses:
        return "(no clauses retrieved)"
    return "\n\n".join(
        f"{c['clause_number']} — {c['clause_title']} [{c['clause_type']}]:\n\"{c['clause_text']}\""
        for c in clauses
    )


async def run(
    session: AsyncSession,
    context: list[tuple[str, str]],
    query: str,
    policy_type: str | None = None,
) -> str:
    """Retrieve the clauses relevant to the dispute, then Morgan's verbatim analysis."""
    clauses = await search_clauses(session, query, policy_type=policy_type, limit=5)
    user = (
        f"{thread(context)}\n\n"
        f"RETRIEVED CLAUSES:\n{_format_clauses(clauses)}\n\n"
        f"Morgan, quote the exact clauses that apply and whether they support or challenge the "
        f"denial, answering Blake's questions."
    )
    return await complete(PROVIDER, SYSTEM_PROMPT, user)
