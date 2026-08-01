"""Repository ingestion API routes."""

from __future__ import annotations

import asyncio
import json
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from fastapi.responses import StreamingResponse

from app.api.deps import get_app_settings, get_ingestion_pipeline
from app.core.config import Settings
from app.middleware.error_handler import NotFoundError
from app.schemas.ingestion import (
    DeleteIngestionResponse,
    GitHubIngestionRequest,
    IngestionJobResponse,
    IngestionStartResponse,
)
from app.services.ingestion.cleanup import delete_ingestion_job
from app.services.ingestion.parse_store import load_parse_results, parse_output_dir
from app.services.ingestion.pipeline import IngestionPipeline
from app.services.ingestion.store import get_ingestion_store

router = APIRouter(prefix="/ingestion", tags=["ingestion"])

MAX_UPLOAD_BYTES = 200 * 1024 * 1024  # 200 MB


@router.post(
    "/github",
    response_model=IngestionStartResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Ingest a GitHub repository",
)
async def ingest_github(
    body: GitHubIngestionRequest,
    pipeline: IngestionPipeline = Depends(get_ingestion_pipeline),
) -> IngestionStartResponse:
    """Validate, clone, and index a GitHub repository."""
    job = await pipeline.start_github_ingestion(url=body.url, token=body.token)
    return IngestionStartResponse(job_id=job.id)


@router.post(
    "/upload",
    response_model=IngestionStartResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Ingest a repository ZIP archive",
)
async def ingest_zip(
    file: UploadFile = File(..., description="ZIP archive of the repository."),
    owner: str = Form(default="local"),
    name: str = Form(..., description="Repository name."),
    settings: Settings = Depends(get_app_settings),
    pipeline: IngestionPipeline = Depends(get_ingestion_pipeline),
) -> IngestionStartResponse:
    """Extract and index a uploaded ZIP archive."""
    if not file.filename or not file.filename.lower().endswith(".zip"):
        from app.middleware.error_handler import ValidationError

        raise ValidationError("Only .zip archives are supported.")

    content = await file.read()
    if len(content) > MAX_UPLOAD_BYTES:
        from app.middleware.error_handler import ValidationError

        raise ValidationError(f"Archive exceeds the {MAX_UPLOAD_BYTES // (1024 * 1024)} MB limit.")

    upload_dir = settings.ingestion_workspace_path / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)
    archive_path = upload_dir / f"{name}-{uuid.uuid4().hex[:8]}.zip"
    archive_path.write_bytes(content)

    job = await pipeline.start_zip_ingestion(archive_path=archive_path, owner=owner, name=name)
    return IngestionStartResponse(job_id=job.id)


@router.get(
    "/{job_id}",
    response_model=IngestionJobResponse,
    summary="Get ingestion job status",
)
async def get_ingestion_status(
    job_id: str,
    settings: Settings = Depends(get_app_settings),
) -> IngestionJobResponse:
    """Poll the current status of an ingestion job."""
    store = get_ingestion_store()
    job = await store.get_job(job_id)
    if job is None:
        output_dir = parse_output_dir(settings.ingestion_workspace_path)
        parse_data = load_parse_results(output_dir, job_id)
        if parse_data is not None:
            from app.services.ingestion.job_store import job_from_parse_artifact

            recovered = job_from_parse_artifact(settings.ingestion_workspace_path, parse_data)
            if recovered is not None:
                await store.remember_job(recovered)
                job = recovered
    if job is None:
        raise NotFoundError(f"Ingestion job '{job_id}' not found.")
    return IngestionJobResponse(**job.to_dict())


@router.delete(
    "/{job_id}",
    response_model=DeleteIngestionResponse,
    summary="Delete an ingestion job and its indexed data",
)
async def delete_ingestion_job_route(
    job_id: str,
    settings: Settings = Depends(get_app_settings),
) -> DeleteIngestionResponse:
    """Remove job snapshots, parse artifacts, embeddings, and graph data."""
    store = get_ingestion_store()
    job = await store.get_job(job_id)
    parse_data = load_parse_results(parse_output_dir(settings.ingestion_workspace_path), job_id)
    if job is None and parse_data is None:
        raise NotFoundError(f"Ingestion job '{job_id}' not found.")

    result = delete_ingestion_job(settings, job_id)
    await store.remove_job(job_id)
    return DeleteIngestionResponse(**result)


@router.get(
    "/{job_id}/parse",
    summary="Get Tree-sitter parse results for a completed ingestion job",
)
async def get_parse_results(
    job_id: str,
    settings: Settings = Depends(get_app_settings),
) -> dict:
    """Return structured parse output (functions, classes, imports, chunks metadata)."""
    output_dir = parse_output_dir(settings.ingestion_workspace_path)
    data = load_parse_results(output_dir, job_id)
    if data is None:
        raise NotFoundError(
            f"Parse results for job '{job_id}' are not available. "
            "The job may still be running or was ingested before parsing was enabled.",
        )
    return data


@router.get(
    "/{job_id}/events",
    summary="Stream ingestion progress (SSE)",
    response_class=StreamingResponse,
)
async def stream_ingestion_events(job_id: str) -> StreamingResponse:
    """Server-Sent Events stream for real-time ingestion progress."""
    store = get_ingestion_store()
    job = await store.get_job(job_id)
    if job is None:
        raise NotFoundError(f"Ingestion job '{job_id}' not found.")

    async def event_generator():
        queue = job.subscribe()
        last_stage: str | None = None
        last_progress: int = -1
        try:
            while True:
                current_job = await store.get_job(job_id)
                if current_job is not None and (
                    current_job.stage.value != last_stage or current_job.progress != last_progress
                ):
                    last_stage = current_job.stage.value
                    last_progress = current_job.progress
                    yield f"data: {json.dumps(current_job.to_dict())}\n\n"
                    if current_job.stage.value in ("completed", "failed"):
                        break

                try:
                    payload = await asyncio.wait_for(queue.get(), timeout=1.0)
                    yield f"data: {json.dumps(payload)}\n\n"
                    if payload.get("stage") in ("completed", "failed"):
                        break
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"
        finally:
            job.unsubscribe(queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
