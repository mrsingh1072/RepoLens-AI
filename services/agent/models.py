"""Agent domain models."""

from __future__ import annotations

from dataclasses import dataclass, field

from services.retrieval.models import CodeCitation


NOT_FOUND = "not found in repository context"


@dataclass(slots=True)
class PlanStep:
    tool: str
    inputs: dict[str, str] = field(default_factory=dict)
    rationale: str = ""


@dataclass(slots=True)
class ToolExecutionResult:
    tool: str
    found: bool
    summary: str
    data: list[dict] = field(default_factory=list)
    citations: list[CodeCitation] = field(default_factory=list)


@dataclass(slots=True)
class AgentResponse:
    repo_id: str
    session_id: str
    question: str
    answer: str
    confidence: float
    reasoning_steps: list[str]
    plan: list[str]
    tools_used: list[str]
    citations: list[CodeCitation]
    reasoning_summary: str = ""
    file_references: list[str] = field(default_factory=list)
    function_references: list[str] = field(default_factory=list)
    follow_up_suggestions: list[str] = field(default_factory=list)
