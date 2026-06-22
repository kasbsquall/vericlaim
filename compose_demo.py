"""Demo: VeriClaim composes on-chain — for ONE claim it hires two specialist CAP agents.

The claim cites a policy VeriClaim has never seen (Acme Renters Protect v2). So, driven by the
case, VeriClaim:
  1. HIRES PolicyExtractor on-chain to ingest the policy text into its RAG corpus,
  2. runs the adversarial debate (now grounded in the freshly-ingested §11.4 exception),
  3. HIRES ReportExporter on-chain to render the verdict into a submittable PDF.
One "hire VeriClaim" call -> a real on-chain A2A DAG, driven by the case.

Prereqs for the REAL on-chain run:
  1. Run the two specialists as CAP providers (separate terminals):
       python helper_agents/policy_extractor/main.py --serve
       python helper_agents/report_exporter/main.py --serve
  2. In .env set: VERICLAIM_COMPOSE=1, POLICY_EXTRACTOR_SERVICE_ID=..., REPORT_EXPORTER_SERVICE_ID=...
     and make sure VeriClaim's wallet holds ~0.20 USDC (two $0.05 hires + gas).
Then:
       python compose_demo.py
"""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "agent"))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env")
from cap_handler import process_order  # noqa: E402


async def main() -> None:
    claim = json.loads(
        (ROOT / "agent" / "database" / "sample_claim_compose.json").read_text(encoding="utf-8")
    )
    print("VeriClaim processing a claim on an UNSEEN policy (Acme Renters Protect v2)...\n")
    r = await process_order(claim, cap_call_id="COMPOSE-DEMO", caller_wallet="0xDEMO")
    print(f"DECISION: {r['decision']}   amount: {r['approved_amount']}")
    recruited = r.get("recruited_agents")
    if recruited:
        print("\nON-CHAIN A2A HIRES BY VERICLAIM (case-driven):")
        for x in recruited:
            print(f"  • {x['agent']:16} order={x['order_id']}   ({x['reason']})")
    else:
        print(
            "\n(no recruitment recorded — set VERICLAIM_COMPOSE=1, the two SERVICE_IDs, and make "
            "sure PolicyExtractor + ReportExporter are running as providers.)"
        )


if __name__ == "__main__":
    asyncio.run(main())
