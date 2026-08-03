"""Pydantic schemas for the AI Software Engineer agent API."""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.schemas.query import CodeCitationResponse


class AgentChatRequest(BaseModel):
    repo_id: str = Field(..., description="Repository slug, e.g. owner/name")
    question: str = Field(..., min_length=1, max_length=4000)
    session_id: str | None = Field(
        default=None,
        description="Conversation session id; omit to start a new session",
    )


class AgentChatResponse(BaseModel):
    repo_id: str
    session_id: str
    question: str
    answer: str
    confidence: float
    reasoning_steps: list[str]
    reasoning_summary: str = ""
    plan: list[str]
    tools_used: list[str]
    file_references: list[str] = Field(default_factory=list)
    function_references: list[str] = Field(default_factory=list)
    follow_up_suggestions: list[str] = Field(default_factory=list)
    citations: list[CodeCitationResponse]
