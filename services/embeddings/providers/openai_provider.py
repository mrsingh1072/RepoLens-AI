"""OpenAI embedding provider."""

from __future__ import annotations

from openai import OpenAI

from services.embeddings.providers.base import EmbeddingProvider


class OpenAIEmbeddingProvider(EmbeddingProvider):
    name = "openai"

    def __init__(
        self,
        api_key: str,
        *,
        model: str = "text-embedding-3-small",
    ) -> None:
        self._client = OpenAI(api_key=api_key)
        self._model = model
        self._dimension = 1536

    @property
    def dimension(self) -> int:
        return self._dimension

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        response = self._client.embeddings.create(input=texts, model=self._model)
        ordered = sorted(response.data, key=lambda item: item.index)
        return [item.embedding for item in ordered]
