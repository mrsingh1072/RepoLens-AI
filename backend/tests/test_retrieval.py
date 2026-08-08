"""Tests for hybrid retrieval pipeline."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from services.retrieval.intent import IntentAnalyzer
from services.retrieval.merge import merge_hits
from services.retrieval.models import RetrievalHit, RetrievalStrategy
from services.retrieval.pipeline import HybridRetrievalPipeline, RetrievalError


def _hit(
    hit_id: str,
    source: str,
    file_path: str,
    content: str,
    score: float,
    *,
    symbol: str | None = None,
    start_line: int = 1,
    end_line: int = 10,
) -> RetrievalHit:
    return RetrievalHit(
        hit_id=hit_id,
        source=source,
        file_path=file_path,
        content=content,
        score=score,
        symbol=symbol,
        function_name=symbol,
        start_line=start_line,
        end_line=end_line,
    )


class TestIntentAnalyzer:
    def test_heuristic_prefers_graph_for_call_chain(self) -> None:
        intent = IntentAnalyzer(None).analyze("Show the call chain for AuthService.login")
        assert intent.strategy in {RetrievalStrategy.GRAPH, RetrievalStrategy.HYBRID}
        assert "AuthService" in intent.symbols or "login" in intent.symbols

    def test_llm_intent_parsing(self) -> None:
        llm = MagicMock()
        llm.complete.return_value = (
            '{"strategy":"hybrid","symbols":["UserController"],"query_type":"implementation","reasoning":"Needs code and deps"}'
        )
        intent = IntentAnalyzer(llm).analyze("How does UserController authenticate users?")
        assert intent.strategy == RetrievalStrategy.HYBRID
        assert intent.symbols == ["UserController"]


class TestMergeHits:
    def test_boosts_overlap(self) -> None:
        vector = [_hit("v1", "vector", "a.py", "vector content", 0.9, symbol="login")]
        graph = [_hit("g1", "graph", "a.py", "graph content", 0.8, symbol="login")]
        merged = merge_hits(vector, graph)
        assert len(merged) == 1
        assert merged[0].source == "hybrid"
        assert merged[0].score > 0.9


class TestHybridRetrievalPipeline:
    def _pipeline(self) -> HybridRetrievalPipeline:
        chroma = MagicMock()
        chroma.count_repo.return_value = 5
        chroma.search.return_value = [
            {
                "id": "chunk1",
                "document": "def login(): pass",
                "metadata": {
                    "file": "auth.py",
                    "function": "login",
                    "class": "",
                    "symbol": "login",
                    "start_line": 1,
                    "end_line": 3,
                    "type": "function",
                },
                "distance": 0.1,
                "score": 0.9,
            }
        ]
        embedder = MagicMock()
        embedder.embed_query.return_value = [0.1, 0.2, 0.3]
        graph_engine = MagicMock()
        graph_engine.repository_stats.return_value = {"Function": 3}
        graph_engine.search_symbols.return_value = []
        graph_engine.find_dependencies.return_value = []
        graph_engine.trace_call_chain.return_value = []
        return HybridRetrievalPipeline(
            chroma_store=chroma,
            embedder=embedder,
            graph_engine=graph_engine,
            llm=None,
            retrieval_top_k=5,
            rerank_top_k=3,
        )

    def test_query_requires_context(self) -> None:
        chroma = MagicMock()
        chroma.count_repo.return_value = 0
        embedder = MagicMock()
        graph_engine = MagicMock()
        graph_engine.repository_stats.return_value = {}
        pipeline = HybridRetrievalPipeline(
            chroma_store=chroma,
            embedder=embedder,
            graph_engine=graph_engine,
            llm=None,
        )
        with pytest.raises(RetrievalError):
            pipeline.query("acme/app", "How does auth work?")

    def test_query_returns_answer_with_citations(self) -> None:
        result = self._pipeline().query("acme/app", "How does login work?")
        assert result.answer
        assert result.citations
        assert result.confidence >= 0
        assert result.strategy in RetrievalStrategy
        assert result.retrieval_stats["vector_hits"] >= 1
