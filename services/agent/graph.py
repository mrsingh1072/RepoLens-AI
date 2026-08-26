"""LangGraph workflow for the AI Software Engineer agent."""

from __future__ import annotations

import json
import logging
import operator
import re
from dataclasses import asdict
from typing import Annotated, Any, TypedDict

from langgraph.graph import END, START, StateGraph

from services.agent.models import PlanStep, ToolExecutionResult
from services.agent.synthesis import synthesize_answer
from services.agent.tools import AgentToolContext, run_tool
from services.llm.base import LLMProvider
from services.retrieval.models import CodeCitation

logger = logging.getLogger(__name__)

TOOL_NAMES = (
    "search_code",
    "search_graph",
    "analyze_dependency",
    "generate_architecture",
    "explain_function",
    "trace_request_flow",
    "find_bug_patterns",
)


class AgentState(TypedDict):
    repo_id: str
    session_id: str
    question: str
    history: list[dict[str, str]]
    plan_steps: list[dict[str, Any]]
    step_index: int
    tool_results: Annotated[list[dict[str, Any]], operator.add]
    reasoning_steps: Annotated[list[str], operator.add]
    citations: Annotated[list[dict[str, Any]], operator.add]
    final_answer: str
    confidence: float


def _heuristic_plan(question: str) -> list[PlanStep]:
    lowered = question.lower()
    steps: list[PlanStep] = []

    if any(
        k in lowered
        for k in (
            "how does this project",
            "how does the project",
            "how this project",
            "how it work",
            "what is this project",
            "what does this project",
            "project work",
            "overview",
            "how does this repo",
            "how does this app",
        )
    ):
        steps.append(PlanStep("generate_architecture", {}, "Map system architecture layers."))
        steps.append(PlanStep("trace_request_flow", {}, "Trace main API request flows."))
        steps.append(
            PlanStep("search_code", {"query": "main application entry point startup"}, "Find entry points."),
        )

    if any(k in lowered for k in ("architecture", "layer", "structure")):
        steps.append(PlanStep("generate_architecture", {}, "Map repository architecture layers."))
    if any(k in lowered for k in ("call chain", "request flow", "endpoint", "route", "api")):
        steps.append(PlanStep("trace_request_flow", {"route": question}, "Trace HTTP request flow."))
    if any(k in lowered for k in ("depend", "import", "uses")):
        symbol = _extract_symbol(question)
        if symbol:
            steps.append(PlanStep("analyze_dependency", {"symbol": symbol}, "Analyze symbol dependencies."))
    if any(k in lowered for k in ("bug", "issue", "smell", "vulnerability", "anti-pattern")):
        steps.append(PlanStep("find_bug_patterns", {"query": question}, "Scan for bug patterns."))
    symbol = _extract_symbol(question)
    if symbol and any(k in lowered for k in ("explain", "how does", "what does")):
        steps.append(PlanStep("explain_function", {"symbol": symbol, "query": question}, "Explain symbol."))

    if not steps:
        steps.append(PlanStep("search_code", {"query": question}, "Semantic code search."))
    if len(steps) < 2:
        steps.insert(0, PlanStep("search_graph", {"query": question}, "Graph symbol search."))
    elif "search_code" not in {s.tool for s in steps}:
        steps.append(PlanStep("search_code", {"query": question}, "Semantic code search."))
    return steps[:6]


def _extract_symbol(question: str) -> str:
    for match in re.finditer(r"\b([A-Z][A-Za-z0-9_]*(?:Service|Controller|Handler|Router|Model)?)\b", question):
        return match.group(1)
    for match in re.finditer(r"`([A-Za-z_][A-Za-z0-9_.]*)`", question):
        return match.group(1)
    return ""


def _parse_plan(raw: str, question: str) -> list[PlanStep]:
    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return _heuristic_plan(question)

    steps_raw = data.get("steps") if isinstance(data, dict) else data
    if not isinstance(steps_raw, list):
        return _heuristic_plan(question)

    steps: list[PlanStep] = []
    for item in steps_raw[:6]:
        if not isinstance(item, dict):
            continue
        tool = str(item.get("tool", "")).strip()
        if tool not in TOOL_NAMES:
            continue
        inputs = item.get("inputs") if isinstance(item.get("inputs"), dict) else {}
        steps.append(
            PlanStep(
                tool=tool,
                inputs={str(k): str(v) for k, v in inputs.items()},
                rationale=str(item.get("rationale") or ""),
            ),
        )
    return steps or _heuristic_plan(question)


