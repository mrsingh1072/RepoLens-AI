"""Embedding provider abstraction."""

from __future__ import annotations

from abc import ABC, abstractmethod


class EmbeddingProvider(ABC):
    """Provider-agnostic text embedding interface."""

    name: str

    @abstractmethod
    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of texts into dense vectors."""

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Vector dimensionality for this model."""
