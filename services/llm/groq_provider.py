"""Groq chat completions provider."""

from __future__ import annotations

import logging
import time
from typing import Any, Iterator

from groq import Groq

from services.llm.base import LLMProviderError

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "llama-3.3-70b-versatile"
FALLBACK_MODEL = "llama-3.1-8b-instant"


class GroqLLMProvider:
    """Generate text via Groq Chat Completions API."""

    name = "groq"

    def __init__(
        self,
        api_key: str,
        *,
        model: str = DEFAULT_MODEL,
        fallback_model: str = FALLBACK_MODEL,
        timeout_seconds: float = 60.0,
    ) -> None:
        if not api_key or not api_key.strip():
            raise LLMProviderError("GROQ_API_KEY is required for Groq LLM.")
        self._model = model or DEFAULT_MODEL
        self._fallback_model = fallback_model or FALLBACK_MODEL
        self._timeout = timeout_seconds
        self._client = Groq(api_key=api_key.strip(), timeout=timeout_seconds)

    def complete(self, prompt: str, *, system: str | None = None, temperature: float = 0.2) -> str:
        """Return a non-streaming chat completion."""
        messages = self._build_messages(prompt, system=system)
        models = self._model_chain()
        last_exc: Exception | None = None

        for model in models:
            started = time.perf_counter()
            try:
                response = self._client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                )
                elapsed_ms = (time.perf_counter() - started) * 1000
                self._log_usage(model, response, elapsed_ms)
                content = self._extract_content(response)
                return content
            except Exception as exc:
                last_exc = exc
                logger.warning(
                    "Groq completion failed for model=%s: %s",
                    model,
                    exc,
                    exc_info=logger.isEnabledFor(logging.DEBUG),
                )
                if model == models[-1]:
                    break
                logger.info("Falling back from %s to %s", model, models[-1])

        raise self._wrap_error(last_exc)

    def complete_stream(
        self,
        prompt: str,
        *,
        system: str | None = None,
        temperature: float = 0.2,
    ) -> Iterator[str]:
        """Stream chat completion chunks (for future SSE endpoints)."""
        messages = self._build_messages(prompt, system=system)
        models = self._model_chain()
        last_exc: Exception | None = None

        for model in models:
            started = time.perf_counter()
            try:
                stream = self._client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    stream=True,
                )
                for chunk in stream:
                    delta = chunk.choices[0].delta.content if chunk.choices else None
                    if delta:
                        yield delta
                elapsed_ms = (time.perf_counter() - started) * 1000
                logger.info("Groq stream completed model=%s elapsed_ms=%.1f", model, elapsed_ms)
                return
            except Exception as exc:
                last_exc = exc
                if model == models[-1]:
                    break

        raise self._wrap_error(last_exc)

    def _model_chain(self) -> list[str]:
        if self._model == self._fallback_model:
            return [self._model]
        return [self._model, self._fallback_model]

    @staticmethod
    def _build_messages(prompt: str, *, system: str | None) -> list[dict[str, str]]:
        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        return messages

    @staticmethod
    def _extract_content(response: Any) -> str:
        if not response or not getattr(response, "choices", None):
            raise LLMProviderError("Groq returned no choices.")
        message = response.choices[0].message
        content = getattr(message, "content", None) if message else None
        if not content or not str(content).strip():
            raise LLMProviderError("Groq returned an empty response.")
        return str(content).strip()

    @staticmethod
    def _log_usage(model: str, response: Any, elapsed_ms: float) -> None:
        usage = getattr(response, "usage", None)
        if usage is None:
            logger.info("Groq completion model=%s elapsed_ms=%.1f", model, elapsed_ms)
            return
        logger.info(
            "Groq completion model=%s elapsed_ms=%.1f prompt_tokens=%s completion_tokens=%s total_tokens=%s",
            model,
            elapsed_ms,
            getattr(usage, "prompt_tokens", "?"),
            getattr(usage, "completion_tokens", "?"),
            getattr(usage, "total_tokens", "?"),
        )

    @staticmethod
    def _wrap_error(exc: Exception | None) -> LLMProviderError:
        if exc is None:
            return LLMProviderError("Groq completion failed with an unknown error.")
        message = str(exc).lower()
        if "authentication" in message or "invalid api key" in message or "401" in message:
            return LLMProviderError("Groq authentication failed. Check GROQ_API_KEY.")
        if "rate limit" in message or "429" in message:
            return LLMProviderError("Groq rate limit exceeded. Retry shortly or reduce request volume.")
        if "timeout" in message or "timed out" in message:
            return LLMProviderError("Groq request timed out. Retry with a shorter context.")
        if "connection" in message or "network" in message:
            return LLMProviderError(f"Groq network error: {exc}")
        return LLMProviderError(f"Groq completion failed: {exc}")
