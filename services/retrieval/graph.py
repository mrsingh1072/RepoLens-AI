"""Graph retrieval via Neo4j symbol search and traversals."""

from __future__ import annotations

import logging

from services.graph.query_engine import GraphQueryEngine
from services.retrieval.models import RetrievalHit

logger = logging.getLogger(__name__)


class GraphRetriever:
    """Retrieve structural code context from the knowledge graph."""

    def __init__(self, engine: GraphQueryEngine) -> None:
        self._engine = engine

    def search(
        self,
        repo_id: str,
        question: str,
        *,
        symbols: list[str] | None = None,
        top_k: int = 8,
    ) -> list[RetrievalHit]:
        stats = self._engine.repository_stats(repo_id)
        if not stats:
            logger.warning("No graph data for repo=%s", repo_id)
            return []

        hits: list[RetrievalHit] = []
        seen: set[str] = set()

        seed_symbols = list(symbols or [])
        for row in self._engine.search_symbols(repo_id, question, limit=top_k):
            name = row.get("qualified_name") or row.get("name")
            if name and name not in seed_symbols:
                seed_symbols.append(name)

        for symbol in seed_symbols[:6]:
            self._collect_symbol_context(repo_id, symbol, hits, seen, top_k)

        if len(hits) < top_k:
            self._collect_architecture_context(repo_id, question, hits, seen, top_k)

        hits.sort(key=lambda h: h.score, reverse=True)
        return hits[:top_k]

    def _collect_symbol_context(
        self,
        repo_id: str,
        symbol: str,
        hits: list[RetrievalHit],
        seen: set[str],
        top_k: int,
    ) -> None:
        deps = self._engine.find_dependencies(repo_id, symbol=symbol, max_depth=2)
        for dep in deps:
            key = f"{dep.id}:{dep.relationship}"
            if key in seen:
                continue
            seen.add(key)
            hits.append(
                RetrievalHit(
                    hit_id=f"graph::{dep.id}",
                    source="graph",
                    file_path=dep.file_path or "",
                    content=(
                        f"Graph dependency: {dep.name} ({dep.label}) "
                        f"via {dep.relationship} at depth {dep.depth}."
                    ),
                    score=max(0.4, 1.0 - (dep.depth * 0.15)),
                    function_name=dep.name if dep.label in {"Function", "Method"} else None,
                    class_name=dep.name if dep.label == "Class" else None,
                    symbol=dep.name,
                    graph_relationship=dep.relationship,
                ),
            )
            if len(hits) >= top_k:
                return

        chains = self._engine.trace_call_chain(repo_id, symbol=symbol, max_depth=4)
        for chain in chains[:3]:
            for node in chain.path:
                node_id = node.get("id", "")
                if not node_id or node_id in seen:
                    continue
                seen.add(node_id)
                hits.append(
                    RetrievalHit(
                        hit_id=f"graph::{node_id}",
                        source="graph",
                        file_path=node.get("file_path") or "",
                        content=(
                            f"Call chain node: {node.get('name')} ({node.get('label')}) "
                            f"in call path depth {chain.depth}."
                        ),
                        score=max(0.35, 0.9 - (chain.depth * 0.08)),
                        function_name=node.get("name") if node.get("label") == "Function" else None,
                        class_name=node.get("name") if node.get("label") == "Class" else None,
                        symbol=node.get("name"),
                        graph_relationship="CALLS",
                    ),
                )
                if len(hits) >= top_k:
                    return

    def _collect_architecture_context(
        self,
        repo_id: str,
        question: str,
        hits: list[RetrievalHit],
        seen: set[str],
        top_k: int,
    ) -> None:
        if "architect" not in question.lower() and "layer" not in question.lower():
            return
        layers = self._engine.detect_architecture_layers(repo_id)
        for layer in layers:
            key = f"layer::{layer.layer}"
            if key in seen:
                continue
            seen.add(key)
            hits.append(
                RetrievalHit(
                    hit_id=key,
                    source="graph",
                    file_path=", ".join(layer.sample_files[:3]),
                    content=(
                        f"Architecture layer '{layer.layer}': "
                        f"{layer.file_count} files, {layer.symbol_count} symbols. "
                        f"Examples: {', '.join(layer.sample_files[:3])}."
                    ),
                    score=0.45,
                    graph_relationship="ARCHITECTURE",
                ),
            )
            if len(hits) >= top_k:
                return
