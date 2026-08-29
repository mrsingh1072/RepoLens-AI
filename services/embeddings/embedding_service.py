"""Jina AI embedding service.

This module is the **single source of truth** for the embedding provider. All
calls to the Jina Embeddings API happen here — no other module in the codebase
may talk to the Jina HTTP API directly. Everything else depends only on the
provider-agnostic :meth:`JinaEmbeddingService.embed_text` /
:meth:`JinaEmbeddingService.embed_texts` methods.

Design goals (production RAG indexing):

- Reuse a single pooled HTTP session across all requests.
- Batch requests (default 64 texts per call) to minimise API round-trips.
- Automatic retry with exponential backoff on transient failures.
- Bounded request timeouts.
- Clean, structured logging including per-batch progress.

The service implements the existing :class:`EmbeddingProvider` interface so it
plugs into the current provider-factory architecture unchanged.
"""

from __future__ import annotations

import logging
import os
import time
from functools import lru_cache

import httpx

from services.embeddings.providers.base import EmbeddingProvider

logger = logging.getLogger(__name__)

# --- Jina defaults -----------------------------------------------------------
DEFAULT_MODEL = "jina-embeddings-v3"
DEFAULT_API_URL = "https://api.jina.ai/v1/embeddings"
DEFAULT_BATCH_SIZE = 64
DEFAULT_DIMENSION = 1024  # jina-embeddings-v3 native output dimensionality
DEFAULT_TIMEOUT_SECONDS = 60.0
DEFAULT_MAX_RETRIES = 3
DEFAULT_BACKOFF_BASE = 2.0
# Task for embedding stored documents. Queries should use ``retrieval.query``.
DEFAULT_TASK = "retrieval.passage"


class JinaEmbeddingError(RuntimeError):
    """Raised when the Jina embedding API cannot fulfil a request."""


