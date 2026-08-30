"""Vector store integration backed by ChromaDB.

Scaffolding only: connection management and collection operations are added in
a later phase. The interface below defines the contract used by the retrieval
pipeline.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class EmbeddingRecord:
    """A document (with metadata) stored in / retrieved from the vector store."""

    id: str
    document: str
    metadata: dict[str, Any] = field(default_factory=dict)
    embedding: list[float] | None = None
    score: float | None = None


class EmbeddingsService:
    """Add and query embedded documents in ChromaDB.

    Args:
        host: ChromaDB host.
        port: ChromaDB port.
    """

    def __init__(self, host: str = "localhost", port: int = 8000) -> None:
        self._host = host
        self._port = port
        self._client: Any | None = None

    @property
    def is_connected(self) -> bool:
        """Whether a live client connection has been established."""
        return self._client is not None

    def connect(self) -> None:
        """Establish a client connection to ChromaDB.

        Raises:
            NotImplementedError: Always, until the embeddings phase is built.
        """
        raise NotImplementedError("ChromaDB connection is implemented in a later phase.")

    def add(self, collection: str, records: Sequence[EmbeddingRecord]) -> None:
        """Upsert records into a collection."""
        raise NotImplementedError("ChromaDB upsert is implemented in a later phase.")

    def query(self, collection: str, text: str, top_k: int = 5) -> list[EmbeddingRecord]:
        """Return the ``top_k`` most similar records to ``text``."""
        raise NotImplementedError("ChromaDB query is implemented in a later phase.")
