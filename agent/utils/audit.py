"""SHA-256 audit trail over the WHOLE resolution. Ported from orchestrator._finalize.

Tamper-evident: the hash covers the claim input, the ordered debate transcript, AND the final
decision + amount — so any later edit to any of them changes the fingerprint.
"""
from __future__ import annotations

import hashlib
import json


def hash_resolution(
    claim_input: dict,
    turns: list[tuple[str, str]],
    decision: str,
    approved_amount: float | None,
) -> dict:
    """SHA-256 over the full resolution: claim input + ordered transcript + decision + amount.

    `turns` is [(slug, content), ...]. Returns the audit_trail dict embedded in the resolution.
    """
    blob = json.dumps(
        {
            "claim_input": claim_input,
            "transcript": [{"agent": slug, "content": content} for slug, content in turns],
            "decision": decision,
            "approved_amount": approved_amount,
        },
        sort_keys=True,
        default=str,
    )
    digest = hashlib.sha256(blob.encode("utf-8")).hexdigest()
    return {
        "sha256": digest,
        "message_count": len(turns),
        "hash_algorithm": "sha256",
        "covers": ["claim_input", "transcript", "decision", "approved_amount"],
    }
