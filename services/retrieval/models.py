"""Hybrid retrieval domain models."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class RetrievalStrategy(str, Enum):
    VECTOR = "vector"
    GRAPH = "graph"
    HYBRID = "hybrid"


@dataclass(slots=True)
class QueryIntent:
    """Output of the intent analyzer."""

    strategy: RetrievalStrategy
    symbols: list[str] = field(default_factory=list)
    reasoning: str = ""
    query_type: str = "general"


@dataclass(slots=True)
class RetrievalHit:
    """A single retrieved context item from vector or graph search."""

    hit_id: str
    source: str  # vector | graph
    file_path: str
    content: str
    score: float
    function_name: str | None = None
    class_name: str | None = None
    symbol: str | None = None
    start_line: int = 0
    end_line: int = 0
    chunk_type: str | None = None
    graph_relationship: str | None = None


@dataclass(slots=True)
class CodeCitation:
    """Structured citation attached to the final answer."""

    file_path: str
    function_name: str | None
    class_name: str | None
    start_line: int
    end_line: int
    snippet: str
    source: str
    score: float


@dataclass(slots=True)
class HybridQueryResult:
    """Full hybrid retrieval + generation response."""

    answer: str
    confidence: float
    reasoning_summary: str
    strategy: RetrievalStrategy
    intent_reasoning: str
    citations: list[CodeCitation]
    retrieval_stats: dict[str, int | float | str]
