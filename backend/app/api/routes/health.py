"""Health check endpoint.

Controllers stay thin: this handler only assembles a response model from
configuration. Any future readiness checks (DB connectivity, etc.) should be
delegated to a dedicated service rather than implemented inline here.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, status

from app.api.deps import get_app_settings
from app.core.config import Settings
from app.schemas.health import HealthResponse

router = APIRouter()


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Liveness/health check",
)
async def health_check(settings: Settings = Depends(get_app_settings)) -> HealthResponse:
    """Return basic service metadata to signal the API is alive."""
    return HealthResponse(
        status="ok",
        service=settings.app_name,
        version=settings.app_version,
        environment=settings.environment,
    )
