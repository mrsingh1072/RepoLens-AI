"""Domain models for the code knowledge graph."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from services.graph.service import GraphNode, GraphRelationship


class NodeLabel(str, Enum):
    """Supported Neo4j node labels."""

    REPOSITORY = "Repository"
    FILE = "File"
    CLASS = "Class"
    FUNCTION = "Function"
    METHOD = "Method"
    API_ENDPOINT = "ApiEndpoint"
    DATABASE_TABLE = "DatabaseTable"
    EXTERNAL_LIBRARY = "ExternalLibrary"


class RelationshipType(str, Enum):
    """Supported Neo4j relationship types."""

    CALLS = "CALLS"
    IMPORTS = "IMPORTS"
    DEFINES = "DEFINES"
    EXTENDS = "EXTENDS"
    IMPLEMENTS = "IMPLEMENTS"
    READS_FROM = "READS_FROM"
    WRITES_TO = "WRITES_TO"


@dataclass(slots=True)
class GraphBuildResult:
    """In-memory graph produced by :class:`GraphBuilder`."""

    repo_id: str
    nodes: list[GraphNode]
    relationships: list[GraphRelationship]
    node_count: int = 0
    relationship_count: int = 0

    def __post_init__(self) -> None:
        self.node_count = len(self.nodes)
        self.relationship_count = len(self.relationships)


@dataclass(slots=True)
class GraphIndexSummary:
    """Result of indexing a repository into Neo4j."""

    repo_id: str
    nodes_written: int
    relationships_written: int
    nodes_deleted: int = 0


@dataclass(slots=True)
class DependencyResult:
    """A dependency node reachable from a symbol."""

    id: str
    label: str
    name: str
    relationship: str
    depth: int
    file_path: str | None = None


@dataclass(slots=True)
class CallChainResult:
    """A traced call path through the codebase."""

    path: list[dict[str, str]]
    depth: int


@dataclass(slots=True)
class ArchitectureLayer:
    """Aggregated files/symbols for an architecture tier."""

    layer: str
    file_count: int
    symbol_count: int
    sample_files: list[str] = field(default_factory=list)


__all__ = [
    "ArchitectureLayer",
    "CallChainResult",
    "DependencyResult",
    "GraphBuildResult",
    "GraphIndexSummary",
    "GraphNode",
    "GraphRelationship",
    "NodeLabel",
    "RelationshipType",
]
