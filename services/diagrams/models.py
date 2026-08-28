"""Diagram generation domain models."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class VisNode:
    id: str
    label: str
    kind: str
    group: str = ""
    description: str = ""
    file_path: str = ""
    x: float = 0.0
    y: float = 0.0


@dataclass(slots=True)
class VisEdge:
    id: str
    source: str
    target: str
    label: str = ""
    kind: str = "default"


@dataclass(slots=True)
class MermaidDiagrams:
    flowchart: str
    sequence: str
    class_diagram: str


@dataclass(slots=True)
class DiagramBundle:
    repo_id: str
    mermaid: MermaidDiagrams
    system_architecture: dict[str, list]
    dependency_graph: dict[str, list]
    markdown: str
    stats: dict[str, int | str] = field(default_factory=dict)
