"""Background worker entrypoint for ingestion jobs."""

from __future__ import annotations

import asyncio
import logging
import time
from pathlib import Path

import app.bootstrap  # noqa: F401

from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.services.ingestion.github import parse_github_url
from app.services.ingestion.job_store import load_job_snapshot
from app.services.ingestion.pipeline import IngestionPipeline
from app.services.ingestion.store import get_ingestion_store
from services.queue import create_redis_client, dequeue_ingestion_task

logger = get_logger(__name__)
HEALTH_FILE = Path("/tmp/worker_healthy")


def touch_health() -> None:
    HEALTH_FILE.write_text(str(time.time()), encoding="utf-8")


async def process_task(pipeline: IngestionPipeline, payload: dict) -> None:
    task_type = payload.get("type")
    job_id = str(payload.get("job_id") or "")
    if not job_id:
        logger.warning("worker_skip_missing_job_id payload=%s", payload)
        return

    settings = get_settings()
    store = get_ingestion_store()
    job = await store.get_job(job_id)
    if job is None:
        job = load_job_snapshot(settings.ingestion_workspace_path, job_id)
    if job is None:
        logger.error("worker_job_not_found job_id=%s", job_id)
        return
    await store.remember_job(job)

    if task_type == "github":
        parsed = parse_github_url(str(payload.get("url") or ""))
        token = payload.get("token")
        await pipeline._run_github(job, parsed, token)  # noqa: SLF001
        return

    if task_type == "zip":
        archive_path = Path(str(payload.get("archive_path") or ""))
        await pipeline._run_zip(job, archive_path)  # noqa: SLF001
        return

    logger.warning("worker_unknown_task type=%s job_id=%s", task_type, job_id)


async def run_worker() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    client = create_redis_client(settings.redis_url)
    pipeline = IngestionPipeline(settings)
    touch_health()
    logger.info("worker_started redis=%s", settings.redis_url)

    while True:
        try:
            payload = await dequeue_ingestion_task(client, timeout=5)
            touch_health()
            if payload is None:
                continue
            logger.info("worker_processing job_id=%s type=%s", payload.get("job_id"), payload.get("type"))
            await process_task(pipeline, payload)
            touch_health()
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("worker_task_failed")
            touch_health()
            await asyncio.sleep(1)


def main() -> None:
    try:
        asyncio.run(run_worker())
    except KeyboardInterrupt:
        logging.info("worker_shutdown")


if __name__ == "__main__":
    main()
