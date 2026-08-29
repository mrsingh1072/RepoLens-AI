"""Repository embedding indexer.

Orchestrates the embedding stage: builds semantic chunks, embeds them in
batches via the configured :class:`EmbeddingProvider` (Jina by default), and
upserts vectors into ChromaDB with incremental (per-file hash) re-indexing.

The provider owns batching + retry/backoff for a single API call; this indexer
owns repo-level orchestration: iterating batches, persisting progress, and
continuing past a permanently-failing batch instead of aborting the whole run.
"""

from __future__ import annotations

import logging
from pathlib import Path

from services.embeddings.chroma_store import ChromaEmbeddingStore
from services.embeddings.manifest import (
    RepoManifest,
    diff_files,
    load_manifest,
    save_manifest,
)
from services.embeddings.models import IndexSummary, SemanticChunk
from services.embeddings.providers import create_embedding_provider
from services.embeddings.semantic_chunks import build_repository_chunks, file_content_hash
from services.parser.models import ParsedFile

logger = logging.getLogger(__name__)


class EmbeddingIndexer:
    """Index semantic code chunks into ChromaDB with incremental updates."""

    def __init__(
        self,
        *,
        provider_name: str,
        openai_api_key: str | None = None,
        openai_model: str = "text-embedding-3-small",
        jina_api_key: str | None = None,
        jina_model: str = "jina-embeddings-v3",
        jina_batch_size: int = 64,
        jina_api_url: str = "https://api.jina.ai/v1/embeddings",
        jina_timeout_seconds: float = 60.0,
        jina_max_retries: int = 3,
        jina_dimensions: int | None = None,
        chroma_host: str | None = None,
        chroma_port: int | None = None,
        chroma_persistent_path: Path | None = None,
        collection_name: str = "repo_embeddings",
        manifest_dir: Path | None = None,
        batch_size: int = 64,
        class_line_threshold: int = 80,
    ) -> None:
        self._provider = create_embedding_provider(
            provider_name,
            openai_api_key=openai_api_key,
            openai_model=openai_model,
            jina_api_key=jina_api_key,
            jina_model=jina_model,
            jina_batch_size=jina_batch_size,
            jina_api_url=jina_api_url,
            jina_timeout_seconds=jina_timeout_seconds,
            jina_max_retries=jina_max_retries,
            jina_dimensions=jina_dimensions,
        )
        self._store = ChromaEmbeddingStore(
            host=chroma_host,
            port=chroma_port,
            persistent_path=chroma_persistent_path,
            collection_name=collection_name,
        )
        self._manifest_dir = manifest_dir or Path("data/embeddings/manifests")
        self._batch_size = max(1, batch_size)
        self._class_line_threshold = class_line_threshold

    def index_repository(
        self,
        repo_id: str,
        parsed_files: list[ParsedFile],
        sources: dict[str, str],
    ) -> IndexSummary:
        """Embed and store chunks, re-indexing only changed files."""
        current_hashes = {
            pf.file: file_content_hash(sources[pf.file])
            for pf in parsed_files
            if pf.file in sources
        }
        expected_dim = getattr(self._provider, "dimension", None)
        if isinstance(expected_dim, int):
            if self._store.reset_collection_if_dimension_mismatch(expected_dim):
                previous = None
                prev_files: dict[str, str] = {}
            else:
                previous = load_manifest(self._manifest_dir, repo_id)
                prev_files = previous.files if previous else {}
        else:
            previous = load_manifest(self._manifest_dir, repo_id)
            prev_files = previous.files if previous else {}

        unchanged, changed, removed = diff_files(prev_files, current_hashes)

        deleted = 0
        for file_path in removed | changed:
            deleted += self._store.delete_repo_file(repo_id, file_path)

        all_chunks = build_repository_chunks(
            repo_id,
            parsed_files,
            sources,
            class_line_threshold=self._class_line_threshold,
        )

        existing_ids = self._store.get_existing_ids(repo_id)
        new_chunks = [c for c in all_chunks if c.content_hash not in existing_ids]

        logger.info(
            "Embedding repository %s: %d new chunks (%d already indexed) via provider=%s",
            repo_id,
            len(new_chunks),
            len(all_chunks) - len(new_chunks),
            self._provider.name,
        )

        indexed, failed = self._embed_and_upsert(new_chunks, repo_id, current_hashes)
        skipped = len(all_chunks) - len(new_chunks)
        final_ids = self._store.get_existing_ids(repo_id)

        manifest = RepoManifest(
            repo_id=repo_id,
            files=current_hashes,
            chunk_ids=sorted(final_ids),
        )
        save_manifest(self._manifest_dir, manifest)

        pending_files = {chunk.file_path for chunk in new_chunks}

        logger.info(
            "Repository indexing complete: repo=%s indexed=%d skipped=%d failed=%d",
            repo_id,
            indexed,
            skipped,
            failed,
        )

        return IndexSummary(
            repo_id=repo_id,
            chunks_indexed=indexed,
            chunks_skipped=skipped,
            chunks_deleted=deleted,
            files_processed=len(pending_files),
            files_unchanged=len(unchanged),
            files_changed=len(changed),
            files_removed=len(removed),
            provider=self._provider.name,
            collection=self._store.collection.name,
            chunks_total=len(all_chunks),
            chunks_failed=failed,
        )

    def _embed_and_upsert(
        self,
        chunks: list[SemanticChunk],
        repo_id: str,
        file_hashes: dict[str, str],
    ) -> tuple[int, int]:
        """Embed ``chunks`` in batches and upsert them into ChromaDB.

        Returns ``(indexed, failed)``. A batch that permanently fails (after the
        provider's internal retries) is logged and skipped so the remaining
        batches still get indexed — indexing is never aborted mid-repository.
        """
        if not chunks:
            return 0, 0

        indexed = 0
        failed = 0
        indexed_ids: list[str] = list(self._store.get_existing_ids(repo_id))
        total_batches = (len(chunks) + self._batch_size - 1) // self._batch_size

        for batch_index, start in enumerate(range(0, len(chunks), self._batch_size), start=1):
            batch = chunks[start : start + self._batch_size]
            texts = [chunk.document for chunk in batch]
            try:
                vectors = self._provider.embed_texts(texts)
            except Exception:
                failed += len(batch)
                logger.exception(
                    "embedding_batch_failed batch=%d/%d size=%d — skipping and continuing",
                    batch_index,
                    total_batches,
                    len(batch),
                )
                # Persist progress so a later re-run resumes from here.
                save_manifest(
                    self._manifest_dir,
                    RepoManifest(repo_id=repo_id, files=file_hashes, chunk_ids=sorted(set(indexed_ids))),
                )
                continue

            indexed += self._store.upsert_chunks(batch, vectors)
            indexed_ids.extend(chunk.content_hash for chunk in batch)
            save_manifest(
                self._manifest_dir,
                RepoManifest(repo_id=repo_id, files=file_hashes, chunk_ids=sorted(set(indexed_ids))),
            )
            logger.info("Batch %d/%d complete (%d chunks)", batch_index, total_batches, len(batch))

        return indexed, failed
