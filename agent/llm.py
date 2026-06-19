"""OpenAI-compatible LLM helpers. Ported from Recourse's base_agent.build_llm, minus Band.

Two providers (partner wiring):
  - aimlapi     -> Blake, Morgan, Sam  (AI/ML API, GPT-4o)
  - featherless -> Alex                (Featherless, Hermes-2-Pro)
"""
from __future__ import annotations

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from config import settings


_clients: dict[str, ChatOpenAI] = {}


def build_llm(provider: str) -> ChatOpenAI:
    """Return a cached chat model for the provider (one client reused across calls so the HTTP
    connection pool isn't rebuilt on every LLM turn)."""
    if provider not in _clients:
        _clients[provider] = _make_llm(provider)
    return _clients[provider]


def _make_llm(provider: str) -> ChatOpenAI:
    if provider == "featherless":
        # Fail fast: the engine fails Alex's turn over to the reliable provider if Featherless
        # stalls, so a single slow/cold call should give up quickly. timeout=45, no retries.
        return ChatOpenAI(
            base_url=settings.featherless_base_url,
            api_key=settings.featherless_api_key,
            model=settings.featherless_model,
            temperature=0.4,
            timeout=45,
            max_retries=0,
            max_tokens=900,
            disable_streaming=True,
            # Hermes-2-Pro (8B) is prone to degenerate repetition loops; penalize repeats at
            # the source. Alex also post-collapses consecutive duplicates as a safety net.
            frequency_penalty=0.6,
            presence_penalty=0.3,
        )
    if provider == "aimlapi":
        return ChatOpenAI(
            base_url=settings.aimlapi_base_url,
            api_key=settings.aimlapi_api_key,
            model=settings.aimlapi_model,
            temperature=0.3,
            timeout=120,
            max_retries=2,
            max_tokens=900,
            disable_streaming=True,
        )
    raise ValueError(f"Unknown LLM provider: {provider!r}")


async def complete(provider: str, system: str, user: str) -> str:
    """Single-shot chat completion. Returns the stripped reply text."""
    llm = build_llm(provider)
    resp = await llm.ainvoke(
        [SystemMessage(content=system), HumanMessage(content=user)]
    )
    return (resp.content or "").strip()


def thread(context: list[tuple[str, str]]) -> str:
    """Render the accumulated debate as a readable thread for the next agent."""
    return "\n\n".join(f"[{who}]:\n{text}" for who, text in context)
