"""Per-repository conversation memory."""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass(slots=True)
class MemoryMessage:
    role: str
    content: str
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


class RepoConversationMemory:
    """Thread-safe in-memory conversation store keyed by repo + session."""

    def __init__(self, max_messages: int = 40) -> None:
        self._max_messages = max_messages
        self._store: dict[str, list[MemoryMessage]] = {}
        self._lock = threading.Lock()

    @staticmethod
    def _key(repo_id: str, session_id: str) -> str:
        return f"{repo_id}::{session_id}"

    def append(self, repo_id: str, session_id: str, role: str, content: str) -> None:
        key = self._key(repo_id, session_id)
        with self._lock:
            messages = self._store.setdefault(key, [])
            messages.append(MemoryMessage(role=role, content=content))
            if len(messages) > self._max_messages:
                self._store[key] = messages[-self._max_messages :]

    def history(self, repo_id: str, session_id: str, *, limit: int = 10) -> list[dict[str, str]]:
        key = self._key(repo_id, session_id)
        with self._lock:
            messages = self._store.get(key, [])
        return [{"role": m.role, "content": m.content} for m in messages[-limit:]]

    def clear(self, repo_id: str, session_id: str) -> None:
        key = self._key(repo_id, session_id)
        with self._lock:
            self._store.pop(key, None)


_memory: RepoConversationMemory | None = None


def get_conversation_memory() -> RepoConversationMemory:
    global _memory
    if _memory is None:
        _memory = RepoConversationMemory()
    return _memory
