"""Tests for the Redis cache layer."""

from __future__ import annotations

from services.cache import NullCache


def test_null_cache_is_noop() -> None:
    cache = NullCache()
    assert cache.ping() is False
    assert cache.get_json("any-key") is None
    cache.set_json("any-key", {"ok": True}, ttl_seconds=60)
    assert cache.delete_prefix("prefix") == 0


def test_cache_key_sanitizes_colons() -> None:
    from app.services.cache_service import cache_key

    assert cache_key("analytics", "owner/repo") == "repolens:analytics:owner/repo"
    assert cache_key("diagrams", "a:b", "c") == "repolens:diagrams:a_b:c"
