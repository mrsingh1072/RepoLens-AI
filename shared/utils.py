"""Small, dependency-free utility helpers."""

from __future__ import annotations

import re
from datetime import datetime, timezone

_SLUG_INVALID = re.compile(r"[^a-z0-9]+")
_SLUG_TRIM = re.compile(r"^-+|-+$")


def utc_now() -> datetime:
    """Return the current timezone-aware UTC time."""
    return datetime.now(timezone.utc)


def slugify(value: str) -> str:
    """Convert an arbitrary string into a lowercase, hyphenated slug.

    Args:
        value: The input string.

    Returns:
        A URL/identifier-safe slug. Returns an empty string for input that
        contains no alphanumeric characters.
    """
    lowered = value.strip().lower()
    hyphenated = _SLUG_INVALID.sub("-", lowered)
    return _SLUG_TRIM.sub("", hyphenated)