def build_agent_graph(ctx: AgentToolContext, llm: LLMProvider | None):
    """Compile the plan → execute → synthesize LangGraph."""

    def plan_node(state: AgentState) -> dict[str, Any]:
        question = state["question"]
        history_text = "\n".join(
            f"{m['role']}: {m['content'][:200]}" for m in state.get("history", [])[-6:]
        )
        reasoning = "Heuristic multi-step plan."
        if llm is not None:
            prompt = f"""You are an AI Software Engineer planning repository analysis.

Repository: {state.get("repo_id", "")}
Question: {question}
Recent conversation:
{history_text or '(none)'}

Available tools: {', '.join(TOOL_NAMES)}

Return JSON only:
{{
  "reasoning": "why these tools",
  "steps": [
    {{"tool": "search_code", "inputs": {{"query": "..."}}, "rationale": "..."}}
  ]
}}

Rules:
- Plan at least 2 tools unless the question is extremely narrow.
- For project overview / "how does this work" questions use generate_architecture, trace_request_flow, and search_code.
- Prefer multi-step investigation before answering."""
            try:
                raw = llm.complete(prompt, system="Output JSON only.", temperature=0.1)
                steps = _parse_plan(raw, question)
                cleaned = raw.strip()
                if cleaned.startswith("```"):
                    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
                    cleaned = re.sub(r"\s*```$", "", cleaned)
                reasoning = json.loads(cleaned).get("reasoning", "LLM plan created.")
            except Exception:
                logger.warning("Agent plan LLM failed; using heuristics.", exc_info=True)
                steps = _heuristic_plan(question)
        else:
            steps = _heuristic_plan(question)

        return {
            "plan_steps": [asdict(step) for step in steps],
            "step_index": 0,
            "reasoning_steps": [f"Plan: {reasoning}", *[f"Step: {s.tool} — {s.rationale}" for s in steps]],
        }

    def execute_node(state: AgentState) -> dict[str, Any]:
        steps = state.get("plan_steps") or []
        index = state.get("step_index", 0)
        if index >= len(steps):
            return {}

        step = steps[index]
        tool = step.get("tool", "")
        inputs = step.get("inputs") or {}
        result = run_tool(ctx, tool, inputs)
        payload = _tool_result_to_dict(result)
        return {
            "tool_results": [payload],
            "citations": [_citation_to_dict(c) for c in result.citations],
            "reasoning_steps": [f"Executed {tool}: {result.summary}"],
            "step_index": index + 1,
        }

    def route_after_execute(state: AgentState) -> str:
        steps = state.get("plan_steps") or []
        if state.get("step_index", 0) < len(steps):
            return "execute"
        return "synthesize"

    def synthesize_node(state: AgentState) -> dict[str, Any]:
        question = state["question"]
        repo_id = state.get("repo_id", "")
        tool_results = state.get("tool_results") or []
        citations = state.get("citations") or []

        answer, confidence, reasoning = synthesize_answer(
            repo_id=repo_id,
            question=question,
            tool_results=tool_results,
            citations=citations,
            llm=llm,
        )

        return {
            "final_answer": answer,
            "confidence": confidence,
            "reasoning_steps": [f"Synthesis: {reasoning}"],
        }

    graph = StateGraph(AgentState)
    graph.add_node("plan", plan_node)
    graph.add_node("execute", execute_node)
    graph.add_node("synthesize", synthesize_node)
    graph.add_edge(START, "plan")
    graph.add_edge("plan", "execute")
    graph.add_conditional_edges("execute", route_after_execute, {"execute": "execute", "synthesize": "synthesize"})
    graph.add_edge("synthesize", END)
    return graph.compile()


def _tool_result_to_dict(result: ToolExecutionResult) -> dict[str, Any]:
    return {
        "tool": result.tool,
        "found": result.found,
        "summary": result.summary,
        "data": result.data,
    }


def _citation_to_dict(citation: CodeCitation) -> dict[str, Any]:
    return {
        "file_path": citation.file_path,
        "function_name": citation.function_name,
        "class_name": citation.class_name,
        "start_line": citation.start_line,
        "end_line": citation.end_line,
        "snippet": citation.snippet,
        "source": citation.source,
        "score": citation.score,
    }


def dict_to_citation(data: dict[str, Any]) -> CodeCitation:
    return CodeCitation(
        file_path=str(data.get("file_path") or ""),
        function_name=data.get("function_name"),
        class_name=data.get("class_name"),
        start_line=int(data.get("start_line") or 1),
        end_line=int(data.get("end_line") or 1),
        snippet=str(data.get("snippet") or ""),
        source=str(data.get("source") or "agent"),
        score=float(data.get("score") or 0.0),
    )
