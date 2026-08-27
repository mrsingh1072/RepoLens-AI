"""SSE streaming helpers for agent chat."""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from typing import Any


def format_sse(event: str, payload: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(payload)}\n\n"


def chunk_text(text: str, *, chunk_size: int = 24) -> list[str]:
    if not text:
        return []
    chunks: list[str] = []
    for index in range(0, len(text), chunk_size):
        chunks.append(text[index : index + chunk_size])
    return chunks


async def stream_answer_tokens(answer: str, *, delay_s: float = 0.012) -> AsyncIterator[str]:
    for chunk in chunk_text(answer):
        yield chunk
        await asyncio.sleep(delay_s)
