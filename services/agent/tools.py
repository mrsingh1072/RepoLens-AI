"""Agent tools backed by vector search and Neo4j graph queries."""

from __future__ import annotations

import re
from dataclasses import asdict
from dataclasses import dataclass

from services.agent.models import NOT_FOUND, ToolExecutionResult
from services.graph.query_engine import GraphQueryEngine
from services.retrieval.graph import GraphRetriever
from services.retrieval.models import CodeCitation
from services.retrieval.vector import VectorRetriever

BUG_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("bare_except", re.compile(r"except\s*:\s*\n", re.MULTILINE)),
    ("swallowed_exception", re.compile(r"except[^:\n]+:\s*pass\b", re.MULTILINE)),
    ("todo_fixme", re.compile(r"\b(TODO|FIXME|HACK|XXX)\b", re.IGNORECASE)),
    ("hardcoded_secret", re.compile(r"(api[_-]?key|password|secret)\s*=\s*['\"][^'\"]+['\"]", re.IGNORECASE)),
    ("empty_catch", re.compile(r"catch\s*\([^)]*\)\s*\{\s*\}", re.MULTILINE)),
)


@dataclass(slots=True)
class AgentToolContext:
    repo_id: str
    vector: VectorRetriever
    graph: GraphRetriever | None
    graph_engine: GraphQueryEngine | None
    top_k: int = 8


def _citation_from_hit(hit, source: str) -> CodeCitation:
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
        source=source,
        score=round(hit.score, 3),
    )


def search_code(ctx: AgentToolContext, *, query: str) -> ToolExecutionResult:
    hits = ctx.vector.search(ctx.repo_id, query, top_k=ctx.top_k)
    if not hits:
        return ToolExecutionResult("search_code", False, NOT_FOUND)
    citations = [_citation_from_hit(h, "vector") for h in hits]
    return ToolExecutionResult(
        tool="search_code",
        found=True,
        summary=f"Found {len(hits)} semantic code matches for '{query}'.",
        data=[
            {
                "file_path": h.file_path,
                "symbol": h.symbol,
                "score": h.score,
                "preview": h.content[:300],
            }
            for h in hits
        ],
        citations=citations,
    )


def search_graph(ctx: AgentToolContext, *, query: str) -> ToolExecutionResult:
    if ctx.graph is None:
        return ToolExecutionResult("search_graph", False, NOT_FOUND)
    hits = ctx.graph.search(ctx.repo_id, query, top_k=ctx.top_k)
    if not hits:
        return ToolExecutionResult("search_graph", False, NOT_FOUND)
    citations = [_citation_from_hit(h, "graph") for h in hits]
    return ToolExecutionResult(
        tool="search_graph",
        found=True,
        summary=f"Found {len(hits)} graph nodes matching '{query}'.",
        data=[
            {
                "file_path": h.file_path,
                "symbol": h.symbol,
                "relationship": h.graph_relationship,
                "preview": h.content[:300],
            }
            for h in hits
        ],
        citations=citations,
    )


def analyze_dependency(ctx: AgentToolContext, *, symbol: str) -> ToolExecutionResult:
    if ctx.graph_engine is None:
        return ToolExecutionResult("analyze_dependency", False, NOT_FOUND)
    deps = ctx.graph_engine.find_dependencies(ctx.repo_id, symbol=symbol, max_depth=3)
    if not deps:
        return ToolExecutionResult(
            tool="analyze_dependency",
            found=False,
            summary=f"{NOT_FOUND} for symbol '{symbol}'.",
        )
    citations = [
        CodeCitation(
            file_path=d.file_path or "",
            function_name=d.name if d.label in {"Function", "Method"} else None,
            class_name=d.name if d.label == "Class" else None,
            start_line=1,
            end_line=1,
            snippet=f"{d.name} ({d.label}) via {d.relationship} depth={d.depth}",
            source="graph",
            score=max(0.3, 1.0 - d.depth * 0.15),
        )
        for d in deps[:10]
        if d.file_path
    ]
    return ToolExecutionResult(
        tool="analyze_dependency",
        found=True,
        summary=f"Found {len(deps)} dependencies for '{symbol}'.",
        data=[
            {
                "name": d.name,
                "label": d.label,
                "relationship": d.relationship,
                "depth": d.depth,
                "file_path": d.file_path,
            }
            for d in deps
        ],
        citations=citations,
    )


def generate_architecture(ctx: AgentToolContext) -> ToolExecutionResult:
    if ctx.graph_engine is None:
        return ToolExecutionResult("generate_architecture", False, NOT_FOUND)
    layers = ctx.graph_engine.detect_architecture_layers(ctx.repo_id)
    cross = ctx.graph_engine.cross_layer_calls(ctx.repo_id)
    if not layers:
        return ToolExecutionResult("generate_architecture", False, NOT_FOUND)
    return ToolExecutionResult(
        tool="generate_architecture",
        found=True,
        summary=f"Detected {len(layers)} architecture layers with {len(cross)} cross-layer calls.",
        data=[
            {"type": "layer", **asdict(layer)} for layer in layers
        ]
        + [{"type": "cross_layer_call", **row} for row in cross[:20]],
        citations=[],
    )


