"""Vector retrieval via Jina query embeddings + ChromaDB."""

from __future__ import annotations

import logging

from services.embeddings.chroma_store import ChromaEmbeddingStore
from services.embeddings.embedding_service import JinaEmbeddingService
from services.retrieval.models import RetrievalHit

logger = logging.getLogger(__name__)


class VectorRetriever:
    """Semantic search over indexed code chunks."""

    def __init__(
        self,
        store: ChromaEmbeddingStore,
        embedder: JinaEmbeddingService,
    ) -> None:
        self._store = store
        self._embedder = embedder

    def search(self, repo_id: str, question: str, *, top_k: int = 8) -> list[RetrievalHit]:
        if self._store.count_repo(repo_id) == 0:
            logger.warning("No vectors indexed for repo=%s", repo_id)
            return []

        query_vector = self._embedder.embed_query(question)
        raw_hits = self._store.search(repo_id, query_vector, top_k=top_k)
        hits: list[RetrievalHit] = []
        for item in raw_hits:
            meta = item.get("metadata") or {}
            hits.append(
                RetrievalHit(
                    hit_id=f"vector::{item['id']}",
                    source="vector",
                    file_path=str(meta.get("file") or ""),
                    content=str(item.get("document") or ""),
                    score=float(item.get("score") or 0.0),
                    function_name=_optional_str(meta.get("function")),
                    class_name=_optional_str(meta.get("class")),
                    symbol=_optional_str(meta.get("symbol")),
                    start_line=int(meta.get("start_line") or 0),
                    end_line=int(meta.get("end_line") or 0),
                    chunk_type=_optional_str(meta.get("type")),
                ),
            )
        return hits


def _optional_str(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
