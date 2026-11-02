"""LLM provider factories.

Returns a ChatModel instance based on LLM_PROVIDER setting.
Supports groq, mistral, openrouter, and fake (for tests/local dev).
"""
from __future__ import annotations

from langchain_core.language_models import BaseChatModel

from app.config import settings


def get_chat_model() -> BaseChatModel:
    """Instantiate the primary chat model based on LLM_PROVIDER."""
    provider = settings.llm_provider

    if provider == "fake":
        # FakeListChatModel streams its responses token-by-token, giving a
        # deterministic end-to-end streaming path for tests and dev.
        from langchain_core.language_models.fake_chat_models import FakeListChatModel
        return FakeListChatModel(responses=["Hello! I am a fake LLM for testing."])

    if provider == "groq":
        from langchain_groq import ChatGroq
        return ChatGroq(
            model=settings.llm_primary_model or "llama-3.1-8b-instant",
            api_key=settings.groq_api_key,
        )

    if provider == "mistral":
        from langchain_mistralai import ChatMistralAI
        return ChatMistralAI(
            model=settings.llm_primary_model or "mistral-small-latest",
            api_key=settings.mistral_api_key,  # type: ignore[arg-type]
        )

    raise ValueError(f"Unknown LLM_PROVIDER: {provider!r}")


def get_embedding_model():
    """Instantiate the embedding model (Mistral mistral-embed)."""
    from langchain_mistralai import MistralAIEmbeddings
    return MistralAIEmbeddings(
        model=settings.embedding_model,
        api_key=settings.mistral_api_key,  # type: ignore[arg-type]
    )
