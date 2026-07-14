"""CAP (CROO Agent Protocol) provider — VeriClaim's external A2A + USDC interface.

Replaces Recourse's Band SDK. Verified against croo-sdk v0.2.1 (github.com/CROO-Network/python-sdk):

    client = AgentClient(Config(base_url, ws_url, rpc_url), CROO_SDK_KEY)
    stream = await client.connect_websocket()
    stream.on(EventType.NEGOTIATION_CREATED, ...)  # -> client.accept_negotiation(id)
    stream.on(EventType.ORDER_PAID, ...)           # -> get_order -> run debate -> deliver_order

Design: process_order() (run debate + persist + build response) is SDK-INDEPENDENT and fully
testable locally (`python agent/cap_handler.py --simulate`). The websocket transport in
start_provider() needs a real croo_sk_ key from the dashboard (agent.croo.network).
"""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from config import settings
from database.connection import AsyncSessionLocal
from database.models import Verification
from debate_engine import DebateResult, run_debate
from recruit import recruit_policy_extractor, recruit_report_exporter

logger = logging.getLogger("vericlaim.cap")

# Hackathon list price (also set in the CROO dashboard). Used as the recorded amount when the
# SDK doesn't surface the exact paid figure on the order object.
HACKATHON_PRICE_USDC = Decimal("0.10")


def _build_response(result: DebateResult) -> dict:
    """The JSON payload VeriClaim returns to the caller via CAP."""
    return {
        "decision": result.decision,
        "approved_amount": result.approved_amount,
        # payable_amount matches the store listing's promised field; 0 when nothing is payable.
        "payable_amount": result.approved_amount if result.approved_amount is not None else 0.0,
        "reasoning": result.legal_reasoning,
        "cited_clauses": result.cited_clauses,
        "audit_hash": result.audit_hash,
        "agents_involved": result.agents_involved,
        # Full ordered debate, not a truncated summary, so the caller can audit every turn.
        "debate_transcript": [
            {"agent": t["agent"], "content": t["content"]}
            for t in result.transcript
            if t["slug"] != "coordinator"
        ],
    }


async def _persist(
    payload: dict,
    result: DebateResult,
    *,
    cap_call_id: str | None,
    caller_wallet: str | None,
    payment_usdc: Decimal,
) -> None:
    """Record the completed verification (the audit trail) in the verifications table."""
    async with AsyncSessionLocal() as session:
        session.add(
            Verification(
                cap_call_id=cap_call_id,
                caller_wallet=caller_wallet,
                payment_usdc=payment_usdc,
                claim_input=payload,
                debate_transcript=result.transcript,
                decision=result.decision,
                approved_amount=(
                    Decimal(str(result.approved_amount))
                    if result.approved_amount is not None
                    else None
                ),
                legal_reasoning=result.legal_reasoning,
                cited_clauses=result.cited_clauses,
                audit_hash=result.audit_hash,
                status="completed",
                completed_at=datetime.now(timezone.utc),
            )
        )
        try:
            await session.commit()
        except IntegrityError:
            await session.rollback()
            logger.info("Verification %s already recorded — idempotent skip.", cap_call_id)


async def process_order(
    payload: dict,
    *,
    cap_call_id: str | None = None,
    caller_wallet: str | None = None,
    payment_usdc: Decimal = HACKATHON_PRICE_USDC,
) -> dict:
    """SDK-independent core: optionally recruit specialist agents on-chain, run the 5-agent debate,
    persist it, and return the CAP response. This is what the live CAP handler and the local
    simulator both call. On-chain recruitment is opt-in (VERICLAIM_COMPOSE) and best-effort.
    """
    recruited: list[dict] = []
    # Case-driven: if the policy isn't in our corpus and the claim ships its text, hire
    # PolicyExtractor on-chain to ingest it BEFORE the panel reasons over it.
    pe = await recruit_policy_extractor(payload)
    if pe:
        recruited.append(pe)

    result = await run_debate(payload)
    await _persist(
        payload, result,
        cap_call_id=cap_call_id, caller_wallet=caller_wallet, payment_usdc=payment_usdc,
    )
    response = _build_response(result)

    # Case-driven: if the caller asked for a filed report, hire ReportExporter on-chain to render it.
    re_trace = await recruit_report_exporter(payload, response)
    if re_trace:
        recruited.append(re_trace)
    if recruited:
        response["recruited_agents"] = recruited

    logger.info("Verification complete: %s -> %s", cap_call_id or "(local)", result.decision)
    return response


