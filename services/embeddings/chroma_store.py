"""ChromaDB vector store for repository embeddings."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import chromadb
from chromadb.api import ClientAPI
from chromadb.api.models.Collection import Collection

from services.embeddings.models import SemanticChunk

logger = logging.getLogger(__name__)

COLLECTION_NAME = "repo_embeddings"


class ChromaEmbeddingStore:
    """Persist and query code embeddings in ChromaDB."""

    def __init__(
        self,
        *,
        host: str | None = None,
        port: int | None = None,
        persistent_path: Path | None = None,
        collection_name: str = COLLECTION_NAME,
    ) -> None:
        self._collection_name = collection_name
        self._client = self._build_client(host=host, port=port, persistent_path=persistent_path)
        self._collection = self._client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    @property
    def collection(self) -> Collection:
        return self._collection

    @staticmethod
    def _build_client(
        *,
        host: str | None,
        port: int | None,
        persistent_path: Path | None,
    ) -> ClientAPI:
        if host and port:
            try:
                return chromadb.HttpClient(host=host, port=port)
            except Exception as exc:
                logger.warning("Chroma HTTP client failed (%s); falling back to persistent store.", exc)
        path = persistent_path or Path("data/chroma")
        path.mkdir(parents=True, exist_ok=True)
        return chromadb.PersistentClient(path=str(path))

    def delete_repo_file(self, repo_id: str, file_path: str) -> int:
        """Remove all vectors for a file within a repository."""
        existing = self._collection.get(where={"$and": [{"repo_id": repo_id}, {"file": file_path}]})
        ids = existing.get("ids") or []
        if ids:
            self._collection.delete(ids=ids)
        return len(ids)

    def delete_repo(self, repo_id: str) -> int:
        existing = self._collection.get(where={"repo_id": repo_id})
        ids = existing.get("ids") or []
        if ids:
            self._collection.delete(ids=ids)
        return len(ids)

    def get_existing_ids(self, repo_id: str) -> set[str]:
        result = self._collection.get(where={"repo_id": repo_id}, include=[])
        return set(result.get("ids") or [])

    def get_repo_embedding_dimension(self, repo_id: str) -> int | None:
        """Return the dimensionality of stored vectors for ``repo_id``, if any."""
        result = self._collection.get(
            where={"repo_id": repo_id},
            include=["embeddings"],
            limit=1,
        )
        embeddings = result.get("embeddings")
        if embeddings is None or len(embeddings) == 0:
            return None
        return len(embeddings[0])

    def get_collection_embedding_dimension(self) -> int | None:
        """Return the dimensionality of any vector in the collection, if present."""
        result = self._collection.get(include=["embeddings"], limit=1)
        embeddings = result.get("embeddings")
        if embeddings is None or len(embeddings) == 0:
            return None
        return len(embeddings[0])

    def reset_collection_if_dimension_mismatch(self, expected_dim: int) -> bool:
        """Drop and recreate the collection when embedding dimensionality changes.

        Chroma fixes vector dimension on first insert; switching embedding
        providers (e.g. legacy 3072-dim vectors → Jina 1024) requires a full reset.
        """
        current = self.get_collection_embedding_dimension()
        if current is None or current == expected_dim:
            return False
        logger.warning(
            "Chroma collection dimension mismatch stored=%d expected=%d — resetting collection",
            current,
            expected_dim,
        )
        self._client.delete_collection(self._collection_name)
        self._collection = self._client.get_or_create_collection(
            name=self._collection_name,
            metadata={"hnsw:space": "cosine"},
        )
        return True

    def upsert_chunks(self, chunks: list[SemanticChunk], embeddings: list[list[float]]) -> int:
        if not chunks:
            return 0
        if len(chunks) != len(embeddings):
            raise ValueError("chunks and embeddings length mismatch")

        ids = [chunk.chroma_id for chunk in chunks]
        documents = [chunk.document for chunk in chunks]
        metadatas = [_chroma_metadata(chunk) for chunk in chunks]
        self._collection.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
        )
        return len(chunks)

    def count_repo(self, repo_id: str) -> int:
        result = self._collection.get(where={"repo_id": repo_id}, include=[])
        return len(result.get("ids") or [])

    def search(
        self,
        repo_id: str,
        query_embedding: list[float],
        *,
        top_k: int = 8,
    ) -> list[dict[str, Any]]:
        """Return the ``top_k`` most similar chunks for ``repo_id``."""
        if self.count_repo(repo_id) == 0:
            return []

        result = self._collection.query(
            query_embeddings=[query_embedding],
            n_results=max(1, top_k),
            where={"repo_id": repo_id},
            include=["documents", "metadatas", "distances"],
        )

        ids = (result.get("ids") or [[]])[0]
        documents = (result.get("documents") or [[]])[0]
        metadatas = (result.get("metadatas") or [[]])[0]
        distances = (result.get("distances") or [[]])[0]

        hits: list[dict[str, Any]] = []
        for idx, chunk_id in enumerate(ids):
            meta = metadatas[idx] if idx < len(metadatas) else {}
            distance = float(distances[idx]) if idx < len(distances) else 1.0
            hits.append(
                {
                    "id": chunk_id,
                    "document": documents[idx] if idx < len(documents) else "",
                    "metadata": meta or {},
                    "distance": distance,
                    "score": max(0.0, 1.0 - distance),
                },
            )
        return hits


def _chroma_metadata(chunk: SemanticChunk) -> dict[str, Any]:
    """Chroma metadata values must be scalar types."""
    return {
        "repo_id": chunk.repo_id,
        "file": chunk.file_path,
        "class": chunk.class_name or "",
        "function": chunk.function_name or "",
        "type": chunk.chunk_type,
        "language": chunk.language,
        "symbol": chunk.symbol,
        "start_line": chunk.start_line,
        "end_line": chunk.end_line,
        "content_hash": chunk.content_hash,
        "tags": ",".join(chunk.tags),
    }
