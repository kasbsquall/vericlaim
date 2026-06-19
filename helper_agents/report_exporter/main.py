"""ReportExporter (CAP agent, $0.05 USDC) — Track: Creator & Content Ops.

Takes a VeriClaim resolution JSON -> renders a formatted PDF (decision, legal reasoning, cited
clauses, SHA-256 audit trail) the insured can submit. A real A2A counterparty hired after VeriClaim.

Run from vericlaim/:
  python helper_agents/report_exporter/main.py --simulate   # writes a sample PDF locally
  python helper_agents/report_exporter/main.py --serve       # CAP provider (returns base64 PDF)
"""
from __future__ import annotations

import asyncio
import base64
import io
import logging
import os
import sys
from pathlib import Path

VERICLAIM_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(VERICLAIM_ROOT))

from helper_agents.common import serve_provider  # noqa: E402

logger = logging.getLogger("vericlaim.report_exporter")
SDK_KEY = os.getenv("REPORT_EXPORTER_SDK_KEY", "")

NAVY = "#09285C"
BLUE = "#126CEB"

SAMPLE_RESOLUTION = {
    "decision": "APPROVED",
    "approved_amount": 12000.0,
    "reasoning": (
        "DECISION: APPROVED\nAPPROVED AMOUNT: $12,000.00\nLEGAL REASONING:\nThe claim is approved "
        "under §12.1, an exception to §7.3 for mechanical failure directly caused by a covered "
        "collision, as evidenced by the mechanic report. CONFIDENCE: HIGH"
    ),
    "cited_clauses": ["§7.3", "§12.1"],
    "audit_hash": "d539eca870603fa065249a016372a45849564863aaa406feeae28531ba40dfda",
    "agents_involved": ["Blake", "Morgan", "Alex", "Sam"],
}


def build_pdf(resolution: dict) -> bytes:
    """Render the resolution to a formatted PDF, returned as bytes."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import LETTER
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=LETTER, topMargin=0.9 * inch, bottomMargin=0.8 * inch)
    styles = getSampleStyleSheet()
    h = ParagraphStyle("h", parent=styles["Title"], textColor=colors.HexColor(NAVY), fontSize=22)
    lbl = ParagraphStyle("lbl", parent=styles["Heading4"], textColor=colors.HexColor(BLUE), spaceAfter=2)
    body = ParagraphStyle("body", parent=styles["BodyText"], fontSize=10.5, leading=15)
    mono = ParagraphStyle("mono", parent=styles["BodyText"], fontName="Courier", fontSize=8, textColor=colors.grey)

    decision = resolution.get("decision", "—")
    amount = resolution.get("approved_amount")
    amount_str = f"${float(amount):,.2f}" if amount is not None else "—"

    story = [
        Paragraph("VeriClaim — Claim Resolution", h),
        Spacer(1, 4),
        Paragraph("Adversarial AI audit · legally-defensible resolution", body),
        Spacer(1, 16),
        Paragraph("DECISION", lbl),
        Paragraph(f"<b>{decision}</b> &nbsp;·&nbsp; Approved amount: <b>{amount_str}</b>", body),
        Spacer(1, 12),
        Paragraph("LEGAL REASONING", lbl),
        Paragraph(str(resolution.get("reasoning", "")).replace("\n", "<br/>"), body),
        Spacer(1, 12),
        Paragraph("CITED CLAUSES", lbl),
        Paragraph(", ".join(resolution.get("cited_clauses", [])) or "—", body),
        Spacer(1, 12),
        Paragraph("PANEL", lbl),
        Paragraph(", ".join(resolution.get("agents_involved", [])) or "—", body),
        Spacer(1, 20),
        Paragraph("AUDIT TRAIL (SHA-256)", lbl),
        Paragraph(resolution.get("audit_hash", "—"), mono),
    ]
    doc.build(story)
    return buf.getvalue()


async def _handler(requirements: dict) -> dict:
    """CAP provider handler: resolution JSON -> base64 PDF deliverable.

    (Production note: for large files use client.upload_file -> deliverable_url instead of base64.)
    """
    pdf = build_pdf(requirements)
    name = f"vericlaim-{requirements.get('decision', 'resolution')}.pdf".lower()
    return {"filename": name, "content_type": "application/pdf",
            "pdf_base64": base64.b64encode(pdf).decode("ascii")}


def _simulate() -> None:
    out_dir = VERICLAIM_ROOT / "helper_agents" / "report_exporter" / "out"
    out_dir.mkdir(exist_ok=True)
    out = out_dir / "sample-resolution.pdf"
    out.write_bytes(build_pdf(SAMPLE_RESOLUTION))
    print(f"Wrote {out} ({out.stat().st_size} bytes)")


if __name__ == "__main__":
    if "--serve" in sys.argv:
        logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
        asyncio.run(serve_provider(SDK_KEY, _handler, label="ReportExporter"))
    else:
        _simulate()
