"""Ingestion pipeline orchestrator."""

from __future__ import annotations

import asyncio
import logging
import shutil
from pathlib import Path
from typing import Any

from app.core.config import Settings
from app.middleware.error_handler import AppError, ValidationError
from app.services.ingestion.clone import clone_repository, extract_zip_archive
from app.services.ingestion.filter import scan_repository
from app.services.ingestion.github import (
    GitHubRepoMetadata,
    ParsedGitHubUrl,
    build_clone_url,
    fetch_repo_metadata,
    parse_github_url,
)
from app.services.ingestion.parse_store import load_parse_results, parse_output_dir, save_parse_results
from app.services.ingestion.store import IngestionJob, IngestionStage, get_ingestion_store

logger = logging.getLogger(__name__)


class IngestionPipeline:
    """Runs the full repository ingestion pipeline."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._store = get_ingestion_store()
        self._workspace = settings.ingestion_workspace_path

    async def start_github_ingestion(
        self,
        *,
        url: str,
        token: str | None = None,
    ) -> IngestionJob:
        parsed = parse_github_url(url)
        job = await self._store.create_job(
            source="github",
            owner=parsed.owner,
            name=parsed.name,
        )
        await self._dispatch_github(job, parsed, token, url=url)
        return job

    async def start_zip_ingestion(
        self,
        *,
        archive_path: Path,
        owner: str,
        name: str,
    ) -> IngestionJob:
        job = await self._store.create_job(source="zip", owner=owner, name=name)
        await self._dispatch_zip(job, archive_path)
        return job

    async def _dispatch_github(
        self,
        job: IngestionJob,
        parsed: ParsedGitHubUrl,
        token: str | None,
        *,
        url: str,
    ) -> None:
        if self._settings.ingestion_use_worker:
            from services.queue import create_redis_client, enqueue_ingestion_task

            client = create_redis_client(self._settings.redis_url)
            await enqueue_ingestion_task(
                client,
                {
                    "type": "github",
                    "job_id": job.id,
                    "url": url,
                    "token": token,
                },
            )
            await client.aclose()
            job.update(stage=IngestionStage.QUEUED, message="Queued for background processing…")
            return
        asyncio.create_task(self._run_github(job, parsed, token))

    async def _dispatch_zip(self, job: IngestionJob, archive_path: Path) -> None:
        if self._settings.ingestion_use_worker:
            from services.queue import create_redis_client, enqueue_ingestion_task

            client = create_redis_client(self._settings.redis_url)
            await enqueue_ingestion_task(
                client,
                {
                    "type": "zip",
                    "job_id": job.id,
                    "archive_path": str(archive_path.resolve()),
                },
            )
            await client.aclose()
            job.update(stage=IngestionStage.QUEUED, message="Queued for background processing…")
            return
        asyncio.create_task(self._run_zip(job, archive_path))

    async def _run_github(
        self,
        job: IngestionJob,
        parsed: ParsedGitHubUrl,
        token: str | None,
    ) -> None:
        work_dir = self._workspace / job.id
        try:
            job.update(
                stage=IngestionStage.VALIDATING,
                message="Validating repository URL…",
            )
            metadata = await fetch_repo_metadata(parsed, token=token)
            if metadata.is_private and not token:
                raise ValidationError(
                    "This is a private repository. Provide a GitHub personal access token.",
                )

            job.update(
                stage=IngestionStage.CLONING,
                message=f"Cloning {metadata.full_name}…",
                metadata={
                    "description": metadata.description,
                    "default_branch": metadata.default_branch,
                    "stars": metadata.stars,
                    "forks": metadata.forks,
                },
            )

            clone_url = build_clone_url(metadata.clone_url, token)
            commit_hash = await clone_repository(
                clone_url,
                work_dir,
                branch=metadata.default_branch,
            )

            await self._scan_and_finalize(
                job,
                work_dir,
                branch=metadata.default_branch,
                commit_hash=commit_hash,
                github_metadata=metadata,
            )
        except AppError as exc:
            logger.warning("ingestion_failed job=%s error=%s", job.id, exc.message)
            job.update(stage=IngestionStage.FAILED, error=exc.message, message="Ingestion failed")
        except Exception:
            logger.exception("ingestion_unexpected job=%s", job.id)
            job.update(
                stage=IngestionStage.FAILED,
                error="An unexpected error occurred during ingestion.",
                message="Ingestion failed",
            )
        finally:
            self._cleanup_work_dir(work_dir)

    async def _run_zip(self, job: IngestionJob, archive_path: Path) -> None:
        work_dir = self._workspace / job.id
        try:
            job.update(
                stage=IngestionStage.VALIDATING,
                message="Validating archive…",
            )
            if not archive_path.exists():
                raise ValidationError("Uploaded archive was not found.")

            job.update(
                stage=IngestionStage.CLONING,
                message="Extracting archive…",
            )
            await extract_zip_archive(archive_path, work_dir)

            await self._scan_and_finalize(
                job,
                work_dir,
                branch="upload",
                commit_hash="uploaded",
                github_metadata=None,
            )
        except AppError as exc:
            job.update(stage=IngestionStage.FAILED, error=exc.message, message="Ingestion failed")
        except Exception:
            logger.exception("zip_ingestion_unexpected job=%s", job.id)
            job.update(
                stage=IngestionStage.FAILED,
                error="An unexpected error occurred during ingestion.",
                message="Ingestion failed",
            )
        finally:
            archive_path.unlink(missing_ok=True)
            self._cleanup_work_dir(work_dir)

    async def _scan_and_finalize(
        self,
        job: IngestionJob,
        work_dir: Path,
        *,
        branch: str,
        commit_hash: str,
        github_metadata: GitHubRepoMetadata | None,
    ) -> None:
        job.update(stage=IngestionStage.PARSING, message="Parsing code with Tree-sitter…")
        scan = await asyncio.to_thread(scan_repository, work_dir)

        if scan.file_count == 0:
            raise ValidationError(
                "No code files were found after filtering. "
                "The repository may only contain ignored directories.",
            )

        file_entries = [(f.path, f.language) for f in scan.files]
        parsed_files, chunks, parse_summary, sources = await asyncio.to_thread(
            _run_tree_sitter_parse,
            work_dir,
            file_entries,
            job.id,
            job.owner,
            job.name,
            f"{job.owner}/{job.name}",
            parse_output_dir(self._settings.ingestion_workspace_path),
        )

        job.update(
            progress=60,
            message=f"Parsed {parse_summary.files_parsed} files into {parse_summary.chunk_count} semantic chunks…",
        )

        repo_slug = f"{job.owner}/{job.name}"
        graph_summary = None
        if self._settings.neo4j_enabled:
            job.update(
                stage=IngestionStage.GRAPHING,
                message="Building code knowledge graph in Neo4j…",
            )
            graph_summary = await asyncio.to_thread(
                _run_graph_index,
                repo_slug,
                parsed_files,
                sources,
                self._settings,
            )

        job.update(
            stage=IngestionStage.INDEXING,
            progress=75,
            message=f"Indexed {parse_summary.symbol_count} symbols across {parse_summary.files_parsed} files…",
        )

        job.update(
            stage=IngestionStage.EMBEDDING,
            progress=85,
            message="Generating embeddings and storing in ChromaDB…",
        )

        embed_summary = await asyncio.to_thread(
            _run_embedding_index,
            repo_slug,
            parsed_files,
            sources,
            self._settings,
        )

        languages = scan.language_percentages()
        total_embedded = embed_summary.chunks_embedded
        result_metadata: dict[str, Any] = {
            "owner": job.owner,
            "name": job.name,
            "repo_id": repo_slug,
            "branch": branch,
            "commit_hash": commit_hash,
            "file_count": scan.file_count,
            "total_size_bytes": scan.total_size_bytes,
            "languages": languages,
            "primary_language": scan.primary_language,
            "chunk_count": embed_summary.chunks_total or parse_summary.chunk_count,
            "symbol_count": parse_summary.symbol_count,
            "api_endpoint_count": parse_summary.api_endpoint_count,
            "files_parsed": parse_summary.files_parsed,
            "graph_nodes": graph_summary.nodes_written if graph_summary else 0,
            "graph_relationships": graph_summary.relationships_written if graph_summary else 0,
            "graph_enabled": self._settings.neo4j_enabled,
            "embeddings_indexed": total_embedded,
            "embeddings_new": embed_summary.chunks_indexed,
            "embeddings_skipped": embed_summary.chunks_skipped,
            "embeddings_deleted": embed_summary.chunks_deleted,
            "embedding_provider": embed_summary.provider,
            "chroma_collection": embed_summary.collection,
            "description": (
                github_metadata.description
                if github_metadata
                else f"Uploaded archive for {job.owner}/{job.name}"
            ),
            "stars": github_metadata.stars if github_metadata else 0,
            "forks": github_metadata.forks if github_metadata else 0,
        }

        expected_chunks = embed_summary.chunks_total or parse_summary.chunk_count
        # Allow up to 20% embedding failures (transient API rate-limits on large repos).
        # Below 80% coverage is a hard failure — user should retry.
        if expected_chunks > 0 and total_embedded < expected_chunks * 0.80:
            raise ValidationError(
                f"Embedding incomplete ({total_embedded}/{expected_chunks} chunks indexed). "
                "Retry ingestion to continue.",
            )

        job.update(
            stage=IngestionStage.COMPLETED,
            progress=100,
            message=(
                f"Successfully ingested {scan.file_count} files "
                f"({total_embedded} embeddings, "
                f"{graph_summary.nodes_written if graph_summary else 0} graph nodes)."
            ),
            metadata=result_metadata,
        )

    def _cleanup_work_dir(self, work_dir: Path) -> None:
        if work_dir.exists():
            shutil.rmtree(work_dir, ignore_errors=True)


def _run_tree_sitter_parse(
    work_dir: Path,
    file_entries: list[tuple[str, str]],
    job_id: str,
    owner: str,
    name: str,
    repo_id: str,
    parse_output_dir: Path,
):
    from services.parser import ParserService

    parser = ParserService()
    parsed_files, chunks, summary = parser.parse_repository(work_dir, file_entries)
    sources = {
        pf.file: (work_dir / pf.file).read_text(encoding="utf-8", errors="replace")
        for pf in parsed_files
    }
    save_parse_results(
        parse_output_dir,
        job_id,
        parsed_files,
        owner=owner,
        name=name,
        repo_id=repo_id,
        extra={
            "chunk_count": summary.chunk_count,
            "symbol_count": summary.symbol_count,
            "api_endpoint_count": summary.api_endpoint_count,
            "files_parsed": summary.files_parsed,
            "files_skipped": summary.files_skipped,
        },
    )
    return parsed_files, chunks, summary, sources


def _run_embedding_index(
    repo_id: str,
    parsed_files: list,
    sources: dict[str, str],
    settings: Settings,
):
    from services.embeddings import EmbeddingIndexer
    from services.embeddings.providers import EmbeddingProviderError

    provider = settings.embedding_provider.lower().strip()
    if provider == "jina" and not settings.jina_api_key:
        raise ValidationError(
            "JINA_API_KEY is required for embeddings. Set it in .env or switch EMBEDDING_PROVIDER.",
        )
    if provider == "openai" and not settings.openai_api_key:
        raise ValidationError(
            "OPENAI_API_KEY is required for embeddings. Set it in .env or switch EMBEDDING_PROVIDER.",
        )

    # Jina batches internally at jina_batch_size; OpenAI uses the generic size.
    batch_size = settings.jina_batch_size if provider == "jina" else settings.embedding_batch_size

    try:
        indexer = EmbeddingIndexer(
            provider_name=settings.embedding_provider,
            openai_api_key=settings.openai_api_key,
            jina_api_key=settings.jina_api_key,
            jina_model=settings.jina_embedding_model,
            jina_batch_size=settings.jina_batch_size,
            jina_api_url=settings.jina_api_url,
            jina_timeout_seconds=settings.jina_timeout_seconds,
            jina_max_retries=settings.jina_max_retries,
            jina_dimensions=settings.jina_dimensions,
            chroma_host=settings.chroma_host if settings.chroma_use_http else None,
            chroma_port=settings.chroma_port if settings.chroma_use_http else None,
            chroma_persistent_path=settings.chroma_persistent_path_resolved,
            collection_name=settings.chroma_collection,
            manifest_dir=settings.embedding_manifest_dir,
            batch_size=batch_size,
            class_line_threshold=settings.class_line_threshold,
        )
    except EmbeddingProviderError as exc:
        raise ValidationError(str(exc)) from exc

    try:
        return indexer.index_repository(repo_id, parsed_files, sources)
    except Exception as exc:
        message = str(exc).lower()
        if "401" in message or "unauthorized" in message or "invalid_api_key" in message:
            if provider == "jina":
                raise ValidationError("Invalid Jina API key. Check JINA_API_KEY in .env.") from exc
            raise ValidationError("Invalid OpenAI API key. Check OPENAI_API_KEY in .env.") from exc
        if "insufficient_quota" in message or "429" in message or "rate limit" in message:
            if provider == "jina":
                raise ValidationError(
                    "Jina API rate limit or quota exceeded. Wait a moment and retry ingestion — "
                    "already-indexed chunks are saved.",
                ) from exc
            raise ValidationError(
                "OpenAI API quota exceeded. Add billing at platform.openai.com or switch "
                "to EMBEDDING_PROVIDER=jina.",
            ) from exc
        raise


def _run_graph_index(
    repo_id: str,
    parsed_files: list,
    sources: dict[str, str],
    settings: Settings,
):
    from services.graph import GraphIndexer, GraphServiceError

    try:
        indexer = GraphIndexer(
            uri=settings.neo4j_uri,
            user=settings.neo4j_user,
            password=settings.neo4j_password,
        )
        return indexer.index_repository(repo_id, parsed_files, sources)
    except GraphServiceError as exc:
        raise ValidationError(
            f"Neo4j graph indexing failed: {exc}. "
            "Ensure Neo4j is running (docker compose up neo4j) or set NEO4J_ENABLED=false.",
        ) from exc
