"""Tests for agent answer synthesis."""

from __future__ import annotations

from services.agent.synthesis import extractive_fallback, synthesize_answer, try_meta_answer


class TestAgentSynthesis:
    def test_owner_meta_answer(self) -> None:
        result = try_meta_answer("SaurabhKumar/VeriSight-AI", "who is the owner of this repo")
        assert result is not None
        assert "SaurabhKumar" in result[0]

    def test_extractive_uses_snippets_not_summaries(self) -> None:
        answer, confidence, _ = extractive_fallback(
            "owner/repo",
            "how does auth work?",
            [{"tool": "search_code", "found": True, "summary": "Found 8 semantic code matches", "data": []}],
            [
                {
                    "file_path": "auth.py",
                    "function_name": "login",
                    "snippet": "def login(user, password):\n    return verify(user, password)",
                    "source": "vector",
                    "score": 0.9,
                    "start_line": 1,
                    "end_line": 2,
                },
            ],
        )
        assert "Found 8 semantic" not in answer
        assert "auth.py" in answer
        assert "login" in answer.lower()
        assert confidence > 0
