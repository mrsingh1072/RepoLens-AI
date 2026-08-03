"""Pydantic schemas for repository analytics API."""

from __future__ import annotations

from pydantic import BaseModel, Field


class SymbolRefResponse(BaseModel):
    name: str
    file_path: str
    start_line: int
    end_line: int
    kind: str
    lines: int = 0
    complexity_score: int = 0


class DuplicateClusterResponse(BaseModel):
    fingerprint: str
    count: int
    similarity: float
    symbols: list[SymbolRefResponse]


class LanguageSliceResponse(BaseModel):
    language: str
    files: int
    lines: int
    percentage: float


class ComplexitySliceResponse(BaseModel):
    level: str
    count: int


class HeatmapCellResponse(BaseModel):
    path: str
    directory: str
    language: str
    lines: int
    complexity_score: int
    symbol_count: int
    complexity_label: str


class DependencyNodeResponse(BaseModel):
    id: str
    label: str
    path: str
    group: str


class DependencyEdgeResponse(BaseModel):
    source: str
    target: str
    label: str


class DependencyGraphResponse(BaseModel):
    nodes: list[DependencyNodeResponse]
    edges: list[DependencyEdgeResponse]
    max_depth: int


class RepositoryAnalyticsResponse(BaseModel):
    repo_id: str
    job_id: str
    file_count: int
    function_count: int
    class_count: int
    dependency_depth: int
    most_complex_file: SymbolRefResponse | None = None
    largest_function: SymbolRefResponse | None = None
    duplicate_clusters: list[DuplicateClusterResponse] = Field(default_factory=list)
    duplicate_estimate: int = 0
    dead_code_symbols: list[SymbolRefResponse] = Field(default_factory=list)
    dead_code_estimate: int = 0
    language_distribution: list[LanguageSliceResponse] = Field(default_factory=list)
    complexity_distribution: list[ComplexitySliceResponse] = Field(default_factory=list)
    heatmap: list[HeatmapCellResponse] = Field(default_factory=list)
    dependency_graph: DependencyGraphResponse
    summary: dict[str, int | float | str | None] = Field(default_factory=dict)
