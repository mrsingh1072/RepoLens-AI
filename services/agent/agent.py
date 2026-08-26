"""AI Software Engineer agent entry point."""

from __future__ import annotations

import asyncio
import logging
import uuid
from collections.abc import AsyncIterator

from services.agent.enrichment import enrich_agent_payload
from services.agent.graph import build_agent_graph, dict_to_citation
from services.agent.memory import RepoConversationMemory, get_conversation_memory
from services.agent.models import AgentResponse
from services.agent.synthesis import try_meta_answer
from services.agent.tools import AgentToolContext
from services.graph.query_engine import GraphQueryEngine
from services.llm.base import LLMProvider
from services.retrieval.graph import GraphRetriever
from services.agent.streaming import format_sse, stream_answer_tokens

logger = logging.getLogger(__name__)


def _finalize_response(
    *,
    repo_id: str,
    session_id: str,
    question: str,
    answer: str,
    confidence: float,
    reasoning_steps: list[str],
    plan: list[str],
    tools_used: list[str],
    citations: list,
) -> AgentResponse:
    enriched = enrich_agent_payload(
        answer=answer,
        citations=citations,
        reasoning_steps=reasoning_steps,
        question=question,
        repo_id=repo_id,
    )
    return AgentResponse(
        repo_id=repo_id,
        session_id=session_id,
        question=question,
        answer=enriched["answer"],
        confidence=confidence,
        reasoning_steps=reasoning_steps,
        plan=plan,
        tools_used=tools_used,
        citations=citations,
        reasoning_summary=enriched["reasoning_summary"],
        file_references=enriched["file_references"],
        function_references=enriched["function_references"],
        follow_up_suggestions=enriched["follow_up_suggestions"],
    )


class SoftwareEngineerAgent:
    """LangGraph agent with repository-scoped memory and grounded tools."""

    def __init__(
        self,
        *,
        vector: VectorRetriever,
        graph: GraphRetriever | None,
        graph_engine: GraphQueryEngine | None,
        llm: LLMProvider | None,
        memory: RepoConversationMemory | None = None,
        top_k: int = 8,
    ) -> None:
        self._memory = memory or get_conversation_memory()
        self._top_k = top_k
        self._llm = llm
        self._vector = vector
        self._graph = graph
        self._graph_engine = graph_engine

    def run(
        self,
        repo_id: str,
        question: str,
        *,
        session_id: str | None = None,
    ) -> AgentResponse:
        session = session_id or f"{repo_id}::default"
        question = question.strip()
        history = self._memory.history(repo_id, session, limit=12)

        meta = try_meta_answer(repo_id, question)
        if meta is not None:
            answer, confidence, reasoning = meta
            self._memory.append(repo_id, session, "user", question)
            self._memory.append(repo_id, session, "assistant", answer)
            return _finalize_response(
                repo_id=repo_id,
                session_id=session,
                question=question,
                answer=answer,
                confidence=confidence,
                reasoning_steps=[f"Synthesis: {reasoning}"],
                plan=[],
                tools_used=[],
                citations=[],
            )

        ctx = AgentToolContext(
            repo_id=repo_id,
            vector=self._vector,
            graph=self._graph,
            graph_engine=self._graph_engine,
            top_k=self._top_k,
        )
        graph = build_agent_graph(ctx, self._llm)
        final_state = graph.invoke(
            {
                "repo_id": repo_id,
                "session_id": session,
                "question": question,
                "history": history,
                "plan_steps": [],
                "step_index": 0,
                "tool_results": [],
                "reasoning_steps": [],
                "citations": [],
                "final_answer": "",
                "confidence": 0.0,
            },
        )

        answer = str(final_state.get("final_answer") or "").strip()
        confidence = float(final_state.get("confidence") or 0.0)
        reasoning_steps = list(final_state.get("reasoning_steps") or [])
        plan_steps = final_state.get("plan_steps") or []
        tool_results = final_state.get("tool_results") or []

        raw_citations = final_state.get("citations") or []
        seen: set[tuple[str, str, int]] = set()
        citations = []
        for item in raw_citations:
            c = dict_to_citation(item)
            key = (c.file_path, c.snippet[:80], c.start_line)
            if key in seen or not c.file_path:
                continue
            seen.add(key)
            citations.append(c)

        tools_used = [str(r.get("tool")) for r in tool_results if r.get("tool")]
        plan_labels = [
            f"{step.get('tool')}({step.get('inputs', {})})" for step in plan_steps if step.get("tool")
        ]

        self._memory.append(repo_id, session, "user", question)
        self._memory.append(repo_id, session, "assistant", answer)

        logger.info(
            "agent_complete repo=%s session=%s tools=%s citations=%d",
            repo_id,
            session,
            tools_used,
            len(citations),
        )

        return _finalize_response(
            repo_id=repo_id,
            session_id=session,
            question=question,
            answer=answer or "not found in repository context",
            confidence=confidence,
            reasoning_steps=reasoning_steps,
            plan=plan_labels,
            tools_used=tools_used,
            citations=citations,
        )

    async def run_stream(
        self,
        repo_id: str,
        question: str,
        *,
        session_id: str | None = None,
    ) -> AsyncIterator[str]:
        """Yield SSE frames: status → meta → token chunks → done."""
        yield format_sse("status", {"message": "Analyzing repository context…"})

        result = await asyncio.to_thread(self.run, repo_id, question, session_id=session_id)

        yield format_sse(
            "meta",
            {
                "repo_id": result.repo_id,
                "session_id": result.session_id,
                "question": result.question,
                "confidence": result.confidence,
                "reasoning_steps": result.reasoning_steps,
                "reasoning_summary": result.reasoning_summary,
                "plan": result.plan,
                "tools_used": result.tools_used,
                "file_references": result.file_references,
                "function_references": result.function_references,
                "follow_up_suggestions": result.follow_up_suggestions,
                "citations": [
                    {
                        "file_path": c.file_path,
                        "function_name": c.function_name,
                        "class_name": c.class_name,
                        "start_line": c.start_line,
                        "end_line": c.end_line,
                        "snippet": c.snippet,
                        "source": c.source,
                        "score": c.score,
                    }
                    for c in result.citations
                ],
            },
        )

        async for token in stream_answer_tokens(result.answer):
            yield format_sse("token", {"text": token})

        yield format_sse("done", {"answer": result.answer})

    @staticmethod
    def new_session_id() -> str:
        return f"sess-{uuid.uuid4().hex[:12]}"
