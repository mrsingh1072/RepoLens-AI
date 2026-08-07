"""Tests for agent response enrichment."""

from __future__ import annotations

from services.agent.enrichment import (
    build_reasoning_summary,
    enrich_agent_payload,
    extract_file_references,
    extract_function_references,
    generate_follow_up_suggestions,
)
from services.retrieval.models import CodeCitation


def _citation(**kwargs) -> CodeCitation:
    defaults = {
        "file_path": "backend/app/main.py",
        "function_name": "create_app",
        "class_name": None,
        "start_line": 10,
        "end_line": 20,
        "snippet": "def create_app(): ...",
        "source": "vector",
        "score": 0.9,
    }
    defaults.update(kwargs)
    return CodeCitation(**defaults)


def test_extract_references():
    citations = [_citation(), _citation(file_path="backend/app/routes/agent.py", function_name="agent_chat")]
    assert extract_file_references(citations) == ["backend/app/main.py", "backend/app/routes/agent.py"]
    assert extract_function_references(citations) == ["agent_chat", "create_app"]


def test_build_reasoning_summary_prefers_synthesis():
    steps = ["Plan: search_code", "Synthesis: Grounded in vector hits."]
    assert build_reasoning_summary(steps) == "Grounded in vector hits."


def test_enrich_agent_payload_appends_missing_refs():
    citations = [_citation()]
    payload = enrich_agent_payload(
        answer="The app boots via create_app.",
        citations=citations,
        reasoning_steps=["Synthesis: Entry point analysis."],
        question="How does the app start?",
        repo_id="owner/repo",
    )
    assert payload["file_references"] == ["backend/app/main.py"]
    assert payload["function_references"] == ["create_app"]
    assert "Files referenced" in payload["answer"]
    assert len(payload["follow_up_suggestions"]) >= 1


def test_follow_up_suggestions_are_unique():
    suggestions = generate_follow_up_suggestions(
        "How does authentication work?",
        repo_id="owner/repo",
        file_references=["backend/auth.py"],
        function_references=["verify_token"],
        citations=[_citation(file_path="backend/auth.py", function_name="verify_token")],
    )
    assert len(suggestions) == len(set(s.lower() for s in suggestions))
