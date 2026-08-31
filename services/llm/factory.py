"""LLM provider factory."""

from __future__ import annotations

from services.llm.base import LLMProvider, LLMProviderError
from services.llm.groq_provider import FALLBACK_MODEL, GroqLLMProvider
from services.llm.openai_provider import OpenAILLMProvider


def create_llm_provider(
    provider: str,
    *,
    openai_api_key: str | None = None,
    openai_model: str = "gpt-4o-mini",
    groq_api_key: str | None = None,
    llm_model: str = "llama-3.3-70b-versatile",
    llm_fallback_model: str = FALLBACK_MODEL,
) -> LLMProvider:
    normalized = provider.lower().strip()
    if normalized == "openai":
        if not openai_api_key:
            raise LLMProviderError("OPENAI_API_KEY is required for OpenAI LLM.")
        return OpenAILLMProvider(openai_api_key, model=openai_model)
    if normalized == "groq":
        if not groq_api_key:
            raise LLMProviderError("GROQ_API_KEY is required for Groq LLM.")
        return GroqLLMProvider(
            groq_api_key,
            model=llm_model,
            fallback_model=llm_fallback_model,
        )
    raise LLMProviderError(f"Unsupported LLM provider: {provider}")