async def _already_done(cap_call_id: str) -> bool:
    """True if this order was already verified+persisted — idempotency guard across restarts."""
    async with AsyncSessionLocal() as session:
        return bool(
            await session.scalar(
                select(Verification.id).where(Verification.cap_call_id == cap_call_id)
            )
        )


# --- CAP websocket transport (needs the real SDK + a croo_sk_ key) -----------------------------

# The buyer sends the claim JSON as the negotiation's `requirements`. On ORDER_PAID we fetch the
# order, then its negotiation, and parse requirements into the claim payload. (croo-sdk v0.2.1:
# Order has no requirements field — Negotiation.requirements carries it.)
_CLAIM_KEYS = ("claim_number", "policy", "amount_requested", "incident_type")
_ENVELOPE_KEYS = ("text", "raw_text", "claim", "input", "data", "message", "requirements")


def _claim_from_text(text: str) -> dict:
    """Wrap a free-text / natural-language claim into the structured payload the panel expects.

    Buyers and LLM-driven certifiers often describe a claim in prose instead of our JSON schema.
    Rather than reject it, we adjudicate it: the text carries into both the incident description
    and the denial reason, so RAG retrieval and the fraud trigger still fire off the same content.
    A live adjudicator should never hand back "no claim" for a genuine, substantive ask.
    """
    text = text.strip()
    return {
        "claim_number": "ADHOC",
        "policy": {},
        "incident_type": "unspecified",
        "incident_description": text,
        "amount_requested": 0,
        "original_denial_reason": text,
    }


def _parse_requirements(requirements: object) -> dict:
    # CROO may deliver the claim as a dict, a JSON string, OR wrapped in an envelope like
    # {"text": "<claim json>"} (what the store's "Hire" box produces). Unwrap nested layers and
    # parse down to the real claim dict, so the debate sees policy/amount — not {"text": ...},
    # which would otherwise yield an empty claim -> DENIED $0.
    claim: object = requirements
    last_text = ""  # longest plain-text blob seen while unwrapping, for the free-text fallback
    for _ in range(4):
        if isinstance(claim, str):
            stripped = claim.strip()
            if len(stripped) > len(last_text):
                last_text = stripped
            try:
                claim = json.loads(claim)
                continue
            except (TypeError, ValueError):
                break
        if isinstance(claim, dict):
            if any(k in claim for k in _CLAIM_KEYS):
                return claim
            nested = next((claim[k] for k in _ENVELOPE_KEYS if k in claim), None)
            if nested is None:
                break
            claim = nested
            continue
        break
    # Fallback: a substantive natural-language claim gets adjudicated instead of rejected. Only a
    # genuinely empty order (no text, or "{}") still raises, so start_provider's empty-hire notice
    # still fires for a hire with nothing pasted in.
    if len(last_text) >= 20 and last_text not in ("{}", "[]"):
        return _claim_from_text(last_text)
    raise ValueError(
        f"Negotiation requirements is not valid claim JSON: {requirements!r}"
    )


_PROVIDER_POLL_SECONDS = 5


