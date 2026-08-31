"""LLM provider interface."""

from __future__ import annotations

from typing import Protocol


class LLMProviderError(RuntimeError):
    """Raised when an LLM provider cannot fulfil a request."""


class LLMProvider(Protocol):
    """Generate text completions from a prompt."""

    name: str

    def complete(self, prompt: str, *, system: str | None = None, temperature: float = 0.2) -> str:
        """Return the model's text response."""
