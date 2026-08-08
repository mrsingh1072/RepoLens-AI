"""Tests for LLM providers."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from services.llm.factory import create_llm_provider
from services.llm.groq_provider import FALLBACK_MODEL, GroqLLMProvider


class TestGroqLLMProvider:
    def test_requires_api_key(self) -> None:
        with pytest.raises(Exception):
            GroqLLMProvider("")

    def test_complete_uses_chat_completions(self) -> None:
        client = MagicMock()
        response = MagicMock()
        response.choices = [MagicMock(message=MagicMock(content='{"answer":"ok"}'))]
        response.usage = MagicMock(prompt_tokens=10, completion_tokens=5, total_tokens=15)
        client.chat.completions.create.return_value = response

        provider = GroqLLMProvider("test-key", model="llama-3.3-70b-versatile")
        provider._client = client
        text = provider.complete("question", system="system prompt")
        assert "ok" in text
        client.chat.completions.create.assert_called_once()
        kwargs = client.chat.completions.create.call_args.kwargs
        assert kwargs["model"] == "llama-3.3-70b-versatile"
        assert kwargs["messages"][0]["role"] == "system"

    def test_falls_back_to_secondary_model(self) -> None:
        client = MagicMock()
        response = MagicMock()
        response.choices = [MagicMock(message=MagicMock(content="fallback answer"))]
        response.usage = None
        client.chat.completions.create.side_effect = [
            RuntimeError("model unavailable"),
            response,
        ]

        provider = GroqLLMProvider("test-key")
        provider._client = client
        text = provider.complete("question")
        assert text == "fallback answer"
        assert client.chat.completions.create.call_count == 2
        assert client.chat.completions.create.call_args_list[1].kwargs["model"] == FALLBACK_MODEL

    def test_factory_selects_groq(self) -> None:
        provider = create_llm_provider("groq", groq_api_key="abc")
        assert provider.name == "groq"

    def test_factory_rejects_missing_groq_key(self) -> None:
        with pytest.raises(Exception):
            create_llm_provider("groq", groq_api_key=None)
