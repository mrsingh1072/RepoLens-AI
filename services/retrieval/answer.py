"""Grounded answer generation with structured citations."""

from __future__ import annotations

import json
import logging
import re

from services.llm.base import LLMProvider
from services.retrieval.models import CodeCitation, RetrievalHit

logger = logging.getLogger(__name__)


class AnswerGenerator:
    """Generate a final answer strictly grounded in retrieved context."""

    def __init__(self, llm: LLMProvider | None = None) -> None:
        self._llm = llm

    def generate(self, question: str, hits: list[RetrievalHit]) -> tuple[str, float, str, list[CodeCitation]]:
        citations = [_hit_to_citation(hit) for hit in hits]
        if self._llm is None:
            return self._fallback_answer(question, hits, citations)

        try:
            return self._generate_with_llm(question, hits, citations)
        except Exception:
            logger.warning("LLM answer generation failed; using extractive fallback.", exc_info=True)
            return self._fallback_answer(question, hits, citations)

    def _generate_with_llm(
        self,
        question: str,
        hits: list[RetrievalHit],
        citations: list[CodeCitation],
    ) -> tuple[str, float, str, list[CodeCitation]]:
        context_blocks = []
        for index, hit in enumerate(hits):
            context_blocks.append(
                f"[{index}] file={hit.file_path} symbol={hit.symbol or hit.function_name or 'n/a'} "
                f"lines={hit.start_line}-{hit.end_line} source={hit.source}\n{hit.content[:1200]}",
            )
        prompt = f"""Answer the question using ONLY the retrieved context below.
If the context is insufficient, say you cannot determine the answer from the indexed code.

Question: {question}

Context:
{chr(10).join(context_blocks)}

Return JSON only:
{{
  "answer": "detailed answer",
  "confidence": 0.0,
  "reasoning_summary": "how you used the context",
  "citation_ids": [0, 1]
}}

Rules:
- Cite specific files/functions from the context.
- confidence is 0-1 based on context quality.
- Never invent files or functions not present in the context."""
        raw = self._llm.complete(
            prompt,
            system="You are a codebase assistant. Ground every claim in provided context.",
            temperature=0.1,
        )
        data = _parse_json(raw)
        used_ids = [int(i) for i in data.get("citation_ids") or [] if isinstance(i, int) or str(i).isdigit()]
        selected = [citations[i] for i in used_ids if 0 <= i < len(citations)] or citations[:3]
        answer = str(data.get("answer") or "").strip()
        confidence = float(data.get("confidence") or 0.5)
        reasoning = str(data.get("reasoning_summary") or "")
        if not answer:
            raise ValueError("Empty LLM answer")
        return answer, min(1.0, max(0.0, confidence)), reasoning, selected

    def _fallback_answer(
        self,
        question: str,
        hits: list[RetrievalHit],
        citations: list[CodeCitation],
    ) -> tuple[str, float, str, list[CodeCitation]]:
        top = hits[:3]
        if not top:
            return (
                "I could not find relevant indexed context to answer this question.",
                0.0,
                "No retrieval hits were available.",
                [],
            )
        parts = [
            f"Based on retrieved code in `{hit.file_path}`"
            + (f" (`{hit.symbol}`)" if hit.symbol else "")
            + f": {hit.content[:240].strip()}"
            for hit in top
        ]
        answer = (
            f"Question: {question}\n\n"
            + "Retrieved context indicates:\n- "
            + "\n- ".join(parts)
        )
        avg_score = sum(hit.score for hit in top) / len(top)
        return (
            answer,
            round(min(0.75, avg_score), 2),
            "Extractive fallback summary from top retrieval hits (LLM unavailable).",
            citations[:3],
        )


def _hit_to_citation(hit: RetrievalHit) -> CodeCitation:
    snippet = hit.content.strip()
    if len(snippet) > 500:
        snippet = snippet[:500] + "…"
    end_line = hit.end_line or (hit.start_line + max(1, snippet.count("\n")))
    return CodeCitation(
        file_path=hit.file_path,
        function_name=hit.function_name,
        class_name=hit.class_name,
        start_line=hit.start_line or 1,
        end_line=end_line,
        snippet=snippet,
        source=hit.source,
        score=round(hit.score, 3),
    )


def _parse_json(raw: str) -> dict:
    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return json.loads(text)
