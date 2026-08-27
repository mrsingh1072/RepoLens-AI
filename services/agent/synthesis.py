"""Answer synthesis helpers for the software engineer agent."""

from __future__ import annotations

import json
import re
from typing import Any

from services.agent.models import NOT_FOUND
from services.retrieval.answer import AnswerGenerator
from services.retrieval.models import RetrievalHit


def try_meta_answer(repo_id: str, question: str) -> tuple[str, float, str] | None:
    """Answer repository metadata questions without code search."""
    lowered = question.lower().strip()
    if "/" not in repo_id:
        return None

    owner, _, name = repo_id.partition("/")
    if not owner or not name:
        return None

    owner_patterns = (
        "owner of this repo",
        "owner of the repo",
        "who is the owner",
        "who owns this repo",
        "who owns the repo",
        "repository owner",
        "repo owner",
    )
    if any(p in lowered for p in owner_patterns):
        return (
            f"The repository owner is `{owner}` and the repository name is `{name}` "
            f"(full slug: `{repo_id}`). This is derived from the indexed repository identity, "
            f"not from searching source files.",
            0.98,
            "Repository slug metadata.",
        )

    name_patterns = (
        "what is this repo",
        "what repo is this",
        "repository name",
        "repo name",
        "what repository",
        "which repository",
    )
    if any(p in lowered for p in name_patterns):
        return (
            f"The indexed repository is `{repo_id}` (GitHub-style owner/name: `{owner}` / `{name}`).",
            0.98,
            "Repository slug metadata.",
        )

    return None


def parse_llm_json(raw: str) -> dict[str, Any]:
    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{[\s\S]*\}", text)
        if match:
            return json.loads(match.group(0))
        raise


def build_evidence_blocks(
    tool_results: list[dict[str, Any]],
    citations: list[dict[str, Any]],
) -> list[str]:
    blocks: list[str] = []

    for result in tool_results:
        if not result.get("found"):
            continue
        tool = result.get("tool", "")
        blocks.append(f"[{tool}] {result.get('summary', '')}")
        data = result.get("data") or []
        if isinstance(data, list):
            for row in data[:4]:
                if isinstance(row, dict):
                    preview = row.get("preview") or row.get("path") or row.get("name") or str(row)[:200]
                    blocks.append(f"  - {preview}")

    for citation in citations[:8]:
        path = citation.get("file_path") or ""
        symbol = citation.get("function_name") or citation.get("class_name") or ""
        snippet = (citation.get("snippet") or "").strip()
        if not path or not snippet:
            continue
        header = f"{path}" + (f" ({symbol})" if symbol else "")
        blocks.append(f"[code] {header}\n{snippet[:600]}")

    return blocks


def citations_to_hits(citations: list[dict[str, Any]]) -> list[RetrievalHit]:
    hits: list[RetrievalHit] = []
    for index, citation in enumerate(citations):
        snippet = (citation.get("snippet") or "").strip()
        if not snippet:
            continue
        hits.append(
            RetrievalHit(
                hit_id=str(index),
                source=str(citation.get("source") or "agent"),
                file_path=str(citation.get("file_path") or ""),
                content=snippet,
                score=float(citation.get("score") or 0.5),
                symbol=citation.get("function_name"),
                function_name=citation.get("function_name"),
                class_name=citation.get("class_name"),
                start_line=int(citation.get("start_line") or 1),
                end_line=int(citation.get("end_line") or 1),
            ),
        )
    return hits


def synthesize_answer(
    *,
    repo_id: str,
    question: str,
    tool_results: list[dict[str, Any]],
    citations: list[dict[str, Any]],
    llm: Any | None,
) -> tuple[str, float, str]:
    """Produce a grounded final answer from tool evidence."""
    meta = try_meta_answer(repo_id, question)
    if meta is not None:
        return meta

    found_any = any(r.get("found") for r in tool_results)
    if not found_any and not citations:
        return NOT_FOUND, 0.0, "No repository evidence collected."

    evidence = build_evidence_blocks(tool_results, citations)
    if llm is not None and evidence:
        prompt = f"""You are an AI Software Engineer answering questions about a codebase.

Repository: {repo_id}
Question: {question}

Evidence collected from repository tools (use ONLY this):
{chr(10).join(evidence[:20])}

Write a clear, helpful answer in **Markdown**. Use fenced code blocks with language tags for snippets.
Reference specific files with backticks (e.g. `backend/app/main.py`) and functions with backticks.
For "how does this project work" questions, summarize the architecture, main entry points, and data flow.

Return JSON only:
{{
  "answer": "detailed answer",
  "confidence": 0.0,
  "reasoning_summary": "brief note on evidence used"
}}

If evidence cannot answer the question, set answer to "{NOT_FOUND}" and confidence to 0."""
        try:
            raw = llm.complete(
                prompt,
                system="Ground every claim in the evidence. Never invent files or behavior.",
                temperature=0.15,
            )
            data = parse_llm_json(raw)
            answer = str(data.get("answer") or "").strip()
            confidence = float(data.get("confidence") or 0.0)
            reasoning = str(data.get("reasoning_summary") or "")
            if answer and answer != NOT_FOUND:
                return answer, min(1.0, max(0.0, confidence)), reasoning
        except Exception:
            pass

        hits = citations_to_hits(citations)
        if hits:
            try:
                answer, confidence, reasoning, _ = AnswerGenerator(llm).generate(question, hits)
                if answer.strip():
                    return answer.strip(), confidence, reasoning
            except Exception:
                pass

    return extractive_fallback(repo_id, question, tool_results, citations)


def extractive_fallback(
    repo_id: str,
    question: str,
    tool_results: list[dict[str, Any]],
    citations: list[dict[str, Any]],
) -> tuple[str, float, str]:
    """Build a readable answer from snippets when the LLM is unavailable."""
    hits = citations_to_hits(citations)
    if hits:
        answer, confidence, reasoning, _ = AnswerGenerator(None).generate(question, hits)
        if answer.strip() and "could not find" not in answer.lower():
            return answer.strip(), confidence, reasoning

    parts: list[str] = []
    for result in tool_results:
        if not result.get("found"):
            continue
        tool = str(result.get("tool", ""))
        if tool == "generate_architecture":
            layers = [row for row in (result.get("data") or []) if row.get("type") == "layer"]
            if layers:
                parts.append(
                    "Architecture layers detected: "
                    + ", ".join(f"{layer.get('layer', 'layer')} ({layer.get('file_count', 0)} files)" for layer in layers[:5]),
                )
        elif tool == "trace_request_flow":
            endpoints = [row for row in (result.get("data") or []) if row.get("route")]
            if endpoints:
                parts.append(
                    "API endpoints: "
                    + "; ".join(
                        f"{ep.get('method', 'GET')} {ep.get('route')} → {ep.get('handler', 'handler')}"
                        for ep in endpoints[:4]
                    ),
                )

    for hit in hits[:4]:
        symbol = hit.symbol or hit.function_name or "code"
        parts.append(f"`{hit.file_path}` ({symbol}): {hit.content[:280].strip()}")

    if not parts:
        return NOT_FOUND, 0.0, "Evidence was insufficient for a grounded answer."

    answer = (
        f"For repository `{repo_id}`, here is what the indexed codebase shows regarding "
        f'"{question}":\n\n'
        + "\n\n".join(f"- {part}" for part in parts)
    )
    return answer, 0.62, "Extractive synthesis from code snippets and tool outputs."
