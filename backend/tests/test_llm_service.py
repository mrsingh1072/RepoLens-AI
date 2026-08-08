"""Tests for the FastAPI LLM service."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.services.llm_service import LLMService, RAG_SYSTEM_PROMPT


class TestLLMService:
    def test_generate_answer_builds_context_prompt(self) -> None:
        provider = MagicMock()
        provider.complete.return_value = "Final answer"
        service = LLMService(provider)

        answer = service.generate_answer(
            "How does auth work?",
            "def login(): pass",
            conversation_history=[{"role": "user", "content": "hello"}],
        )

        assert answer == "Final answer"
        provider.complete.assert_called_once()
        prompt = provider.complete.call_args.args[0]
        assert "Repository Context" in prompt
        assert "def login(): pass" in prompt
        assert "How does auth work?" in prompt
        assert provider.complete.call_args.kwargs["system"] == RAG_SYSTEM_PROMPT

    def test_generate_answer_requires_context(self) -> None:
        service = LLMService(MagicMock())
        with pytest.raises(Exception):
            service.generate_answer("question", "   ")
