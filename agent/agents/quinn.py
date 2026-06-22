"""🟪 Quinn — Special Investigations Unit (SIU) examiner (AI/ML API / GPT-4o).

Quinn is NOT a standing panelist. The debate engine RECRUITS Quinn dynamically — only when the
denial alleges fraud, misrepresentation, or a material inconsistency. Quinn examines whether that
allegation is actually substantiated by the evidence already in the debate, so a claim is never
upheld-denied on unproven suspicion. Ported from Recourse's quinn_siu_investigator.py (minus Band).
"""
from __future__ import annotations

import logging

from llm import complete, thread

logger = logging.getLogger("vericlaim.quinn")

PROVIDER = "aimlapi"

SYSTEM_PROMPT = """You are Quinn, the Special Investigations Unit (SIU) examiner for VeriClaim.
You are NOT a standing panelist — you are recruited into a case only when fraud, misrepresentation,
or a material inconsistency has been alleged. Your job: decide whether that allegation actually
holds up against the evidence already in the debate — weighing it BOTH ways. If the evidence
substantiates the allegation, say so plainly and that it supports upholding the denial. If it does
not, say it cannot, by itself, defeat coverage. The panel must neither uphold a denial on unproven
suspicion nor wave through a claim the evidence shows is fraudulent.

Work strictly from the record: the case file, the supporting documents, the original denial
reason, and what Blake, Morgan and Alex have said. Do NOT invent evidence.

Weigh the allegation against the facts — name the specific documents and findings that support or
undercut it (rideshare/trip logs, commercial markings, prior claims, motive, timing, forced entry,
origin/cause reports). Reference the relevant clause numbers the way the rest of the panel does
(the exclusion the insurer is invoking, and the coverage clause it would otherwise fall under). If
the allegation is not backed by real evidence, say plainly that it cannot, by itself, defeat coverage.

Write in plain, natural prose — like a sharp investigator briefing the panel, not a form. No labels
or headings. Keep it under 180 words."""

_NEUTRAL = (
    "The misrepresentation allegation is not corroborated by anything in the file — no "
    "documentation, records, or physical findings are offered to substantiate it. On the evidence "
    "in the record, an unproven suspicion cannot, by itself, defeat otherwise-valid coverage."
)


async def run(context: list[tuple[str, str]]) -> str:
    """Quinn's SIU finding on the fraud/misrepresentation allegation."""
    user = (
        f"{thread(context)}\n\n"
        f"Quinn, a fraud or misrepresentation allegation is in play. Examine whether it is actually "
        f"substantiated by the evidence already in the debate, and report your finding now."
    )
    try:
        text = await complete(PROVIDER, SYSTEM_PROMPT, user)
        if text:
            return text
    except Exception:
        logger.warning("Quinn (aimlapi) failed; using a neutral SIU finding")
    return _NEUTRAL
