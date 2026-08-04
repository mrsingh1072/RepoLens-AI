"""Delete ingestion artifacts for a repository job."""

from __future__ import annotations

import logging
import shutil
from pathlib import Path
from typing import Any

from app.core.config import Settings
from app.services.ingestion.job_store import jobs_dir, load_job_snapshot, manifest_dir
from app.services.ingestion.parse_store import load_parse_results, parse_output_dir

logger = logging.getLogger(__name__)


def _resolve_repo_id(job_id: str, workspace: Path) -> str | None:
    job = load_job_snapshot(workspace, job_id)
    if job is not None:
        repo_id = job.metadata.get("repo_id")
        if isinstance(repo_id, str) and repo_id:
            return repo_id
        if job.owner and job.name:
            return f"{job.owner}/{job.name}"

    parse_data = load_parse_results(parse_output_dir(workspace), job_id)
    if parse_data is None:
        return None

    repo_id = parse_data.get("repo_id")
    if isinstance(repo_id, str) and repo_id:
        return repo_id
    owner = parse_data.get("owner")
    name = parse_data.get("name")
    if owner and name:
        return f"{owner}/{name}"
    return None


def _safe_unlink(path: Path) -> bool:
    try:
        if path.is_file():
            path.unlink(missing_ok=True)
            return True
    except OSError as exc:
        logger.warning("Failed to delete file %s: %s", path, exc)
    return False


def _safe_rmtree(path: Path) -> bool:
    try:
        if path.is_dir():
            shutil.rmtree(path, ignore_errors=True)
            return True
    except OSError as exc:
        logger.warning("Failed to delete directory %s: %s", path, exc)
    return False


def delete_ingestion_job(settings: Settings, job_id: str) -> dict[str, Any]:
    """Remove on-disk artifacts, vectors, and graph data for an ingestion job."""
    workspace = settings.ingestion_workspace_path
    repo_id = _resolve_repo_id(job_id, workspace)
    deleted: dict[str, int | bool] = {
        "job_snapshot": False,
        "parse_artifact": False,
        "workspace_dir": False,
        "embedding_manifest": False,
        "embeddings": 0,
        "graph_nodes": 0,
    }

    deleted["job_snapshot"] = _safe_unlink(jobs_dir(workspace) / f"{job_id}.json")
    deleted["parse_artifact"] = _safe_unlink(parse_output_dir(workspace) / f"{job_id}.json")
    deleted["workspace_dir"] = _safe_rmtree(workspace / job_id)

    if repo_id:
        manifest_path = manifest_dir(workspace) / f"{repo_id.replace('/', '__')}.json"
        deleted["embedding_manifest"] = _safe_unlink(manifest_path)

        try:
            from app.services.cache_service import cache_key, get_cache_service

            cache = get_cache_service()
            cache.delete_prefix(cache_key("analytics", repo_id))
            cache.delete_prefix(cache_key("diagrams", repo_id))
        except Exception as exc:
            logger.warning("Cache cleanup failed for %s: %s", repo_id, exc)

        try:
            from services.embeddings.chroma_store import ChromaEmbeddingStore

            chroma = ChromaEmbeddingStore(
                host=settings.chroma_host if settings.chroma_use_http else None,
                port=settings.chroma_port if settings.chroma_use_http else None,
                persistent_path=settings.chroma_persistent_path_resolved,
                collection_name=settings.chroma_collection,
            )
            deleted["embeddings"] = chroma.delete_repo(repo_id)
        except Exception as exc:
            logger.warning("Embedding cleanup failed for %s: %s", repo_id, exc)

        if settings.neo4j_enabled:
            try:
                from services.graph import GraphService

                graph = GraphService(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password)
                graph.connect()
                deleted["graph_nodes"] = graph.delete_repository(repo_id)
            except Exception as exc:
                logger.warning("Graph cleanup failed for %s: %s", repo_id, exc)

    return {
        "job_id": job_id,
        "repo_id": repo_id,
        "deleted": deleted,
    }
