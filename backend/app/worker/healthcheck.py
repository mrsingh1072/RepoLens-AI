"""Worker health probe for Docker."""

from __future__ import annotations

import sys
import time
from pathlib import Path

from app.core.config import get_settings

HEALTH_FILE = Path("/tmp/worker_healthy")
MAX_AGE_SECONDS = 120


def main() -> int:
    settings = get_settings()
    if not HEALTH_FILE.is_file():
        return 1
    try:
        age = time.time() - float(HEALTH_FILE.read_text(encoding="utf-8"))
    except ValueError:
        return 1
    if age > MAX_AGE_SECONDS:
        return 1

    try:
        import redis

        redis.Redis.from_url(settings.redis_url).ping()
    except Exception:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
