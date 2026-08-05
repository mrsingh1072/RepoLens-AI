"""FastAPI-facing LLM service backed by Groq."""

from __future__ import annotations

import logging
from functools import lru_cache

from app.core.config import Settings, get_settings
from services.llm.base import LLMProvider, LLMProviderError
from services.llm.factory import create_llm_provider

logger = logging.getLogger(__name__)

RAG_SYSTEM_PROMPT = """You are an expert senior software engineer specializing in understanding software repositories.

Answer ONLY using the provided repository context.

If the answer is not present in the retrieved context, clearly state that the repository does not contain enough information.

Never hallucinate functions, classes, files, APIs, or implementation details.

When possible:
- Mention filenames.
- Mention class names.
- Mention function names.
- Explain the architecture clearly.
- Use Markdown formatting for readability."""


class LLMService:
    """Central entry point for LLM answer generation."""

    def __init__(self, provider: LLMProvider) -> None:
        self._provider = provider

    @property
    def provider(self) -> LLMProvider:
        """Underlying provider used for non-RAG LLM calls."""
        return self._provider

    def generate_answer(
        self,
        question: str,
        context: str,
        conversation_history: list[dict[str, str]] | None = None,
    ) -> str:
        """Generate a grounded answer from retrieved repository context."""
        if not context.strip():
            raise LLMProviderError("Cannot generate an answer without repository context.")

        prompt = self._build_prompt(question, context, conversation_history)
        return self._provider.complete(
            prompt,
            system=RAG_SYSTEM_PROMPT,
            temperature=0.15,
        )

    @staticmethod
    def _build_prompt(
        question: str,
        context: str,
        conversation_history: list[dict[str, str]] | None,
    ) -> str:
        sections: list[str] = []

        if conversation_history:
            recent = conversation_history[-6:]
            if recent:
                lines = [f"{item['role'].title()}: {item['content'][:500]}" for item in recent if item.get("content")]
                if lines:
                    sections.append("Previous conversation:\n" + "\n".join(lines))

        sections.extend(
            [
                "Repository Context",
                "========================",
                context.strip(),
                "========================",
                "",
                "User Question",
                question.strip(),
            ],
        )
        return "\n".join(sections)


def build_llm_service(settings: Settings | None = None) -> LLMService:
    """Construct an :class:`LLMService` from application settings."""
    cfg = settings or get_settings()
    provider = create_llm_provider(
        cfg.llm_provider,
        openai_api_key=cfg.openai_api_key,
        openai_model=cfg.openai_model,
        groq_api_key=cfg.groq_api_key,
        llm_model=cfg.llm_model,
        llm_fallback_model=cfg.llm_fallback_model,
    )
    return LLMService(provider)


@lru_cache
def get_llm_service() -> LLMService:
    """Return a cached LLM service for the process."""
    return build_llm_service(get_settings())
