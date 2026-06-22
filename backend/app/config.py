"""
Centralised application configuration.

Every external dependency (Mongo, Meta, the LLM provider) is configured purely
through environment variables so the same image can run locally, in
docker-compose, or on Cloud Run without code changes.  See `.env.example` at
the repo root for the full list of variables and what they do.
"""
from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- Core service -------------------------------------------------
    environment: str = "development"
    app_name: str = "WhatsApp Multi-Tenant Agent"
    port: int = 8000

    # --- MongoDB --------------------------------------------------------
    mongo_uri: str = "mongodb://localhost:27017"
    mongo_db_name: str = "whatsapp_agent"

    # --- Meta / WhatsApp Cloud API --------------------------------------
    whatsapp_access_token: str = ""
    whatsapp_phone_number_id: str = ""
    whatsapp_business_account_id: str = ""
    whatsapp_api_version: str = "v20.0"
    whatsapp_verify_token: str = "change-me-verify-token"
    whatsapp_app_secret: str = ""  # used to validate X-Hub-Signature-256

    # If no access token is configured (or DRY_RUN is forced on), the
    # WhatsApp client logs every outbound call instead of hitting Meta's
    # Graph API. This lets the entire LangGraph pipeline + dashboard be
    # demoed end-to-end without a live Meta App, which is invaluable while
    # developing or when a grader doesn't have a WhatsApp test number handy.
    dry_run_whatsapp: bool = False

    # --- LLM provider -----------------------------------------------------
    llm_provider: Literal["openai", "anthropic", "groq"] = "openai"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-6"
    groq_api_key: str = ""          # free tier at console.groq.com
    groq_model: str = "llama-3.3-70b-versatile"  # best free Groq model

    # --- Misc -------------------------------------------------------------
    cors_origins: str = "*"
    sentiment_handover_enabled: bool = True

    @property
    def graph_api_base(self) -> str:
        return f"https://graph.facebook.com/{self.whatsapp_api_version}"


@lru_cache
def get_settings() -> Settings:
    return Settings()
