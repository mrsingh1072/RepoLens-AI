"""Pydantic schemas for hybrid retrieval / query API."""

from __future__ import annotations

from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    repo_id: str = Field(..., description="Repository slug, e.g. owner/name")
    question: str = Field(..., min_length=1, max_length=4000)
    top_k: int | None = Field(default=None, ge=1, le=20)


class CodeCitationResponse(BaseModel):
    file_path: str
    function_name: str | None = None
    class_name: str | None = None
    start_line: int
    end_line: int
    snippet: str
    source: str
    score: float


class QueryResponse(BaseModel):
    repo_id: str
    question: str
    answer: str
    confidence: float
    reasoning_summary: str
    strategy: str
    intent_reasoning: str
    citations: list[CodeCitationResponse]
    retrieval_stats: dict[str, int | float | str]
