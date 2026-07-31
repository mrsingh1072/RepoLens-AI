"""Architecture diagram generation API."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse

from app.api.deps import get_app_settings, get_graph_query_engine
from app.core.config import Settings
from app.middleware.error_handler import NotFoundError, ValidationError
from app.services.cache_service import cache_key, get_cache_service
from app.schemas.diagrams import (
    DiagramBundleResponse,
    DiagramExportResponse,
    GraphViewResponse,
    MermaidDiagramsResponse,
    VisEdgeResponse,
    VisNodeResponse,
)
from services.diagrams import DiagramGenerator
from services.graph import GraphQueryEngine, GraphServiceError

router = APIRouter(prefix="/diagrams", tags=["diagrams"])


def _decode_repo_id(repo_id: str) -> str:
    return repo_id.replace("__", "/")


def _bundle_to_response(bundle) -> DiagramBundleResponse:
    def _graph(data: dict) -> GraphViewResponse:
        return GraphViewResponse(
            nodes=[VisNodeResponse(**n) for n in data.get("nodes", [])],
            edges=[VisEdgeResponse(**e) for e in data.get("edges", [])],
        )

    return DiagramBundleResponse(
        repo_id=bundle.repo_id,
        mermaid=MermaidDiagramsResponse(
            flowchart=bundle.mermaid.flowchart,
            sequence=bundle.mermaid.sequence,
            class_diagram=bundle.mermaid.class_diagram,
        ),
        system_architecture=_graph(bundle.system_architecture),
        dependency_graph=_graph(bundle.dependency_graph),
        markdown=bundle.markdown,
        stats=bundle.stats,
    )


@router.get(
    "/{repo_id}",
    response_model=DiagramBundleResponse,
    summary="Generate architecture diagrams for a repository",
)
async def generate_diagrams(
    repo_id: str,
    engine: GraphQueryEngine = Depends(get_graph_query_engine),
    settings: Settings = Depends(get_app_settings),
) -> DiagramBundleResponse:
    """Build Mermaid diagrams, system architecture, and dependency graph views."""
    decoded = _decode_repo_id(repo_id)
    cache = get_cache_service()
    key = cache_key("diagrams", decoded)
    cached = cache.get_json(key)
    if cached:
        return DiagramBundleResponse(**cached)

    try:
        stats = engine.repository_stats(decoded)
    except GraphServiceError as exc:
        raise ValidationError(str(exc)) from exc
    if not stats:
        raise NotFoundError(f"No graph data found for repository '{decoded}'.")

    bundle = DiagramGenerator(engine).generate(decoded)
    response = _bundle_to_response(bundle)
    cache.set_json(key, response.model_dump(), ttl_seconds=settings.cache_ttl_diagrams)
    return response


@router.get(
    "/{repo_id}/export/markdown",
    response_class=PlainTextResponse,
    summary="Export diagrams as Markdown",
)
async def export_markdown(
    repo_id: str,
    engine: GraphQueryEngine = Depends(get_graph_query_engine),
) -> PlainTextResponse:
    decoded = _decode_repo_id(repo_id)
    try:
        stats = engine.repository_stats(decoded)
    except GraphServiceError as exc:
        raise ValidationError(str(exc)) from exc
    if not stats:
        raise NotFoundError(f"No graph data found for repository '{decoded}'.")
    markdown = DiagramGenerator(engine).generate(decoded).markdown
    return PlainTextResponse(
        content=markdown,
        headers={"Content-Disposition": f'attachment; filename="{decoded.replace("/", "_")}_diagrams.md"'},
    )


@router.get(
    "/{repo_id}/export/mermaid",
    response_model=DiagramExportResponse,
    summary="Export Mermaid source bundle as JSON",
)
async def export_mermaid(
    repo_id: str,
    engine: GraphQueryEngine = Depends(get_graph_query_engine),
) -> DiagramExportResponse:
    decoded = _decode_repo_id(repo_id)
    try:
        stats = engine.repository_stats(decoded)
    except GraphServiceError as exc:
        raise ValidationError(str(exc)) from exc
    if not stats:
        raise NotFoundError(f"No graph data found for repository '{decoded}'.")
    bundle = DiagramGenerator(engine).generate(decoded)
    content = (
        f"## Flowchart\n\n```mermaid\n{bundle.mermaid.flowchart}\n```\n\n"
        f"## Sequence\n\n```mermaid\n{bundle.mermaid.sequence}\n```\n\n"
        f"## Class\n\n```mermaid\n{bundle.mermaid.class_diagram}\n```\n"
    )
    return DiagramExportResponse(repo_id=decoded, format="mermaid", content=content)


@router.get(
    "/{repo_id}/export/svg",
    response_model=DiagramExportResponse,
    summary="Export Mermaid flowchart as SVG markup",
)
async def export_svg(
    repo_id: str,
    engine: GraphQueryEngine = Depends(get_graph_query_engine),
) -> DiagramExportResponse:
    """Return Mermaid flowchart source for client-side SVG rendering."""
    decoded = _decode_repo_id(repo_id)
    try:
        stats = engine.repository_stats(decoded)
    except GraphServiceError as exc:
        raise ValidationError(str(exc)) from exc
    if not stats:
        raise NotFoundError(f"No graph data found for repository '{decoded}'.")
    flowchart = DiagramGenerator(engine).generate(decoded).mermaid.flowchart
    svg = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<!-- Render with Mermaid: {decoded} -->\n'
        f"<svg xmlns=\"http://www.w3.org/2000/svg\"><desc>{flowchart}</desc></svg>"
    )
    return DiagramExportResponse(repo_id=decoded, format="svg", content=svg)
