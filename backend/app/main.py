"""Application entrypoint.

Uses the *app factory* pattern so the fully-configured application can be
constructed by tests, ASGI servers, and tooling without side effects at import
time beyond building the instance itself.
"""

from __future__ import annotations

import app.bootstrap  # noqa: F401  # must run before services.* imports

from fastapi import FastAPI

from app.api.router import api_router
from app.core.config import Settings, get_settings
from app.core.lifespan import create_lifespan
from app.core.logging import configure_logging, get_logger
from app.middleware import register_middleware

logger = get_logger(__name__)


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build and configure a FastAPI application instance.

    Args:
        settings: Optional pre-built settings (primarily for tests). When
            omitted, the cached environment-derived settings are used.

    Returns:
        A configured :class:`fastapi.FastAPI` instance.
    """
    settings = settings or get_settings()
    configure_logging(settings.log_level)

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        docs_url="/docs" if settings.enable_docs else None,
        redoc_url="/redoc" if settings.enable_docs else None,
        openapi_url="/openapi.json" if settings.enable_docs else None,
        lifespan=create_lifespan(settings),
    )

    # Expose settings on app state so request-scoped dependencies resolve the
    # exact settings this app was built with (important for tests/multi-app).
    app.state.settings = settings

    # Order matters: middleware first, then routers.
    register_middleware(app, settings)
    app.include_router(api_router, prefix=settings.api_prefix)

    logger.info(
        "Application initialised (%s v%s, env=%s)",
        settings.app_name,
        settings.app_version,
        settings.environment,
    )
    return app


# ASGI entrypoint referenced by uvicorn: `uvicorn app.main:app`.
app = create_app()
