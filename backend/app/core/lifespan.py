"""Ensure the ingestion workspace exists at startup."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI

from app.core.config import Settings
from app.core.logging import get_logger

logger = get_logger(__name__)


def create_lifespan(settings: Settings):
    """Return a lifespan context manager that prepares ingestion directories."""

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        workspace = settings.ingestion_workspace_path
        workspace.mkdir(parents=True, exist_ok=True)
        (workspace / "uploads").mkdir(parents=True, exist_ok=True)
        logger.info("Ingestion workspace ready at %s", workspace.resolve())
        yield

    return lifespan