def explain_function(ctx: AgentToolContext, *, symbol: str, query: str = "") -> ToolExecutionResult:
    search_query = query or f"explain function {symbol} implementation"
    code = search_code(ctx, query=search_query)
    dep = analyze_dependency(ctx, symbol=symbol)
    combined_data = []
    citations: list[CodeCitation] = []
    if code.found:
        combined_data.extend(code.data if isinstance(code.data, list) else [])
        citations.extend(code.citations)
    if dep.found:
        combined_data.extend(dep.data if isinstance(dep.data, list) else [])
        citations.extend(dep.citations)
    if not combined_data:
        return ToolExecutionResult("explain_function", False, NOT_FOUND)
    return ToolExecutionResult(
        tool="explain_function",
        found=True,
        summary=f"Collected implementation and dependency context for '{symbol}'.",
        data=combined_data,
        citations=citations,
    )


def trace_request_flow(ctx: AgentToolContext, *, route: str = "", handler: str = "") -> ToolExecutionResult:
    if ctx.graph_engine is None:
        return ToolExecutionResult("trace_request_flow", False, NOT_FOUND)
    endpoints = ctx.graph_engine.list_api_endpoints(ctx.repo_id)
    if not endpoints:
        return ToolExecutionResult("trace_request_flow", False, NOT_FOUND)

    matched = endpoints
    if route:
        matched = [e for e in endpoints if route.lower() in e["route"].lower()]
    if handler:
        matched = [e for e in matched if handler.lower() in e["handler"].lower()]
    if not matched:
        matched = endpoints[:5]

    flow: list[dict] = []
    citations: list[CodeCitation] = []
    for ep in matched[:5]:
        flow.append(ep)
        citations.append(
            CodeCitation(
                file_path=ep.get("file_path") or "",
                function_name=ep.get("handler"),
                class_name=None,
                start_line=1,
                end_line=1,
                snippet=f"{ep.get('method')} {ep.get('route')} -> {ep.get('handler')}",
                source="graph",
                score=0.8,
            ),
        )
        chains = ctx.graph_engine.trace_call_chain(ctx.repo_id, symbol=ep.get("handler", ""), max_depth=6)
        for chain in chains[:2]:
            flow.append({"call_chain_depth": chain.depth, "path": chain.path})

    return ToolExecutionResult(
        tool="trace_request_flow",
        found=True,
        summary=f"Traced request flow for {len(matched)} endpoint(s).",
        data=flow,
        citations=citations,
    )


def find_bug_patterns(ctx: AgentToolContext, *, query: str = "error handling exception bug") -> ToolExecutionResult:
    hits = ctx.vector.search(ctx.repo_id, query, top_k=ctx.top_k)
    if not hits:
        return ToolExecutionResult("find_bug_patterns", False, NOT_FOUND)

    findings: list[dict] = []
    citations: list[CodeCitation] = []
    for hit in hits:
        for label, pattern in BUG_PATTERNS:
            if pattern.search(hit.content):
                findings.append(
                    {
                        "pattern": label,
                        "file_path": hit.file_path,
                        "symbol": hit.symbol,
                        "score": hit.score,
                    },
                )
                citations.append(_citation_from_hit(hit, "vector"))
                break

    if not findings:
        return ToolExecutionResult(
            tool="find_bug_patterns",
            found=False,
            summary=f"{NOT_FOUND} for common bug patterns in retrieved chunks.",
        )
    return ToolExecutionResult(
        tool="find_bug_patterns",
        found=True,
        summary=f"Flagged {len(findings)} potential bug pattern(s).",
        data=findings,
        citations=citations,
    )


TOOL_REGISTRY: dict[str, callable] = {
    "search_code": lambda ctx, inputs: search_code(ctx, query=inputs.get("query", "")),
    "search_graph": lambda ctx, inputs: search_graph(ctx, query=inputs.get("query", "")),
    "analyze_dependency": lambda ctx, inputs: analyze_dependency(ctx, symbol=inputs.get("symbol", "")),
    "generate_architecture": lambda ctx, inputs: generate_architecture(ctx),
    "explain_function": lambda ctx, inputs: explain_function(
        ctx,
        symbol=inputs.get("symbol", ""),
        query=inputs.get("query", ""),
    ),
    "trace_request_flow": lambda ctx, inputs: trace_request_flow(
        ctx,
        route=inputs.get("route", ""),
        handler=inputs.get("handler", ""),
    ),
    "find_bug_patterns": lambda ctx, inputs: find_bug_patterns(ctx, query=inputs.get("query", "")),
}


def run_tool(ctx: AgentToolContext, tool: str, inputs: dict[str, str]) -> ToolExecutionResult:
    runner = TOOL_REGISTRY.get(tool)
    if runner is None:
        return ToolExecutionResult(tool, False, f"Unknown tool '{tool}'.")
    return runner(ctx, inputs)
