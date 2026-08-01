"""Hybrid retrieval query API."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import get_hybrid_retrieval_pipeline
from app.middleware.error_handler import ValidationError
from app.schemas.query import CodeCitationResponse, QueryRequest, QueryResponse
from services.retrieval import HybridRetrievalPipeline, RetrievalError

router = APIRouter(prefix="/query", tags=["query"])


@router.post("", response_model=QueryResponse, summary="Ask a question about a repository")
async def ask_repository(
    body: QueryRequest,
    pipeline: HybridRetrievalPipeline = Depends(get_hybrid_retrieval_pipeline),
) -> QueryResponse:
    """Run hybrid retrieval (vector + graph), rerank, and generate a grounded answer."""
    try:
        result = pipeline.query(body.repo_id, body.question)
    except RetrievalError as exc:
        raise ValidationError(str(exc)) from exc

    return QueryResponse(
        repo_id=body.repo_id,
        question=body.question,
        answer=result.answer,
        confidence=result.confidence,
        reasoning_summary=result.reasoning_summary,
        strategy=result.strategy.value,
        intent_reasoning=result.intent_reasoning,
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
        retrieval_stats=result.retrieval_stats,
    )
