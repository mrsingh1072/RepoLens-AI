"""Redis response cache for expensive read endpoints."""

from __future__ import annotations

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


class RedisCache:
    """Thin JSON cache on top of Redis."""

    def __init__(self, redis_url: str) -> None:
        import redis

        self._client = redis.from_url(redis_url, decode_responses=True)

    def ping(self) -> bool:
        try:
            return bool(self._client.ping())
        except Exception:
            return False

    def get_json(self, key: str) -> Any | None:
        try:
            raw = self._client.get(key)
            if not raw:
                return None
            return json.loads(raw)
        except Exception as exc:
            logger.warning("cache_get_failed key=%s error=%s", key, exc)
            return None

    def set_json(self, key: str, value: Any, *, ttl_seconds: int) -> None:
        try:
            self._client.setex(key, ttl_seconds, json.dumps(value))
        except Exception as exc:
            logger.warning("cache_set_failed key=%s error=%s", key, exc)

    def delete_prefix(self, prefix: str) -> int:
        try:
            keys = list(self._client.scan_iter(match=f"{prefix}*"))
            if not keys:
                return 0
            return int(self._client.delete(*keys))
        except Exception as exc:
            logger.warning("cache_delete_failed prefix=%s error=%s", prefix, exc)
            return 0


class NullCache:
    """No-op cache when Redis is disabled."""

    def ping(self) -> bool:
        return False

    def get_json(self, key: str) -> Any | None:
        return None

    def set_json(self, key: str, value: Any, *, ttl_seconds: int) -> None:
        return None

    def delete_prefix(self, prefix: str) -> int:
        return 0
