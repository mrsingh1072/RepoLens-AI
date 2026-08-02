"""Centralised logging configuration.

A single ``configure_logging`` call installs a consistent stdout handler on the
root logger. It is idempotent so repeated calls (e.g. per-test app creation) do
not stack handlers.
"""

from __future__ import annotations

import logging
import sys

_LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
_DATE_FORMAT = "%Y-%m-%dT%H:%M:%S%z"

_configured = False


def configure_logging(level: str = "INFO") -> None:
    """Configure the root logger exactly once.

    Args:
        level: Logging level name (e.g. ``"INFO"``, ``"DEBUG"``). Unknown
            values fall back to ``INFO``.
    """
    global _configured
    if _configured:
        return

    resolved_level = getattr(logging, level.upper(), logging.INFO)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(fmt=_LOG_FORMAT, datefmt=_DATE_FORMAT))

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(resolved_level)

    # Align uvicorn's loggers with our handler to avoid duplicate lines.
    for name in ("uvicorn", "uvicorn.access", "uvicorn.error"):
        uvicorn_logger = logging.getLogger(name)
        uvicorn_logger.handlers.clear()
        uvicorn_logger.propagate = True

    _configured = True


def get_logger(name: str) -> logging.Logger:
    """Return a named logger."""
    return logging.getLogger(name)
