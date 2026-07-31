"""Repository analytics API."""

from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, Depends

from app.api.deps import get_app_settings
from app.core.config import Settings
from app.middleware.error_handler import NotFoundError
from app.services.cache_service import cache_key, get_cache_service
from app.schemas.analytics import (
    ComplexitySliceResponse,
    DependencyEdgeResponse,
    DependencyGraphResponse,
    DependencyNodeResponse,
    DuplicateClusterResponse,
    HeatmapCellResponse,
    LanguageSliceResponse,
    RepositoryAnalyticsResponse,
    SymbolRefResponse,
)
from services.analytics import AnalyticsComputer
from services.analytics.resolver import resolve_parse_data

router = APIRouter(prefix="/analytics", tags=["analytics"])


def _decode_repo_id(repo_id: str) -> str:
    return repo_id.replace("__", "/")


def _symbol_response(symbol) -> SymbolRefResponse | None:
    if symbol is None:
        return None
    return SymbolRefResponse(**asdict(symbol))


@router.get(
    "/{repo_id}",
    response_model=RepositoryAnalyticsResponse,
    summary="Repository code analytics",
)
async def get_repository_analytics(
    repo_id: str,
    settings: Settings = Depends(get_app_settings),
) -> RepositoryAnalyticsResponse:
    """Compute metrics, heatmaps, and dependency graphs from parse artifacts."""
    decoded = _decode_repo_id(repo_id)
    cache = get_cache_service()
    key = cache_key("analytics", decoded)
    cached = cache.get_json(key)
    if cached:
        return RepositoryAnalyticsResponse(**cached)

    parse_data = resolve_parse_data(settings.ingestion_workspace_path, decoded)
    if parse_data is None and decoded != repo_id:
        parse_data = resolve_parse_data(settings.ingestion_workspace_path, repo_id)
    if parse_data is None:
        raise NotFoundError(
            f"No parse data found for repository '{decoded}'. Ingest and index the repository first.",
        )

    analytics = AnalyticsComputer().compute(parse_data)
    graph = analytics.dependency_graph

    response = RepositoryAnalyticsResponse(
        repo_id=analytics.repo_id,
        job_id=analytics.job_id,
        file_count=analytics.file_count,
        function_count=analytics.function_count,
        class_count=analytics.class_count,
        dependency_depth=analytics.dependency_depth,
        most_complex_file=_symbol_response(analytics.most_complex_file),
        largest_function=_symbol_response(analytics.largest_function),
        duplicate_clusters=[
            DuplicateClusterResponse(
                fingerprint=cluster.fingerprint,
                count=cluster.count,
                similarity=cluster.similarity,
                symbols=[SymbolRefResponse(**asdict(s)) for s in cluster.symbols],
            )
            for cluster in analytics.duplicate_clusters
        ],
        duplicate_estimate=analytics.duplicate_estimate,
        dead_code_symbols=[SymbolRefResponse(**asdict(s)) for s in analytics.dead_code_symbols],
        dead_code_estimate=analytics.dead_code_estimate,
        language_distribution=[LanguageSliceResponse(**row) for row in analytics.language_distribution],
        complexity_distribution=[ComplexitySliceResponse(**row) for row in analytics.complexity_distribution],
        heatmap=[HeatmapCellResponse(**asdict(cell)) for cell in analytics.heatmap],
        dependency_graph=DependencyGraphResponse(
            nodes=[DependencyNodeResponse(**node) for node in graph.nodes],
            edges=[DependencyEdgeResponse(**edge) for edge in graph.edges],
            max_depth=graph.max_depth,
        ),
        summary=analytics.summary,
    )
    cache.set_json(key, response.model_dump(), ttl_seconds=settings.cache_ttl_analytics)
    return response
