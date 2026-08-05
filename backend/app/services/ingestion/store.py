"""In-memory job and repository store for ingestion."""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any


class IngestionStage(str, Enum):
    """Pipeline stages surfaced to the frontend."""

    QUEUED = "queued"
    VALIDATING = "validating"
    CLONING = "cloning"
    PARSING = "parsing"
    GRAPHING = "graphing"
    INDEXING = "indexing"
    EMBEDDING = "embedding"
    COMPLETED = "completed"
    FAILED = "failed"


STAGE_PROGRESS: dict[IngestionStage, int] = {
    IngestionStage.QUEUED: 0,
    IngestionStage.VALIDATING: 5,
    IngestionStage.CLONING: 20,
    IngestionStage.PARSING: 50,
    IngestionStage.GRAPHING: 65,
    IngestionStage.INDEXING: 75,
    IngestionStage.EMBEDDING: 90,
    IngestionStage.COMPLETED: 100,
    IngestionStage.FAILED: 0,
}


@dataclass
class IngestionJob:
    """Tracks a single ingestion run."""

    id: str
    source: str  # "github" | "zip"
    owner: str
    name: str
    stage: IngestionStage = IngestionStage.QUEUED
    progress: int = 0
    message: str = "Waiting to start…"
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    _listeners: list[asyncio.Queue[dict[str, Any]]] = field(default_factory=list, repr=False)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "source": self.source,
            "owner": self.owner,
            "name": self.name,
            "stage": self.stage.value,
            "progress": self.progress,
            "message": self.message,
            "error": self.error,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> IngestionJob:
        created = data.get("created_at")
        updated = data.get("updated_at")
        return cls(
            id=data["id"],
            source=data["source"],
            owner=data["owner"],
            name=data["name"],
            stage=IngestionStage(data["stage"]),
            progress=int(data.get("progress", 0)),
            message=data.get("message", ""),
            error=data.get("error"),
            metadata=data.get("metadata") or {},
            created_at=datetime.fromisoformat(created) if isinstance(created, str) else datetime.now(UTC),
            updated_at=datetime.fromisoformat(updated) if isinstance(updated, str) else datetime.now(UTC),
        )

    def update(
        self,
        *,
        stage: IngestionStage | None = None,
        progress: int | None = None,
        message: str | None = None,
        error: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        if stage is not None:
            self.stage = stage
            if progress is None:
                self.progress = STAGE_PROGRESS.get(stage, self.progress)
        if progress is not None:
            self.progress = min(100, max(0, progress))
        if message is not None:
            self.message = message
        if error is not None:
            self.error = error
        if metadata:
            self.metadata.update(metadata)
        self.updated_at = datetime.now(UTC)
        self._notify()
        self._persist()

    def _persist(self) -> None:
        try:
            from app.core.config import get_settings
            from app.services.ingestion.job_store import save_job_snapshot

            save_job_snapshot(get_settings().ingestion_workspace_path, self)
        except Exception:
            pass

    def _notify(self) -> None:
        payload = self.to_dict()
        for queue in self._listeners:
            try:
                queue.put_nowait(payload)
            except asyncio.QueueFull:
                pass

    def subscribe(self) -> asyncio.Queue[dict[str, Any]]:
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=64)
        self._listeners.append(queue)
        queue.put_nowait(self.to_dict())
        return queue

    def unsubscribe(self, queue: asyncio.Queue[dict[str, Any]]) -> None:
        if queue in self._listeners:
            self._listeners.remove(queue)


class IngestionStore:
    """Thread-safe in-memory store for ingestion jobs."""

    def __init__(self) -> None:
        self._jobs: dict[str, IngestionJob] = {}
        self._lock = asyncio.Lock()

    async def create_job(
        self,
        *,
        source: str,
        owner: str,
        name: str,
    ) -> IngestionJob:
        job_id = f"job-{uuid.uuid4().hex[:12]}"
        job = IngestionJob(id=job_id, source=source, owner=owner, name=name)
        async with self._lock:
            self._jobs[job_id] = job
        try:
            from app.core.config import get_settings
            from app.services.ingestion.job_store import save_job_snapshot

            save_job_snapshot(get_settings().ingestion_workspace_path, job)
        except Exception:
            pass
        return job

    async def get_job(self, job_id: str) -> IngestionJob | None:
        async with self._lock:
            job = self._jobs.get(job_id)

        try:
            from app.core.config import get_settings
            from app.services.ingestion.job_store import load_job_snapshot

            loaded = load_job_snapshot(get_settings().ingestion_workspace_path, job_id)
            if loaded is not None:
                if (
                    job is None
                    or loaded.updated_at >= job.updated_at
                    or (job.stage not in (IngestionStage.COMPLETED, IngestionStage.FAILED) and loaded.stage != job.stage)
                ):
                    async with self._lock:
                        if job is not None:
                            loaded._listeners = job._listeners
                        self._jobs[job_id] = loaded
                    return loaded
        except Exception:
            pass

        return job

    async def remember_job(self, job: IngestionJob) -> None:
        async with self._lock:
            self._jobs[job.id] = job

    async def list_jobs(self) -> list[IngestionJob]:
        async with self._lock:
            return list(self._jobs.values())

    async def remove_job(self, job_id: str) -> None:
        async with self._lock:
            self._jobs.pop(job_id, None)


_store: IngestionStore | None = None


def get_ingestion_store() -> IngestionStore:
    global _store
    if _store is None:
        _store = IngestionStore()
    return _store
