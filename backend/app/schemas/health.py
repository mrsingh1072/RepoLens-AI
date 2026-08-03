"""Schemas for the health endpoint."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Response payload for ``GET /health``."""

    status: Literal["ok"] = Field(description="Service liveness indicator.")
    service: str = Field(description="Human-readable service name.")
    version: str = Field(description="Deployed application version.")
    environment: str = Field(description="Active runtime environment.")
