"""Alex — Devil's Advocate (Featherless / Hermes-2-Pro, failover to AI/ML API). Combative.

Ported from Recourse's alex_devils_advocate.py + the orchestrator's failover: if Featherless
stalls or errors, synthesize Alex's turn on the reliable provider so the debate never dead-airs.
Toolless — weaponizes the evidence already in the debate context.
"""
from __future__ import annotations

import logging
import re

from llm import complete, thread

logger = logging.getLogger("vericlaim.alex")

PROVIDER = "featherless"
FAILOVER = "aimlapi"

SYSTEM_PROMPT = """You are Alex, the Devil's Advocate for VeriClaim.
Your personality: combative, aggressive — you argue the insured's side, hard. But you are an
honest advocate, not a blind one.
You start sentences with "Wait." or "But—" when you disagree.
If the exclusion genuinely applies and no exception, ambiguity, or contrary evidence saves the
claim, you concede the denial is valid — plainly. You do not manufacture a defense that isn't there.
But you ALWAYS look for exceptions, ambiguities, and bad faith indicators first.

You work from the evidence already in the debate: the case file's supporting documents
(police reports, witness statements, mechanic reports) and the exact clauses Morgan quoted.

Your job: challenge the denial. Look for:
1. Exceptions to exclusions (especially §12.1-style carve-outs Morgan surfaced)
2. Ambiguous language that should be interpreted in the insured's favor
3. Inconsistencies between the denial reason and the supporting documentation
4. Bad faith indicators (adjuster using vague language, ignoring evidence)

Output:
- If challenging: start with "Wait." then lay out your argument
- Reference specific documents (police reports, witness statements) by name
- Cite the exception clause by number if it applies

Keep it under 250 words. Be assertive. Short punchy sentences mixed with technical analysis."""

# Neutral fallback — never fabricate specific clause numbers/evidence, since this turn may
# belong to ANY claim. Keeps the audit trail honest.
_NEUTRAL = (
    "Wait — this denial deserves scrutiny. Weigh whether any coverage clause or exception raised "
    "in the debate applies to this loss, and whether the supporting evidence contradicts the "
    "stated grounds, before the claim is dismissed on the exclusion alone."
)


def _collapse_repetition(text: str) -> str:
    """Drop consecutive duplicate sentences — a safety net for small-model repetition loops."""
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    out: list[str] = []
    prev_norm = None
    for p in parts:
        norm = re.sub(r"\s+", " ", p).strip().lower()
        if norm and norm == prev_norm:
            continue
        out.append(p.strip())
        prev_norm = norm
    return " ".join(out).strip()


async def run(context: list[tuple[str, str]]) -> str:
    """Alex's challenge, with failover from Featherless to the reliable provider."""
    user = (
        f"{thread(context)}\n\n"
        f"Alex, challenge the denial from the insured's perspective now."
    )
    try:
        text = _collapse_repetition(await complete(PROVIDER, SYSTEM_PROMPT, user))
        if text:
            return text
        logger.warning("Alex (featherless) returned empty; failing over to %s", FAILOVER)
    except Exception:
        logger.warning("Alex (featherless) failed; failing over to %s", FAILOVER)

    try:
        text = _collapse_repetition(await complete(FAILOVER, SYSTEM_PROMPT, user))
        if text:
            return text
    except Exception:
        logger.warning("Alex failover (%s) also failed; using a neutral placeholder", FAILOVER)
    return _NEUTRAL
