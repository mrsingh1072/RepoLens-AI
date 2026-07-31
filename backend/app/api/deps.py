"""Reusable FastAPI dependencies.

Provides request-scoped access to shared resources (currently settings) so
route handlers stay decoupled from module-level globals and remain testable.
"""

from __future__ import annotations

from fastapi import Request

from app.core.config import Settings, get_settings
from app.services.ingestion.pipeline import IngestionPipeline
from app.services.llm_service import LLMService, build_llm_service
from services.agent import SoftwareEngineerAgent, get_conversation_memory
from services.graph import GraphQueryEngine, GraphService
from services.retrieval import HybridRetrievalPipeline
from services.retrieval.graph import GraphRetriever
from services.retrieval.vector import VectorRetriever


def get_app_settings(request: Request) -> Settings:
    """Return the settings bound to the current application instance.

    Falls back to the cached environment settings if none were attached (e.g.
    when a route is exercised outside of :func:`app.main.create_app`).
    """
    settings: Settings | None = getattr(request.app.state, "settings", None)
    return settings or get_settings()


def get_ingestion_pipeline(request: Request) -> IngestionPipeline:
    """Return an ingestion pipeline bound to the current app settings."""
    settings = get_app_settings(request)
    return IngestionPipeline(settings)


def get_graph_query_engine(request: Request) -> GraphQueryEngine:
    """Return a connected graph query engine for the current request."""
    settings = get_app_settings(request)
    graph = GraphService(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password)
    graph.connect()
    return GraphQueryEngine(graph)


def get_llm_service(request: Request) -> LLMService:
    """Return the Groq-backed LLM service for the current request."""
    return build_llm_service(get_app_settings(request))


def _resolve_llm_provider(settings: Settings):
    """Return the configured LLM provider, or None if misconfigured."""
    from services.llm.base import LLMProviderError

    try:
        return build_llm_service(settings).provider
    except LLMProviderError:
        return None


def get_hybrid_retrieval_pipeline(request: Request) -> HybridRetrievalPipeline:
    """Build a hybrid retrieval pipeline for the current request."""
    settings = get_app_settings(request)

    from services.embeddings.chroma_store import ChromaEmbeddingStore
    from services.embeddings.embedding_service import JinaEmbeddingService

    if not settings.jina_api_key:
        from app.middleware.error_handler import ValidationError

        raise ValidationError("JINA_API_KEY is required for hybrid retrieval embeddings.")

    chroma = ChromaEmbeddingStore(
        host=settings.chroma_host if settings.chroma_use_http else None,
        port=settings.chroma_port if settings.chroma_use_http else None,
        persistent_path=settings.chroma_persistent_path_resolved,
        collection_name=settings.chroma_collection,
    )
    embedder = JinaEmbeddingService(
        settings.jina_api_key,
        model=settings.jina_embedding_model,
        batch_size=settings.jina_batch_size,
        api_url=settings.jina_api_url,
        timeout_seconds=settings.jina_timeout_seconds,
        max_retries=settings.jina_max_retries,
        dimensions=settings.jina_dimensions,
    )

    graph_engine: GraphQueryEngine | None = None
    if settings.neo4j_enabled:
        try:
            graph = GraphService(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password)
            graph.connect()
            graph_engine = GraphQueryEngine(graph)
        except Exception:
            graph_engine = None

    llm = _resolve_llm_provider(settings)

    return HybridRetrievalPipeline(
        chroma_store=chroma,
        embedder=embedder,
        graph_engine=graph_engine,
        llm=llm,
        retrieval_top_k=settings.retrieval_top_k,
        rerank_top_k=settings.rerank_top_k,
        neo4j_enabled=settings.neo4j_enabled,
    )


def get_software_engineer_agent(request: Request) -> SoftwareEngineerAgent:
    """Build the LangGraph AI Software Engineer agent for the current request."""
    settings = get_app_settings(request)

    from services.embeddings.chroma_store import ChromaEmbeddingStore
    from services.embeddings.embedding_service import JinaEmbeddingService

    if not settings.jina_api_key:
        from app.middleware.error_handler import ValidationError

        raise ValidationError("JINA_API_KEY is required for agent code search.")

    chroma = ChromaEmbeddingStore(
        host=settings.chroma_host if settings.chroma_use_http else None,
        port=settings.chroma_port if settings.chroma_use_http else None,
        persistent_path=settings.chroma_persistent_path_resolved,
        collection_name=settings.chroma_collection,
    )
    embedder = JinaEmbeddingService(
        settings.jina_api_key,
        model=settings.jina_embedding_model,
        batch_size=settings.jina_batch_size,
        api_url=settings.jina_api_url,
        timeout_seconds=settings.jina_timeout_seconds,
        max_retries=settings.jina_max_retries,
        dimensions=settings.jina_dimensions,
    )

    graph_engine: GraphQueryEngine | None = None
    if settings.neo4j_enabled:
        try:
            graph = GraphService(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password)
            graph.connect()
            graph_engine = GraphQueryEngine(graph)
        except Exception:
            graph_engine = None

    llm = _resolve_llm_provider(settings)

    vector = VectorRetriever(chroma, embedder)
    graph_retriever = GraphRetriever(graph_engine) if graph_engine is not None else None

    return SoftwareEngineerAgent(
        vector=vector,
        graph=graph_retriever,
        graph_engine=graph_engine,
        llm=llm,
        memory=get_conversation_memory(),
        top_k=settings.retrieval_top_k,
    )
