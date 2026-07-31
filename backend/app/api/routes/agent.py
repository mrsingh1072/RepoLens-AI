"""AI Software Engineer agent API."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.api.deps import get_software_engineer_agent
from app.middleware.error_handler import ValidationError
from app.schemas.agent import AgentChatRequest, AgentChatResponse
from app.schemas.query import CodeCitationResponse
from services.agent import SoftwareEngineerAgent

router = APIRouter(prefix="/agent", tags=["agent"])


def _to_response(result) -> AgentChatResponse:
    return AgentChatResponse(
        repo_id=result.repo_id,
        session_id=result.session_id,
        question=result.question,
        answer=result.answer,
        confidence=result.confidence,
        reasoning_steps=result.reasoning_steps,
        reasoning_summary=result.reasoning_summary,
        plan=result.plan,
        tools_used=result.tools_used,
        file_references=result.file_references,
        function_references=result.function_references,
        follow_up_suggestions=result.follow_up_suggestions,
        citations=[
            CodeCitationResponse(
                file_path=c.file_path,
                function_name=c.function_name,
                class_name=c.class_name,
                start_line=c.start_line,
                end_line=c.end_line,
                snippet=c.snippet,
                source=c.source,
                score=c.score,
            )
            for c in result.citations
        ],
    )


@router.post("/chat", response_model=AgentChatResponse, summary="Chat with the AI Software Engineer agent")
async def agent_chat(
    body: AgentChatRequest,
    agent: SoftwareEngineerAgent = Depends(get_software_engineer_agent),
) -> AgentChatResponse:
    """Plan, execute tools dynamically, and synthesize a grounded answer with citations."""
    question = body.question.strip()
    if not question:
        raise ValidationError("Question must not be empty.")

    result = agent.run(body.repo_id, question, session_id=body.session_id)
    return _to_response(result)


@router.post(
    "/chat/stream",
    summary="Stream chat with the AI Software Engineer agent (SSE)",
    response_class=StreamingResponse,
)
async def agent_chat_stream(
    body: AgentChatRequest,
    agent: SoftwareEngineerAgent = Depends(get_software_engineer_agent),
) -> StreamingResponse:
    """Server-Sent Events: status → metadata → answer tokens → done."""
    question = body.question.strip()
    if not question:
        raise ValidationError("Question must not be empty.")

    async def event_generator():
        async for frame in agent.run_stream(body.repo_id, question, session_id=body.session_id):
            yield frame

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
