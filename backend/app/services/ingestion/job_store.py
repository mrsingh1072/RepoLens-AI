"""Persist ingestion job snapshots to disk."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.services.ingestion.store import IngestionJob, IngestionStage


def jobs_dir(workspace_path: Path) -> Path:
    return workspace_path / "jobs"


def manifest_dir(workspace_path: Path) -> Path:
    return workspace_path.parent / "embeddings" / "manifests"


def save_job_snapshot(workspace_path: Path, job: IngestionJob) -> Path:
    """Write the latest job state for recovery after server restarts."""
    out_dir = jobs_dir(workspace_path)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{job.id}.json"
    out_path.write_text(json.dumps(job.to_dict(), indent=2), encoding="utf-8")
    return out_path


def load_job_snapshot(workspace_path: Path, job_id: str) -> IngestionJob | None:
    """Load a persisted job snapshot if one exists."""
    out_path = jobs_dir(workspace_path) / f"{job_id}.json"
    if not out_path.is_file():
        return None
    data = json.loads(out_path.read_text(encoding="utf-8"))
    return IngestionJob.from_dict(data)


def _embedding_count(workspace_path: Path, repo_id: str) -> int | None:
    path = manifest_dir(workspace_path) / f"{repo_id.replace('/', '__')}.json"
    if not path.is_file():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    chunk_ids = data.get("chunk_ids")
    return len(chunk_ids) if isinstance(chunk_ids, list) else None


def _guess_repo_id(workspace_path: Path, parse_data: dict[str, Any]) -> str | None:
    repo_id = parse_data.get("repo_id")
    if isinstance(repo_id, str) and repo_id:
        return repo_id
    manifests = list(manifest_dir(workspace_path).glob("*.json"))
    if len(manifests) == 1:
        return manifests[0].stem.replace("__", "/")
    return None


def job_from_parse_artifact(workspace_path: Path, parse_data: dict[str, Any]) -> IngestionJob | None:
    """Rebuild a minimal job record from a parse JSON artifact."""
    job_id = parse_data.get("job_id")
    if not isinstance(job_id, str) or not job_id:
        return None

    summary = parse_data.get("summary") if isinstance(parse_data.get("summary"), dict) else {}
    owner = parse_data.get("owner") if isinstance(parse_data.get("owner"), str) else "unknown"
    name = parse_data.get("name") if isinstance(parse_data.get("name"), str) else job_id
    repo_id = _guess_repo_id(workspace_path, parse_data)
    if owner == "unknown" and repo_id and "/" in repo_id:
        owner, name = repo_id.split("/", 1)

    chunk_count = int(summary.get("chunk_count") or 0)
    files_parsed = int(summary.get("files_parsed") or len(parse_data.get("files") or []))
    embedded = _embedding_count(workspace_path, repo_id) if repo_id else None

    metadata: dict[str, Any] = {
        **summary,
        "files_parsed": files_parsed,
        "file_count": files_parsed,
        "chunk_count": chunk_count,
        "symbol_count": summary.get("symbol_count"),
        "api_endpoint_count": summary.get("api_endpoint_count"),
    }
    if repo_id:
        metadata["repo_id"] = repo_id
    if embedded is not None:
        metadata["embeddings_indexed"] = embedded

    stage = IngestionStage.COMPLETED
    error: str | None = None
    message = "Recovered from saved parse results."
    if embedded is not None and chunk_count and embedded < chunk_count:
        stage = IngestionStage.FAILED
        error = f"Embedding incomplete ({embedded}/{chunk_count} chunks indexed). Retry ingestion to continue."
        message = error
    elif embedded is not None and chunk_count and embedded >= chunk_count:
        message = f"Successfully indexed {files_parsed} files ({embedded} embeddings)."

    return IngestionJob(
        id=job_id,
        source="github" if owner not in {"unknown", "local"} else "zip",
        owner=owner,
        name=name,
        stage=stage,
        progress=100 if stage == IngestionStage.COMPLETED else 90,
        message=message,
        error=error,
        metadata=metadata,
    )

