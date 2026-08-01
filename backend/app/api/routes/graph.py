"""Code graph query API routes."""

from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_graph_query_engine
from app.middleware.error_handler import NotFoundError, ValidationError
from app.schemas.graph import (
    ArchitectureLayerItem,
    ArchitectureResponse,
    CallChainItem,
    CallChainNode,
    CallChainResponse,
    DependencyItem,
    DependencyResponse,
    GraphStatsResponse,
)
from services.graph import GraphQueryEngine, GraphServiceError

router = APIRouter(prefix="/graph", tags=["graph"])


def _decode_repo_id(repo_id: str) -> str:
    return repo_id.replace("__", "/")


@router.get(
    "/{repo_id}/dependencies",
    response_model=DependencyResponse,
    summary="Find symbol dependencies",
)
async def get_dependencies(
    repo_id: str,
    symbol: str = Query(..., description="Function, method, or class name."),
    max_depth: int = Query(default=3, ge=1, le=5),
    engine: GraphQueryEngine = Depends(get_graph_query_engine),
) -> DependencyResponse:
    """Return CALLS, IMPORTS, EXTENDS, and IMPLEMENTS dependencies for a symbol."""
    decoded = _decode_repo_id(repo_id)
    try:
        deps = engine.find_dependencies(decoded, symbol=symbol, max_depth=max_depth)
    except GraphServiceError as exc:
        raise ValidationError(str(exc)) from exc
    if not deps and not engine.repository_stats(decoded):
        raise NotFoundError(f"No graph data found for repository '{decoded}'.")
    return DependencyResponse(
        repo_id=decoded,
        symbol=symbol,
        dependencies=[DependencyItem(**asdict(dep)) for dep in deps],
    )


@router.get(
    "/{repo_id}/call-chain",
    response_model=CallChainResponse,
    summary="Trace function call chains",
)
async def get_call_chain(
    repo_id: str,
    symbol: str = Query(..., description="Starting function or method name."),
    max_depth: int = Query(default=8, ge=1, le=12),
    engine: GraphQueryEngine = Depends(get_graph_query_engine),
) -> CallChainResponse:
    """Trace outgoing CALLS paths from a symbol."""
    decoded = _decode_repo_id(repo_id)
    try:
        chains = engine.trace_call_chain(decoded, symbol=symbol, max_depth=max_depth)
    except GraphServiceError as exc:
        raise ValidationError(str(exc)) from exc
    return CallChainResponse(
        repo_id=decoded,
        symbol=symbol,
        chains=[
            CallChainItem(
                depth=chain.depth,
                path=[CallChainNode(**node) for node in chain.path],
            )
            for chain in chains
        ],
    )


@router.get(
    "/{repo_id}/architecture",
    response_model=ArchitectureResponse,
    summary="Detect architecture layers",
)
async def get_architecture(
    repo_id: str,
    engine: GraphQueryEngine = Depends(get_graph_query_engine),
) -> ArchitectureResponse:
    """Classify repository files into presentation, business, data, and other layers."""
    decoded = _decode_repo_id(repo_id)
    try:
        layers = engine.detect_architecture_layers(decoded)
        cross_layer = engine.cross_layer_calls(decoded)
    except GraphServiceError as exc:
        raise ValidationError(str(exc)) from exc
    if not layers:
        raise NotFoundError(f"No graph data found for repository '{decoded}'.")
    return ArchitectureResponse(
        repo_id=decoded,
        layers=[ArchitectureLayerItem(**asdict(layer)) for layer in layers],
        cross_layer_calls=cross_layer,
    )


@router.get(
    "/{repo_id}/stats",
    response_model=GraphStatsResponse,
    summary="Graph node statistics",
)
async def get_graph_stats(
    repo_id: str,
    engine: GraphQueryEngine = Depends(get_graph_query_engine),
) -> GraphStatsResponse:
    """Return node counts grouped by label for a repository."""
    decoded = _decode_repo_id(repo_id)
    try:
        counts = engine.repository_stats(decoded)
    except GraphServiceError as exc:
        raise ValidationError(str(exc)) from exc
    if not counts:
        raise NotFoundError(f"No graph data found for repository '{decoded}'.")
    return GraphStatsResponse(repo_id=decoded, node_counts=counts)
