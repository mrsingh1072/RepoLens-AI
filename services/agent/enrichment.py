"""Enrich agent responses with references and follow-up suggestions."""

from __future__ import annotations

import re
from typing import Any

from services.retrieval.models import CodeCitation


def extract_file_references(citations: list[CodeCitation]) -> list[str]:
    paths = {c.file_path for c in citations if c.file_path}
    return sorted(paths)


def extract_function_references(citations: list[CodeCitation]) -> list[str]:
    symbols: set[str] = set()
    for citation in citations:
        if citation.function_name:
            symbols.add(citation.function_name)
        if citation.class_name:
            symbols.add(citation.class_name)
    return sorted(symbols)


def build_reasoning_summary(reasoning_steps: list[str]) -> str:
    if not reasoning_steps:
        return "No reasoning steps recorded."
    for step in reversed(reasoning_steps):
        if step.startswith("Synthesis:"):
            return step.removeprefix("Synthesis:").strip() or step
    return reasoning_steps[-1]


def generate_follow_up_suggestions(
    question: str,
    *,
    repo_id: str,
    file_references: list[str],
    function_references: list[str],
    citations: list[CodeCitation],
) -> list[str]:
    suggestions: list[str] = []
    seen: set[str] = set()

    def add(text: str) -> None:
        normalized = text.strip()
        if not normalized or normalized.lower() == question.strip().lower():
            return
        key = normalized.lower()
        if key in seen:
            return
        seen.add(key)
        suggestions.append(normalized)

    top_file = file_references[0] if file_references else None
    top_fn = function_references[0] if function_references else None

    if top_fn and top_file:
        add(f"How does `{top_fn}` in `{top_file}` work?")
        add(f"What calls `{top_fn}`?")
    elif top_file:
        add(f"What is implemented in `{top_file}`?")
    elif top_fn:
        add(f"Explain the `{top_fn}` function in more detail.")

    if "architecture" not in question.lower():
        add("What is the overall architecture of this repository?")
    if "endpoint" not in question.lower() and "api" not in question.lower():
        add("What are the main API endpoints?")
    if "depend" not in question.lower():
        add(f"What are the key dependencies in `{repo_id}`?")

    for citation in citations[:2]:
        if citation.function_name and citation.file_path:
            add(f"Show the implementation of `{citation.function_name}` in `{citation.file_path}`.")

    add("What files should I read next to understand this area?")
    return suggestions[:5]


def append_reference_footer(
    answer: str,
    *,
    file_references: list[str],
    function_references: list[str],
) -> str:
    """Ensure markdown answer mentions file and function references."""
    body = answer.strip()
    if not body:
        return body

    sections: list[str] = [body]
    if file_references and not any(path in body for path in file_references[:3]):
        files = ", ".join(f"`{path}`" for path in file_references[:6])
        sections.append(f"\n\n**Files referenced:** {files}")
    if function_references and not any(sym in body for sym in function_references[:3]):
        functions = ", ".join(f"`{name}`" for name in function_references[:6])
        sections.append(f"\n\n**Functions referenced:** {functions}")
    return "".join(sections)


def enrich_agent_payload(
    *,
    answer: str,
    citations: list[CodeCitation],
    reasoning_steps: list[str],
    question: str,
    repo_id: str,
) -> dict[str, Any]:
    file_references = extract_file_references(citations)
    function_references = extract_function_references(citations)
    reasoning_summary = build_reasoning_summary(reasoning_steps)
    follow_up_suggestions = generate_follow_up_suggestions(
        question,
        repo_id=repo_id,
        file_references=file_references,
        function_references=function_references,
        citations=citations,
    )
    enriched_answer = append_reference_footer(
        answer,
        file_references=file_references,
        function_references=function_references,
    )
    return {
        "answer": enriched_answer,
        "file_references": file_references,
        "function_references": function_references,
        "reasoning_summary": reasoning_summary,
        "follow_up_suggestions": follow_up_suggestions,
    }
