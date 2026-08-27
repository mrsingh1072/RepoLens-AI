"""Analytics domain models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class SymbolRef:
    name: str
    file_path: str
    start_line: int
    end_line: int
    kind: str
    lines: int = 0
    complexity_score: int = 0


@dataclass(slots=True)
class DuplicateCluster:
    fingerprint: str
    count: int
    symbols: list[SymbolRef]
    similarity: float


@dataclass(slots=True)
class HeatmapCell:
    path: str
    directory: str
    language: str
    lines: int
    complexity_score: int
    symbol_count: int
    complexity_label: str


@dataclass(slots=True)
class DependencyGraph:
    nodes: list[dict[str, str]]
    edges: list[dict[str, str]]
    max_depth: int


@dataclass(slots=True)
class RepositoryAnalytics:
    repo_id: str
    job_id: str
    file_count: int
    function_count: int
    class_count: int
    dependency_depth: int
    most_complex_file: SymbolRef | None
    largest_function: SymbolRef | None
    duplicate_clusters: list[DuplicateCluster]
    duplicate_estimate: int
    dead_code_symbols: list[SymbolRef]
    dead_code_estimate: int
    language_distribution: list[dict[str, Any]]
    complexity_distribution: list[dict[str, Any]]
    heatmap: list[HeatmapCell]
    dependency_graph: DependencyGraph
    summary: dict[str, Any] = field(default_factory=dict)
