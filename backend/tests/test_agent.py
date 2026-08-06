"""Tests for the AI Software Engineer LangGraph agent."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from services.agent.agent import SoftwareEngineerAgent
from services.agent.memory import RepoConversationMemory
from services.agent.models import NOT_FOUND
from services.agent.tools import AgentToolContext
from services.retrieval.models import RetrievalHit


def _hit(file_path: str, content: str, *, symbol: str = "login") -> RetrievalHit:
    return RetrievalHit(
        hit_id="h1",
        source="vector",
        file_path=file_path,
        content=content,
        score=0.9,
        symbol=symbol,
        function_name=symbol,
        start_line=1,
        end_line=10,
    )


class TestAgentTools:
    def test_search_code_not_found(self) -> None:
        vector = MagicMock()
        vector.search.return_value = []
        ctx = AgentToolContext(repo_id="owner/repo", vector=vector, graph=None, graph_engine=None)
        from services.agent.tools import search_code

        result = search_code(ctx, query="missing")
        assert not result.found
        assert result.summary == NOT_FOUND

    def test_generate_architecture_serializes_layers(self) -> None:
        from services.agent.tools import generate_architecture
        from services.graph.models import ArchitectureLayer

        engine = MagicMock()
        engine.detect_architecture_layers.return_value = [
            ArchitectureLayer("presentation", 3, 5, ["routes/api.py"]),
        ]
        engine.cross_layer_calls.return_value = []
        ctx = AgentToolContext(
            repo_id="owner/repo",
            vector=MagicMock(),
            graph=None,
            graph_engine=engine,
        )
        result = generate_architecture(ctx)
        assert result.found
        assert result.data[0]["layer"] == "presentation"

    def test_find_bug_patterns_detects_bare_except(self) -> None:
        vector = MagicMock()
        vector.search.return_value = [_hit("bad.py", "try:\n    x()\nexcept:\n    pass\n")]
        ctx = AgentToolContext(repo_id="owner/repo", vector=vector, graph=None, graph_engine=None)
        from services.agent.tools import find_bug_patterns

        result = find_bug_patterns(ctx, query="exception handling")
        assert result.found
        assert result.data[0]["pattern"] == "bare_except"


class TestAgentGraph:
    def test_meta_owner_answer(self) -> None:
        agent = SoftwareEngineerAgent(
            vector=MagicMock(),
            graph=None,
            graph_engine=None,
            llm=None,
            memory=RepoConversationMemory(),
        )
        result = agent.run("SaurabhKumar/VeriSight-AI", "who is the owner of this repo")
        assert "SaurabhKumar" in result.answer
        assert result.confidence >= 0.9
        assert result.tools_used == []

    def test_heuristic_plan_for_project_overview(self) -> None:
        from services.agent.graph import _heuristic_plan

        steps = _heuristic_plan("how does this project work?")
        tools = [s.tool for s in steps]
        assert "generate_architecture" in tools
        assert "trace_request_flow" in tools
        assert "search_code" in tools

    def test_heuristic_plan_uses_multiple_tools(self) -> None:
        from services.agent.graph import _heuristic_plan

        steps = _heuristic_plan("Explain the architecture and request flow for the login API")
        tools = [s.tool for s in steps]
        assert len(tools) >= 2
        assert "generate_architecture" in tools
        assert "search_code" in tools

    def test_agent_returns_not_found_without_evidence(self) -> None:
        vector = MagicMock()
        vector.search.return_value = []
        graph = MagicMock()
        graph.search.return_value = []

        agent = SoftwareEngineerAgent(
            vector=vector,
            graph=graph,
            graph_engine=None,
            llm=None,
            memory=RepoConversationMemory(),
            top_k=5,
        )
        result = agent.run("owner/repo", "How does authentication work?")
        assert result.answer == NOT_FOUND
        assert len(result.tools_used) >= 2
        assert any("Plan:" in step or "Executed" in step for step in result.reasoning_steps)

    def test_agent_collects_citations_from_tools(self) -> None:
        vector = MagicMock()
        vector.search.return_value = [_hit("auth.py", "def login(): pass")]
        graph = MagicMock()
        graph.search.return_value = []

        llm = MagicMock()
        llm.complete.side_effect = [
            '{"reasoning":"search code","steps":[{"tool":"search_code","inputs":{"query":"login"},"rationale":"find auth"}]}',
            '{"answer":"Login is in auth.py","confidence":0.8,"reasoning_summary":"Found login function"}',
        ]

        agent = SoftwareEngineerAgent(
            vector=vector,
            graph=graph,
            graph_engine=None,
            llm=llm,
            memory=RepoConversationMemory(),
            top_k=5,
        )
        result = agent.run("owner/repo", "Where is login implemented?")
        assert "auth.py" in result.answer or result.citations
        assert result.tools_used
        assert result.confidence > 0

    def test_conversation_memory_persists_per_session(self) -> None:
        memory = RepoConversationMemory()
        vector = MagicMock()
        vector.search.return_value = [_hit("a.py", "def foo(): pass")]

        agent = SoftwareEngineerAgent(
            vector=vector,
            graph=None,
            graph_engine=None,
            llm=None,
            memory=memory,
            top_k=5,
        )
        first = agent.run("owner/repo", "What is foo?", session_id="sess-1")
        second = agent.run("owner/repo", "Tell me more", session_id="sess-1")
        history = memory.history("owner/repo", "sess-1")
        assert first.session_id == "sess-1"
        assert second.session_id == "sess-1"
        assert len(history) >= 4
        assert history[0]["role"] == "user"
        assert history[0]["content"] == "What is foo?"
