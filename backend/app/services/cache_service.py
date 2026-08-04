"""Application-level cache accessor."""

from __future__ import annotations

from functools import lru_cache

from app.core.config import Settings, get_settings
from services.cache import NullCache, RedisCache


@lru_cache
def get_cache_service() -> RedisCache | NullCache:
    settings = get_settings()
    if not settings.cache_enabled:
        return NullCache()
    try:
        cache = RedisCache(settings.redis_url)
        if cache.ping():
            return cache
    except Exception:
        pass
    return NullCache()


def cache_key(namespace: str, *parts: str) -> str:
    safe = ":".join(p.replace(":", "_") for p in parts if p)
    return f"repolens:{namespace}:{safe}"
