"""Middleware registration.

Exposes a single :func:`register_middleware` entrypoint so ``create_app`` does
not need to know about individual middleware components.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import Settings
from app.middleware.error_handler import register_error_handlers
from app.middleware.request_logging import RequestLoggingMiddleware


def register_middleware(app: FastAPI, settings: Settings) -> None:
    """Attach all middleware and exception handlers to the application.

    Args:
        app: The FastAPI application instance.
        settings: Active application settings.
    """
    # In development, also allow any localhost port so Vite can use 5174, 5175, etc.
    cors_kwargs: dict = {
        "allow_origins": settings.cors_origins,
        "allow_credentials": True,
        "allow_methods": ["*"],
        "allow_headers": ["*"],
    }
    if not settings.is_production:
        cors_kwargs["allow_origin_regex"] = r"http://(localhost|127\.0\.0\.1)(:\d+)?"

    app.add_middleware(CORSMiddleware, **cors_kwargs)

    app.add_middleware(RequestLoggingMiddleware)

    # Exception handlers are registered last so they wrap all responses.
    register_error_handlers(app)


__all__ = ["register_middleware"]
