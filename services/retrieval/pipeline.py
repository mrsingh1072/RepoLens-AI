"""Hybrid retrieval orchestrator."""

from __future__ import annotations

import logging

from services.embeddings.chroma_store import ChromaEmbeddingStore
from services.embeddings.embedding_service import JinaEmbeddingService
from services.graph.query_engine import GraphQueryEngine
from services.llm.base import LLMProvider
from services.retrieval.answer import AnswerGenerator
from services.retrieval.graph import GraphRetriever
from services.retrieval.intent import IntentAnalyzer
from services.retrieval.merge import merge_hits
from services.retrieval.models import HybridQueryResult, RetrievalStrategy
from services.retrieval.rerank import ContextReranker
from services.retrieval.vector import VectorRetriever

logger = logging.getLogger(__name__)


class RetrievalError(RuntimeError):
    """Raised when retrieval cannot produce any context."""


class HybridRetrievalPipeline:
    """End-to-end hybrid retrieval: intent → search → merge → rerank → answer."""

    def __init__(
        self,
        *,
        chroma_store: ChromaEmbeddingStore,
        embedder: JinaEmbeddingService,
        graph_engine: GraphQueryEngine | None = None,
        llm: LLMProvider | None = None,
        retrieval_top_k: int = 8,
        rerank_top_k: int = 5,
        neo4j_enabled: bool = True,
    ) -> None:
        self._vector = VectorRetriever(chroma_store, embedder)
        self._graph = GraphRetriever(graph_engine) if graph_engine is not None else None
        self._intent = IntentAnalyzer(llm)
        self._reranker = ContextReranker(llm)
        self._answer = AnswerGenerator(llm)
        self._retrieval_top_k = max(1, retrieval_top_k)
        self._rerank_top_k = max(1, rerank_top_k)
        self._neo4j_enabled = neo4j_enabled and graph_engine is not None

    def query(self, repo_id: str, question: str) -> HybridQueryResult:
        question = question.strip()
        if not question:
            raise RetrievalError("Question must not be empty.")

        intent = self._intent.analyze(question)
        logger.info(
            "hybrid_query repo=%s strategy=%s symbols=%s",
            repo_id,
            intent.strategy.value,
            intent.symbols,
        )

        vector_hits = []
        graph_hits = []
        use_vector = intent.strategy in {RetrievalStrategy.VECTOR, RetrievalStrategy.HYBRID}
        use_graph = intent.strategy in {RetrievalStrategy.GRAPH, RetrievalStrategy.HYBRID}

        if use_vector:
            vector_hits = self._vector.search(repo_id, question, top_k=self._retrieval_top_k)

        if use_graph and self._neo4j_enabled and self._graph is not None:
            graph_hits = self._graph.search(
                repo_id,
                question,
                symbols=intent.symbols,
                top_k=self._retrieval_top_k,
            )
        elif use_graph and not self._neo4j_enabled:
            logger.warning("Graph retrieval requested but Neo4j is disabled.")

        if intent.strategy == RetrievalStrategy.GRAPH and not graph_hits and vector_hits:
            merged = merge_hits([], vector_hits)
        elif intent.strategy == RetrievalStrategy.VECTOR and not vector_hits and graph_hits:
            merged = merge_hits(graph_hits, [])
        else:
            merged = merge_hits(vector_hits, graph_hits)

        if not merged:
            raise RetrievalError(
                f"No indexed context found for repository '{repo_id}'. "
                "Ensure the repository is fully ingested (embeddings and graph).",
            )

        reranked = self._reranker.rerank(question, merged, top_k=self._rerank_top_k)
        answer, confidence, reasoning, citations = self._answer.generate(question, reranked)

        return HybridQueryResult(
            answer=answer,
            confidence=confidence,
            reasoning_summary=reasoning,
            strategy=intent.strategy,
            intent_reasoning=intent.reasoning,
            citations=citations,
            retrieval_stats={
                "vector_hits": len(vector_hits),
                "graph_hits": len(graph_hits),
                "merged_hits": len(merged),
                "reranked_hits": len(reranked),
                "query_type": intent.query_type,
            },
        )
