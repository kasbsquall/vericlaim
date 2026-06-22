"""Shared CAP layer + LLM helper for the 3 helper agents.

Built on the verified croo-sdk v0.2.1 API:
  buyer:    NegotiateOrderRequest -> negotiate_order -> (provider accepts) -> pay_order -> get_delivery
  provider: connect_websocket -> accept_negotiation (NEGOTIATION_CREATED) -> on ORDER_PAID:
            get_order -> get_negotiation -> handler(requirements) -> deliver_order(TEXT)

Each helper is a separately-registered CAP agent (its own croo_sk_ key) so it is a distinct
counterparty that transacts with VeriClaim.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from pathlib import Path

from dotenv import load_dotenv

# helper_agents/common.py -> helper_agents/ -> vericlaim/.env
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

logger = logging.getLogger("vericlaim.helpers")

CROO_API_URL = os.getenv("CROO_API_URL", "https://api.croo.network")
CROO_WS_URL = os.getenv("CROO_WS_URL", "wss://api.croo.network/ws")
BASE_RPC_URL = os.getenv("BASE_RPC_URL", "https://mainnet.base.org")
VERICLAIM_SERVICE_ID = os.getenv("VERICLAIM_SERVICE_ID", "")

AIMLAPI_KEY = os.getenv("AIMLAPI_API_KEY", "")
AIMLAPI_BASE = os.getenv("AIMLAPI_BASE_URL", "https://api.aimlapi.com/v1")
AIMLAPI_MODEL = os.getenv("AIMLAPI_MODEL", "gpt-4o")

_POLL_SECONDS = 3
_DEFAULT_TIMEOUT = 180


def _make_client(sdk_key: str):
    """Build a CROO AgentClient (lazy import so modules load without croo-sdk installed)."""
    from croo import AgentClient, Config

    return AgentClient(
        Config(base_url=CROO_API_URL, ws_url=CROO_WS_URL, rpc_url=BASE_RPC_URL), sdk_key
    )


# --- LLM (AI/ML API, OpenAI-compatible) — JSON-only completion -----------------------------------

def _extract_json(text: str) -> str:
    """Pull the first {...} block out of an LLM reply (handles ```json fences)."""
    match = re.search(r"\{.*\}", text, re.DOTALL)
    return match.group(0) if match else text


async def llm_json(system: str, user: str) -> dict:
    """Single-shot AI/ML API completion that returns parsed JSON."""
    import httpx

    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(
            f"{AIMLAPI_BASE.rstrip('/')}/chat/completions",
            headers={"Authorization": f"Bearer {AIMLAPI_KEY}"},
            json={
                "model": AIMLAPI_MODEL,
                "temperature": 0,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            },
        )
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"].strip()
    return json.loads(_extract_json(content))


# --- CAP buyer -----------------------------------------------------------------------------------

async def hire_service_traced(
    sdk_key: str, service_id: str, requirements: dict, *, timeout: int = _DEFAULT_TIMEOUT
) -> tuple[dict, dict]:
    """Hire a CROO service; pay in USDC via CAP escrow. Returns (delivered_json, trace) where
    trace = {"order_id", "negotiation_id"} — the on-chain handle of the hire (for the A2A audit)."""
    from croo import NegotiateOrderRequest

    if not sdk_key:
        raise RuntimeError("SDK key is empty — register this agent and set its key in .env.")
    if not service_id:
        raise RuntimeError("service_id is empty — set the target agent's service id in .env.")

    client = _make_client(sdk_key)
    try:
        neg = await client.negotiate_order(
            NegotiateOrderRequest(
                service_id=service_id,
                requirements=json.dumps(requirements),
                metadata="",
                requester_agent_id="",
                fund_amount="",
                fund_token="",
            )
        )
        logger.info("Negotiation %s opened (service %s)", neg.negotiation_id, service_id)
        order = await _await_order(client, neg.negotiation_id, timeout)
        await client.pay_order(order.order_id)
        logger.info("Paid order %s", order.order_id)
        delivery = await _await_delivery(client, order.order_id, timeout)
        trace = {"order_id": order.order_id, "negotiation_id": neg.negotiation_id}
        return json.loads(delivery.deliverable_text), trace
    finally:
        await client.close()


async def hire_service(
    sdk_key: str, service_id: str, requirements: dict, *, timeout: int = _DEFAULT_TIMEOUT
) -> dict:
    """Hire a CROO service and return its delivered JSON. Pays in USDC via CAP escrow."""
    result, _ = await hire_service_traced(sdk_key, service_id, requirements, timeout=timeout)
    return result


async def _await_order(client, negotiation_id: str, timeout: int):
    """Poll until the provider accepts and the order for this negotiation reaches the payable
    'created' state. The order first appears as 'creating' (a transient pre-acceptance state) —
    paying then is rejected with INVALID_STATUS, so we must wait for 'created'."""
    from croo import ListOptions

    waited = 0
    while waited < timeout:
        for order in await client.list_orders(ListOptions(role="buyer")):
            if order.negotiation_id == negotiation_id and getattr(order, "status", None) == "created":
                return order
        await asyncio.sleep(_POLL_SECONDS)
        waited += _POLL_SECONDS
    raise TimeoutError(
        f"Provider did not produce a payable ('created') order for negotiation {negotiation_id} within {timeout}s."
    )


async def _await_delivery(client, order_id: str, timeout: int):
    """Poll get_delivery until the provider submits a deliverable."""
    waited = 0
    while waited < timeout:
        try:
            delivery = await client.get_delivery(order_id)
            if delivery and getattr(delivery, "deliverable_text", None):
                return delivery
        except Exception:
            pass
        await asyncio.sleep(_POLL_SECONDS)
        waited += _POLL_SECONDS
    raise TimeoutError(f"No delivery for order {order_id} within {timeout}s.")


# --- CAP provider --------------------------------------------------------------------------------

async def serve_provider(sdk_key: str, handler, *, label: str = "agent") -> None:
    """Run a CAP provider: auto-accept negotiations; on ORDER_PAID run `handler(requirements)`.

    `handler` is async, takes the parsed requirements dict, and returns a JSON-serializable dict
    that is delivered to the buyer as a TEXT deliverable.
    """
    if not sdk_key:
        raise RuntimeError(f"[{label}] SDK key empty — register the agent and set its key in .env.")

    from croo import DeliverableType, DeliverOrderRequest, EventType

    client = _make_client(sdk_key)
    stream = await client.connect_websocket()
    logger.info("[%s] CAP provider online — waiting for orders.", label)

    async def _on_negotiation(event) -> None:
        try:
            await client.accept_negotiation(event.negotiation_id)
            logger.info("[%s] accepted negotiation %s", label, event.negotiation_id)
        except Exception:
            logger.exception("[%s] failed to accept negotiation %s", label, event.negotiation_id)

    async def _on_paid(event) -> None:
        try:
            order = await client.get_order(event.order_id)
            negotiation = await client.get_negotiation(order.negotiation_id)
            req = negotiation.requirements
            req = req if isinstance(req, dict) else json.loads(req)
            result = await handler(req)
            await client.deliver_order(
                event.order_id,
                DeliverOrderRequest(
                    deliverable_type=DeliverableType.TEXT,
                    deliverable_text=json.dumps(result),
                ),
            )
            logger.info("[%s] delivered order %s", label, event.order_id)
        except Exception:
            logger.exception("[%s] failed order %s", label, event.order_id)

    # Keep strong references to spawned tasks — asyncio holds only weak refs, so without this an
    # in-flight handler can be garbage-collected mid-run ("Task was destroyed but it is pending").
    tasks: set = set()

    def _spawn(coro) -> None:
        task = asyncio.create_task(coro)
        tasks.add(task)
        task.add_done_callback(tasks.discard)

    stream.on(EventType.NEGOTIATION_CREATED, lambda e: _spawn(_on_negotiation(e)))
    stream.on(EventType.ORDER_PAID, lambda e: _spawn(_on_paid(e)))
    try:
        await asyncio.Event().wait()
    finally:
        await stream.close()
        await client.close()
