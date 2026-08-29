"""Embedding domain models."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class SemanticChunk:
    """A semantic code unit ready for embedding."""

    repo_id: str
    file_path: str
    language: str
    chunk_type: str  # function | method | class | module
    class_name: str | None
    function_name: str | None
    symbol: str
    code: str
    document: str
    start_line: int
    end_line: int
    imports_context: str
    tags: list[str] = field(default_factory=list)
    content_hash: str = ""

    @property
    def chroma_id(self) -> str:
        return self.content_hash


@dataclass(slots=True)
class IndexSummary:
    """Result of an embedding indexing run."""

    repo_id: str
    chunks_indexed: int
    chunks_skipped: int
    chunks_deleted: int
    files_processed: int
    files_unchanged: int
    files_changed: int
    files_removed: int
    provider: str
    collection: str
    chunks_total: int = 0
    chunks_failed: int = 0

    @property
    def chunks_embedded(self) -> int:
        """Total chunks present in the vector store after this run."""
        return self.chunks_indexed + self.chunks_skipped
