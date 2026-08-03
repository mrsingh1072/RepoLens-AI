"""Pydantic schemas for architecture diagram generation API."""

from __future__ import annotations

from pydantic import BaseModel, Field


class VisNodeResponse(BaseModel):
    id: str
    label: str
    kind: str
    group: str = ""
    description: str = ""
    file_path: str = ""
    x: float = 0.0
    y: float = 0.0


class VisEdgeResponse(BaseModel):
    id: str
    source: str
    target: str
    label: str = ""
    kind: str = "default"


class GraphViewResponse(BaseModel):
    nodes: list[VisNodeResponse] = Field(default_factory=list)
    edges: list[VisEdgeResponse] = Field(default_factory=list)


class MermaidDiagramsResponse(BaseModel):
    flowchart: str
    sequence: str
    class_diagram: str


class DiagramBundleResponse(BaseModel):
    repo_id: str
    mermaid: MermaidDiagramsResponse
    system_architecture: GraphViewResponse
    dependency_graph: GraphViewResponse
    markdown: str
    stats: dict[str, int | str] = Field(default_factory=dict)


class DiagramExportResponse(BaseModel):
    repo_id: str
    format: str
    content: str