class JinaEmbeddingService(EmbeddingProvider):
    """Embed text with the Jina AI Embeddings API (``jina-embeddings-v3``).

    Args:
        api_key: Jina API key. Required.
        model: Jina embedding model name.
        batch_size: Maximum number of texts sent per API call.
        api_url: Fully-qualified embeddings endpoint.
        timeout_seconds: Per-request timeout.
        max_retries: Attempts per batch before giving up on that batch.
        backoff_base: Multiplier for exponential backoff between retries.
        dimensions: Optional Matryoshka output size (``None`` = model default).
        task: Jina task type; ``retrieval.passage`` for stored documents.
        session: Optional pre-built :class:`httpx.Client` (mainly for tests).
            When omitted, the service owns and manages its own pooled client.
    """

    name = "jina"

    def __init__(
        self,
        api_key: str,
        *,
        model: str = DEFAULT_MODEL,
        batch_size: int = DEFAULT_BATCH_SIZE,
        api_url: str = DEFAULT_API_URL,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        max_retries: int = DEFAULT_MAX_RETRIES,
        backoff_base: float = DEFAULT_BACKOFF_BASE,
        dimensions: int | None = None,
        task: str = DEFAULT_TASK,
        session: httpx.Client | None = None,
    ) -> None:
        if not api_key:
            raise JinaEmbeddingError(
                "JINA_API_KEY is required for Jina embeddings. Set it in .env.",
            )
        self._model = model
        self._batch_size = max(1, batch_size)
        self._api_url = api_url
        self._max_retries = max(1, max_retries)
        self._backoff_base = backoff_base
        self._dimensions = dimensions
        self._task = task
        self._dimension = dimensions or DEFAULT_DIMENSION

        # Reuse a single pooled connection for every request in this process.
        self._owns_client = session is None
        self._client = session or httpx.Client(
            timeout=timeout_seconds,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
        )

        logger.info("Initializing Jina embedding service...")
        logger.info("Embedding model: %s", self._model)
        logger.info(
            "Jina config: batch_size=%d dimensions=%s task=%s",
            self._batch_size,
            self._dimensions or "default",
            self._task,
        )

    # --- EmbeddingProvider interface ----------------------------------------
    @property
    def dimension(self) -> int:
        """Vector dimensionality produced by the configured model."""
        return self._dimension

    # --- Public API (the ONLY embedding entry points) -----------------------
    def embed_text(self, text: str) -> list[float]:
        """Embed a single string and return its dense vector."""
        vectors = self.embed_texts([text])
        return vectors[0]

    def embed_query(self, text: str) -> list[float]:
        """Embed a search query using Jina's ``retrieval.query`` task."""
        return self._embed_with_task(text, "retrieval.query")

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Embed a list of strings, batching internally to minimise API calls.

        Returns vectors aligned 1:1 with ``texts``. Each batch is retried up to
        ``max_retries`` times with exponential backoff; if a batch still fails
        it raises :class:`JinaEmbeddingError` so the caller (the indexer) can
        decide whether to skip that batch and continue.
        """
        if not texts:
            return []

        vectors: list[list[float]] = []
        total_batches = (len(texts) + self._batch_size - 1) // self._batch_size
        for batch_index, start in enumerate(range(0, len(texts), self._batch_size), start=1):
            batch = texts[start : start + self._batch_size]
            logger.info("Embedding batch %d/%d (%d texts)", batch_index, total_batches, len(batch))
            vectors.extend(self._embed_batch_with_retry(batch, batch_index, total_batches))
        return vectors

    # --- Internals ----------------------------------------------------------
    def _embed_batch_with_retry(
        self,
        batch: list[str],
        batch_index: int,
        total_batches: int,
    ) -> list[list[float]]:
        delay = 2.0
        last_exc: Exception | None = None
        for attempt in range(1, self._max_retries + 1):
            try:
                return self._request_embeddings(batch)
            except httpx.HTTPStatusError as exc:
                last_exc = exc
                if exc.response.status_code == 429:
                    # Honour Retry-After header if present; otherwise wait 60s
                    retry_after = exc.response.headers.get("Retry-After")
                    wait = float(retry_after) if retry_after else 62.0
                    logger.warning(
                        "jina_rate_limited batch=%d/%d attempt=%d/%d — waiting %.0fs before retry",
                        batch_index,
                        total_batches,
                        attempt,
                        self._max_retries,
                        wait,
                    )
                    time.sleep(wait)
                    continue
                logger.warning(
                    "jina_batch_failed batch=%d/%d attempt=%d/%d error=%s",
                    batch_index,
                    total_batches,
                    attempt,
                    self._max_retries,
                    exc,
                )
                if attempt < self._max_retries:
                    time.sleep(delay)
                    delay *= self._backoff_base
            except Exception as exc:  # noqa: BLE001 - retried/re-raised below
                last_exc = exc
                logger.warning(
                    "jina_batch_failed batch=%d/%d attempt=%d/%d error=%s",
                    batch_index,
                    total_batches,
                    attempt,
                    self._max_retries,
                    exc,
                )
                if attempt < self._max_retries:
                    time.sleep(delay)
                    delay *= self._backoff_base
        raise JinaEmbeddingError(
            f"Jina embedding batch {batch_index}/{total_batches} failed after "
            f"{self._max_retries} attempts.",
        ) from last_exc

    def _embed_with_task(self, text: str, task: str) -> list[float]:
        delay = 1.0
        last_exc: Exception | None = None
        for attempt in range(1, self._max_retries + 1):
            try:
                return self._request_embeddings([text], task=task)[0]
            except Exception as exc:  # noqa: BLE001
                last_exc = exc
                if attempt < self._max_retries:
                    time.sleep(delay)
                    delay *= self._backoff_base
        raise JinaEmbeddingError(f"Jina query embedding failed after {self._max_retries} attempts.") from last_exc

    def _request_embeddings(
        self,
        batch: list[str],
        *,
        task: str | None = None,
    ) -> list[list[float]]:
        payload: dict[str, object] = {
            "model": self._model,
            "task": task or self._task,
            "input": batch,
            # Long code chunks (e.g. package-lock.json modules) can exceed the
            # model's 8192-token limit; Jina returns 400 without this flag.
            "truncate": True,
        }
        if self._dimensions:
            payload["dimensions"] = self._dimensions

        response = self._client.post(self._api_url, json=payload)
        if response.status_code >= 400:
            logger.error(
                "jina_api_error status=%s batch_size=%d body=%s",
                response.status_code,
                len(batch),
                response.text[:2000],
            )
            response.raise_for_status()
        data = response.json()

        items = data.get("data")
        if not isinstance(items, list) or len(items) != len(batch):
            raise JinaEmbeddingError(
                f"Unexpected Jina response: expected {len(batch)} embeddings, "
                f"got {len(items) if isinstance(items, list) else 'none'}.",
            )
        ordered = sorted(items, key=lambda item: item.get("index", 0))
        return [list(item["embedding"]) for item in ordered]

    def close(self) -> None:
        """Close the pooled HTTP client (only if this service created it)."""
        if self._owns_client:
            self._client.close()

    def __enter__(self) -> JinaEmbeddingService:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()


@lru_cache
def _default_service() -> JinaEmbeddingService:
    """Build a process-wide service from environment variables.

    Enables the module-level :func:`embed_text` / :func:`embed_texts` helpers to
    be used standalone (e.g. in scripts) without wiring backend settings.
    """
    dimensions = os.getenv("JINA_DIMENSIONS")
    return JinaEmbeddingService(
        api_key=os.getenv("JINA_API_KEY", ""),
        model=os.getenv("JINA_EMBEDDING_MODEL", DEFAULT_MODEL),
        batch_size=int(os.getenv("JINA_BATCH_SIZE", str(DEFAULT_BATCH_SIZE))),
        api_url=os.getenv("JINA_API_URL", DEFAULT_API_URL),
        dimensions=int(dimensions) if dimensions else None,
    )


def embed_text(text: str) -> list[float]:
    """Module-level convenience: embed one string via the default service."""
    return _default_service().embed_text(text)


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Module-level convenience: embed many strings via the default service."""
    return _default_service().embed_texts(texts)
