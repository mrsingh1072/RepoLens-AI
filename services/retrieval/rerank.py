"""LLM-based reranking of merged retrieval hits."""

from __future__ import annotations

import json
import logging
import re

from services.llm.base import LLMProvider
from services.retrieval.models import RetrievalHit

logger = logging.getLogger(__name__)


class ContextReranker:
    """Score and reorder retrieved context items for answer generation."""

    def __init__(self, llm: LLMProvider | None = None) -> None:
        self._llm = llm

    def rerank(self, question: str, hits: list[RetrievalHit], *, top_k: int = 5) -> list[RetrievalHit]:
        if not hits:
            return []
        if self._llm is None:
            return hits[:top_k]

        try:
            return self._rerank_with_llm(question, hits, top_k=top_k)
        except Exception:
            logger.warning("LLM rerank failed; using score order.", exc_info=True)
            return hits[:top_k]

    def _rerank_with_llm(self, question: str, hits: list[RetrievalHit], *, top_k: int) -> list[RetrievalHit]:
        catalog = []
        for index, hit in enumerate(hits):
            catalog.append(
                {
                    "id": index,
                    "source": hit.source,
                    "file_path": hit.file_path,
                    "symbol": hit.symbol or hit.function_name or hit.class_name,
                    "preview": hit.content[:400],
                },
            )
        prompt = f"""Question: {question}

Context candidates:
{json.dumps(catalog, indent=2)}

Return JSON array of objects sorted by relevance:
[{{"id": 0, "score": 0.0}}]

Scores must be between 0 and 1. Include every candidate id."""
        raw = self._llm.complete(prompt, system="You rerank code retrieval results. Output JSON only.")
        scores = self._parse_scores(raw)
        scored: list[RetrievalHit] = []
        for index, hit in enumerate(hits):
            llm_score = scores.get(index, hit.score)
            updated = RetrievalHit(
                hit_id=hit.hit_id,
                source=hit.source,
                file_path=hit.file_path,
                content=hit.content,
                score=min(1.0, (hit.score * 0.4) + (llm_score * 0.6)),
                function_name=hit.function_name,
                class_name=hit.class_name,
                symbol=hit.symbol,
                start_line=hit.start_line,
                end_line=hit.end_line,
                chunk_type=hit.chunk_type,
                graph_relationship=hit.graph_relationship,
            )
            scored.append(updated)
        scored.sort(key=lambda h: h.score, reverse=True)
        return scored[:top_k]

    @staticmethod
    def _parse_scores(raw: str) -> dict[int, float]:
        text = raw.strip()
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*", "", text)
            text = re.sub(r"\s*```$", "", text)
        data = json.loads(text)
        scores: dict[int, float] = {}
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict) and "id" in item:
                    scores[int(item["id"])] = float(item.get("score", 0.0))
        return scores
