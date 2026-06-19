"""Coordinator — renders the opening case file from a CAP claim payload.

In Recourse the Coordinator was a Band agent that opened the room; here it is a plain helper
the debate_engine calls. Turn sequencing lives in debate_engine.run_debate.
"""
from __future__ import annotations


def _fmt_amount(value) -> str:
    try:
        return f"${float(value):,.2f}"
    except (TypeError, ValueError):
        return str(value)


def build_case_brief(payload: dict) -> str:
    """Render the opening case file from a CAP claim payload (see sample_claim.json)."""
    policy = payload.get("policy") or {}
    docs = "\n".join(
        f"  - [{d.get('type')}] {d.get('ref')}: {d.get('summary')}"
        for d in (payload.get("supporting_docs") or [])
    ) or "  (none on file)"

    insured = policy.get("insured_name", "the insured")
    company = policy.get("insurance_company", "the insurer")
    policy_type = policy.get("policy_type", "policy")

    return (
        f"CASE FILE — Claim {payload.get('claim_number', 'N/A')} "
        f"(Policy {payload.get('policy_id', 'N/A')}, {insured}, {company} — {policy_type})\n"
        f"Incident: {payload.get('incident_type', 'incident')}.\n"
        f"{payload.get('incident_description', '')}\n"
        f"Amount requested: {_fmt_amount(payload.get('amount_requested'))}.\n"
        f"Policy financials: coverage limit {_fmt_amount(policy.get('coverage_limit'))}, "
        f"deductible {_fmt_amount(policy.get('deductible', 0))}.\n"
        f"ORIGINAL DENIAL: {payload.get('original_denial_reason', 'N/A')}\n"
        f"Supporting documents:\n{docs}\n\n"
        f"This denial is disputed. Blake, begin your coverage analysis."
    )
