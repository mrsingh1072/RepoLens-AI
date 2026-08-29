"""Embedding provider factory.

Providers are constructed here so the rest of the pipeline stays
provider-agnostic. All Jina API logic lives in
:mod:`services.embeddings.embedding_service`.
"""

from __future__ import annotations

from services.embeddings.providers.base import EmbeddingProvider
from services.embeddings.providers.openai_provider import OpenAIEmbeddingProvider


class EmbeddingProviderError(Exception):
    """Raised when no embedding provider can be configured."""


def create_embedding_provider(
    provider: str,
    *,
    openai_api_key: str | None = None,
    openai_model: str = "text-embedding-3-small",
    jina_api_key: str | None = None,
    jina_model: str = "jina-embeddings-v3",
    jina_batch_size: int = 64,
    jina_api_url: str = "https://api.jina.ai/v1/embeddings",
    jina_timeout_seconds: float = 60.0,
    jina_max_retries: int = 3,
    jina_dimensions: int | None = None,
) -> EmbeddingProvider:
    """Return an :class:`EmbeddingProvider` for ``provider``.

    Supported providers: ``jina`` (default embedding backend) and ``openai``.
    """
    normalized = provider.lower().strip()

    if normalized == "jina":
        if not jina_api_key:
            raise EmbeddingProviderError("JINA_API_KEY is required for Jina embeddings.")
        # Lazy import avoids a circular import between this package and the
        # embedding service (which subclasses EmbeddingProvider).
        from services.embeddings.embedding_service import JinaEmbeddingService

        return JinaEmbeddingService(
            jina_api_key,
            model=jina_model,
            batch_size=jina_batch_size,
            api_url=jina_api_url,
            timeout_seconds=jina_timeout_seconds,
            max_retries=jina_max_retries,
            dimensions=jina_dimensions,
        )

    if normalized == "openai":
        if not openai_api_key:
            raise EmbeddingProviderError("OPENAI_API_KEY is required for OpenAI embeddings.")
        return OpenAIEmbeddingProvider(openai_api_key, model=openai_model)

    raise EmbeddingProviderError(f"Unsupported embedding provider: {provider}")
