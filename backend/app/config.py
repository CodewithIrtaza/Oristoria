"""Typed settings loaded from environment variables."""
from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Application
    app_env: str = "development"
    log_level: str = "INFO"

    # Database
    database_url: str = ""

    # LLM
    llm_provider: str = "fake"
    llm_primary_model: str = ""
    llm_fallback_model: str = ""
    embedding_model: str = "mistral-embed"

    # API keys
    groq_api_key: str = ""
    mistral_api_key: str = ""
    openrouter_api_key: str = ""

    # CORS – stored as comma-separated string, exposed as list
    allowed_origins: str = "http://localhost:5173"

    @property
    def allowed_origins_list(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]

    # Upload limits
    max_pdf_mb: int = 5
    max_pdf_pages: int = 40
    max_docs_per_conversation: int = 3

    # Rate limits
    rate_limit_per_hour: int = 20
    rate_limit_per_day: int = 100

    # Concurrency
    max_concurrent_generations: int = 3

    # LLM tuning
    max_output_tokens: int = 2048
    history_token_budget: int = 6000
    retrieval_top_k: int = 4

    # Storage guard
    max_conversations_per_anon: int = 20
    max_messages_per_conversation: int = 100
    retention_days: int = 30


settings = Settings()
