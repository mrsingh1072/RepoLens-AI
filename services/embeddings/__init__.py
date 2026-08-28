"""Vector embedding and ChromaDB indexing service."""

from services.embeddings.chroma_store import COLLECTION_NAME, ChromaEmbeddingStore
from services.embeddings.embedding_service import JinaEmbeddingService
from services.embeddings.indexer import EmbeddingIndexer
from services.embeddings.models import IndexSummary, SemanticChunk
from services.embeddings.semantic_chunks import build_repository_chunks, build_semantic_chunks

__all__ = [
    "COLLECTION_NAME",
    "ChromaEmbeddingStore",
    "EmbeddingIndexer",
    "IndexSummary",
    "JinaEmbeddingService",
    "SemanticChunk",
    "build_repository_chunks",
    "build_semantic_chunks",
]
