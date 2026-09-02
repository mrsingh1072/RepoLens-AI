"""Query intent analysis — LLM with heuristic fallback."""

from __future__ import annotations

import json
import logging
import re

from services.llm.base import LLMProvider
from services.retrieval.models import QueryIntent, RetrievalStrategy

logger = logging.getLogger(__name__)

_GRAPH_KEYWORDS = (
    "call chain",
    "calls",
    "dependency",
    "dependencies",
    "imports",
    "extends",
    "implements",
    "architecture",
    "layer",
    "relationship",
    "who calls",
    "what calls",
)
_VECTOR_KEYWORDS = (
    "where is",
    "how does",
    "explain",
    "what is",
    "show me",
    "find",
    "configured",
    "implementation",
)


class IntentAnalyzer:
    """Decide retrieval strategy and extract symbol hints from a user query."""

    def __init__(self, llm: LLMProvider | None = None) -> None:
        self._llm = llm

    def analyze(self, question: str) -> QueryIntent:
        if self._llm is not None:
            try:
                return self._analyze_with_llm(question)
            except Exception:
                logger.warning("LLM intent analysis failed; using heuristics.", exc_info=True)
        return self._analyze_heuristic(question)

    def _analyze_with_llm(self, question: str) -> QueryIntent:
        prompt = f"""Analyze this codebase question and return JSON only.

Question: {question}

Return:
{{
  "strategy": "vector" | "graph" | "hybrid",
  "symbols": ["SymbolName", ...],
  "query_type": "architecture|dependency|implementation|location|general",
  "reasoning": "one sentence"
}}

Rules:
- Use "graph" for call chains, dependencies, imports, architecture layers.
- Use "vector" for broad conceptual or location questions.
- Use "hybrid" when both structure and implementation details are needed.
- Extract class/function/API names mentioned or implied in the question."""
        raw = self._llm.complete(prompt, system="You classify code search queries. Output JSON only.")
        return self._parse_intent_json(raw, question)

    def _parse_intent_json(self, raw: str, question: str) -> QueryIntent:
        text = raw.strip()
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*", "", text)
            text = re.sub(r"\s*```$", "", text)
        data = json.loads(text)
        strategy_raw = str(data.get("strategy", "hybrid")).lower()
        try:
            strategy = RetrievalStrategy(strategy_raw)
        except ValueError:
            strategy = RetrievalStrategy.HYBRID
        symbols = [str(s) for s in data.get("symbols") or [] if s]
        if not symbols:
            symbols = _extract_symbol_candidates(question)
        return QueryIntent(
            strategy=strategy,
            symbols=symbols,
            reasoning=str(data.get("reasoning") or ""),
            query_type=str(data.get("query_type") or "general"),
        )

    def _analyze_heuristic(self, question: str) -> QueryIntent:
        lowered = question.lower()
        graph_score = sum(1 for kw in _GRAPH_KEYWORDS if kw in lowered)
        vector_score = sum(1 for kw in _VECTOR_KEYWORDS if kw in lowered)
        if graph_score > vector_score:
            strategy = RetrievalStrategy.GRAPH if graph_score >= 2 else RetrievalStrategy.HYBRID
        elif vector_score > graph_score:
            strategy = RetrievalStrategy.VECTOR if vector_score >= 2 else RetrievalStrategy.HYBRID
        else:
            strategy = RetrievalStrategy.HYBRID
        return QueryIntent(
            strategy=strategy,
            symbols=_extract_symbol_candidates(question),
            reasoning="Heuristic intent classification.",
            query_type="general",
        )


def _extract_symbol_candidates(question: str) -> list[str]:
    candidates: list[str] = []
    for match in re.finditer(r"\b([A-Z][A-Za-z0-9_]*(?:Service|Controller|Handler|Router|Model|View|API)?)\b", question):
        candidates.append(match.group(1))
    for match in re.finditer(r"`([A-Za-z_][A-Za-z0-9_.]*)`", question):
        candidates.append(match.group(1))
    for match in re.finditer(r"\b([a-z_][a-z0-9_]*(?:_[a-z0-9_]+)+)\b", question):
        candidates.append(match.group(1))
    seen: set[str] = set()
    unique: list[str] = []
    for item in candidates:
        if item not in seen:
            seen.add(item)
            unique.append(item)
    return unique[:8]
