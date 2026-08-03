"""Pydantic schemas for repository ingestion."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class GitHubIngestionRequest(BaseModel):
    """Request body for GitHub repository ingestion."""

    url: str = Field(description="GitHub repository URL (public or private).")
    token: str | None = Field(
        default=None,
        description="GitHub personal access token for private repositories.",
    )

    @field_validator("url")
    @classmethod
    def strip_url(cls, value: str) -> str:
        return value.strip()


class ZipIngestionRequest(BaseModel):
    """Metadata accompanying a ZIP archive upload."""

    owner: str = Field(default="local", description="Logical owner label for the upload.")
    name: str = Field(description="Repository name for the uploaded archive.")


class IngestionJobResponse(BaseModel):
    """Snapshot of an ingestion job."""

    id: str
    source: Literal["github", "zip"]
    owner: str
    name: str
    stage: str
    progress: int = Field(ge=0, le=100)
    message: str
    error: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class IngestionStartResponse(BaseModel):
    """Response returned when an ingestion job is accepted."""

    job_id: str
    message: str = "Ingestion started."


class DeleteIngestionResponse(BaseModel):
    """Response returned after deleting an ingestion job."""

    job_id: str
    repo_id: str | None = None
    deleted: dict[str, int | bool] = Field(default_factory=dict)
    message: str = "Repository removed."


class RepositoryMetadataResponse(BaseModel):
    """Final repository metadata after successful ingestion."""

    owner: str
    name: str
    branch: str
    commit_hash: str
    file_count: int
    total_size_bytes: int
    languages: dict[str, float]
    primary_language: str
    description: str | None = None
    stars: int = 0
    forks: int = 0