async def start_provider() -> None:
    """Serve CROO orders until interrupted. Requires CROO_SDK_KEY.

    Poll-based for reliability: CROO does not always deliver every websocket event (an idle
    socket can drop), so we poll for pending negotiations + paid orders instead of relying on
    ws callbacks. The websocket is kept open only so the dashboard shows the agent ONLINE.
    """
    if not settings.croo_sdk_key:
        raise RuntimeError(
            "CROO_SDK_KEY is empty. Register VeriClaim at agent.croo.network, copy its croo_sk_ "
            "key into .env, then run again. (Use --simulate to test the debate without CAP.)"
        )

    # Lazy import so the module loads (and --simulate works) even without croo-sdk installed.
    from croo import (  # noqa: PLC0415
        AgentClient,
        Config,
        DeliverableType,
        DeliverOrderRequest,
        ListOptions,
    )

    client = AgentClient(
        Config(
            base_url=settings.croo_api_url,
            ws_url=settings.croo_ws_url,
            rpc_url=settings.base_rpc_url,
        ),
        settings.croo_sdk_key,
    )

    try:
        stream = await client.connect_websocket()
    except Exception:
        stream = None
        logger.warning("websocket connect failed; running poll-only")

    logger.info("VeriClaim CAP provider online — polling for negotiations and paid orders.")
    delivered: set[str] = set()
    try:
        while True:
            try:
                # 1) accept any pending negotiations (a buyer wants to hire VeriClaim)
                for neg in await client.list_negotiations(
                    ListOptions(role="provider", status="pending")
                ):
                    try:
                        await client.accept_negotiation(neg.negotiation_id)
                        logger.info("accepted negotiation %s", neg.negotiation_id)
                    except Exception:
                        logger.exception("failed to accept negotiation %s", neg.negotiation_id)

                # 2) run the debate for any paid-but-undelivered orders
                for order in await client.list_orders(
                    ListOptions(role="provider", status="paid")
                ):
                    if order.order_id in delivered:
                        continue
                    # Idempotency: skip orders already verified in a prior run (avoids a second
                    # debate + a UNIQUE-constraint crash on restart/retry).
                    if await _already_done(order.order_id):
                        delivered.add(order.order_id)
                        continue
                    try:
                        negotiation = await client.get_negotiation(order.negotiation_id)
                        payload = _parse_requirements(negotiation.requirements)
                    except Exception:
                        # A malformed/empty order (e.g. requirements '{}' — a hire with no claim
                        # pasted into the requirement box) must NOT jam the poll loop and block the
                        # good orders behind it. Mark it handled, deliver a helpful notice, move on.
                        logger.exception("order %s has invalid requirements; skipping it", order.order_id)
                        delivered.add(order.order_id)
                        try:
                            await client.deliver_order(
                                order.order_id,
                                DeliverOrderRequest(
                                    deliverable_type=DeliverableType.TEXT,
                                    deliverable_text=json.dumps({
                                        "error": "No claim received. Paste a claim JSON (with "
                                                 "claim_number, policy, incident_type and "
                                                 "amount_requested) into the requirement box before hiring."
                                    }),
                                ),
                            )
                        except Exception:
                            logger.exception("could not deliver the error notice for order %s", order.order_id)
                        continue
                    response = await process_order(
                        payload,
                        cap_call_id=order.order_id,
                        caller_wallet=getattr(order, "requester_wallet_address", None),
                    )
                    # Mark delivered BEFORE the deliver call so a network hiccup there can't
                    # re-trigger the whole debate next poll (the DB row already exists).
                    delivered.add(order.order_id)
                    await client.deliver_order(
                        order.order_id,
                        DeliverOrderRequest(
                            deliverable_type=DeliverableType.TEXT,
                            deliverable_text=json.dumps(response),
                        ),
                    )
                    logger.info("delivered order %s (%s)", order.order_id, response["decision"])
            except Exception:
                logger.exception("provider poll iteration failed")
            await asyncio.sleep(_PROVIDER_POLL_SECONDS)
    finally:
        if stream is not None:
            await stream.close()
        await client.close()


async def _simulate() -> None:
    """Local end-to-end check: feed sample_claim.json through process_order (no CAP transport)."""
    from pathlib import Path

    sample = Path(__file__).resolve().parent / "database" / "sample_claim.json"
    payload = json.loads(sample.read_text(encoding="utf-8"))
    response = await process_order(
        payload, cap_call_id="SIMULATED-0001", caller_wallet="0xSIMULATEDBUYERWALLET",
    )
    print("\n================ CAP RESPONSE ================")
    print(json.dumps(response, indent=2))


if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    if "--simulate" in sys.argv:
        asyncio.run(_simulate())
    else:
        asyncio.run(start_provider())
