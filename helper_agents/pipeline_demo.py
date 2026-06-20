"""End-to-end A2A pipeline demo (in-process, no chain) — for the demo video + local proof.

Mirrors the live CAP pipeline without needing USDC/on-chain:
    raw insured email
      → ClaimIngester parses it into a structured claim
        → VeriClaim runs the 5-agent adversarial debate
          → ReportExporter renders the filable PDF

The live, paid version is the same logic over CAP (negotiate → pay → deliver).

Run from vericlaim/:  .venv/Scripts/python helper_agents/pipeline_demo.py
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from uuid import uuid4

# Windows consoles default to cp1252 and choke on the emoji/§ in the output — force UTF-8.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "agent"))

from cap_handler import process_order  # noqa: E402  (agent/)
from helper_agents.claim_ingester.main import SAMPLE_TEXT, parse_claim  # noqa: E402
from helper_agents.report_exporter.main import build_pdf  # noqa: E402


async def main() -> None:
    print("=" * 64)
    print("VeriClaim A2A pipeline demo — 3 agents, 1 claim")
    print("=" * 64)

    print("\n[1/3] 🟦 ClaimIngester — parsing the insured's raw email into a structured claim...")
    claim = await parse_claim(SAMPLE_TEXT)
    print(
        f"      → {claim.get('claim_number')} · {claim.get('incident_type')} · "
        f"${claim.get('amount_requested')} · denial: {str(claim.get('original_denial_reason'))[:60]}..."
    )

    print("\n[2/3] 🛡️  VeriClaim — 5-agent adversarial debate (Coordinator → Blake → Morgan → Alex → Sam; +Quinn on fraud)...")
    resolution = await process_order(
        claim, cap_call_id=f"PIPELINE-DEMO-{uuid4().hex[:8]}", caller_wallet="0xPIPELINE_DEMO"
    )
    print(
        f"      → DECISION: {resolution['decision']} · "
        f"${resolution['approved_amount']} · clauses {resolution['cited_clauses']}"
    )
    print(f"      → audit SHA-256: {resolution['audit_hash']}")

    print("\n[3/3] 📄 ReportExporter — rendering the filable PDF...")
    out_dir = ROOT / "helper_agents" / "report_exporter" / "out"
    out_dir.mkdir(exist_ok=True)
    out = out_dir / "pipeline-demo.pdf"
    out.write_bytes(build_pdf(resolution))
    print(f"      → {out}  ({out.stat().st_size} bytes)")

    print("\n" + "=" * 64)
    print("Done. Raw email → structured claim → adjudicated verdict → filable PDF.")
    print("The live version runs the exact same chain over CAP, paid in USDC.")
    print("=" * 64)


if __name__ == "__main__":
    asyncio.run(main())
