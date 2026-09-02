"""Redis-backed task queue for background workers."""

from __future__ import annotations

import json
import logging
from typing import Any

import redis.asyncio as redis

logger = logging.getLogger(__name__)

INGESTION_QUEUE_KEY = "ingestion:queue"


def create_redis_client(redis_url: str) -> redis.Redis:
    return redis.from_url(redis_url, decode_responses=True)


async def enqueue_ingestion_task(client: redis.Redis, payload: dict[str, Any]) -> None:
    await client.rpush(INGESTION_QUEUE_KEY, json.dumps(payload))
    logger.info("enqueued_ingestion_task type=%s job_id=%s", payload.get("type"), payload.get("job_id"))


async def dequeue_ingestion_task(client: redis.Redis, *, timeout: int = 5) -> dict[str, Any] | None:
    result = await client.blpop(INGESTION_QUEUE_KEY, timeout=timeout)
    if not result:
        return None
    _, raw = result
    return json.loads(raw)
