"""Centralized settings loaded from vericlaim/.env (pydantic-settings).

Adapts Recourse's backend/config.py: keeps the DB + LLM (AI/ML API, Featherless) + embedding
settings, DROPS all Band agent credentials, ADDS the CROO/CAP settings.
"""
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# agent/config.py -> agent/ -> vericlaim/ (repo root, where .env lives)
ROOT_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = ROOT_DIR / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE), env_file_encoding="utf-8", extra="ignore"
    )

    # Database (host 5434 / DB `vericlaim` locally, to coexist with Recourse on 5433)
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5434/vericlaim"

    # AI/ML API — Blake, Morgan, Sam (OpenAI-compatible)
    aimlapi_api_key: str = ""
    aimlapi_base_url: str = "https://api.aimlapi.com/v1"
    aimlapi_model: str = "gpt-4o"

    # Featherless — Alex (OpenAI-compatible)
    featherless_api_key: str = ""
    featherless_base_url: str = "https://api.featherless.ai/v1"
    featherless_model: str = "NousResearch/Hermes-2-Pro-Llama-3-8B"

    # CROO Agent Protocol (CAP). Registration/pricing/key come from the dashboard;
    # the AA wallet + gas are handled by CROO. See README.
    croo_api_url: str = "https://api.croo.network"
    croo_ws_url: str = "wss://api.croo.network/ws"
    base_rpc_url: str = "https://mainnet.base.org"
    croo_sdk_key: str = ""  # VeriClaim's own service key (croo_sk_...)

    # Helper-agent CAP keys (separate counterparty agents)
    claim_ingester_sdk_key: str = ""
    report_exporter_sdk_key: str = ""
    policy_extractor_sdk_key: str = ""

    # App
    environment: str = "development"
    embedding_model: str = "all-MiniLM-L6-v2"
    embedding_dim: int = 384


settings = Settings()
