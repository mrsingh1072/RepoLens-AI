"""Cypher query engine for code graph analysis."""

from __future__ import annotations

from services.graph.models import ArchitectureLayer, CallChainResult, DependencyResult
from services.graph.service import GraphService


class GraphQueryEngine:
    """Run optimized, indexed Cypher queries against the code graph."""

    def __init__(self, graph: GraphService) -> None:
        self._graph = graph

    def find_dependencies(
        self,
        repo_id: str,
        *,
        symbol: str | None = None,
        node_id: str | None = None,
        max_depth: int = 3,
    ) -> list[DependencyResult]:
        """Return symbols reachable via CALLS, IMPORTS, EXTENDS, or IMPLEMENTS."""
        if not node_id and symbol:
            node_id = self._resolve_symbol_id(repo_id, symbol)
        if not node_id:
            return []

        depth = max(1, min(max_depth, 5))
        rows = self._graph.run(
            f"""
            MATCH (start {{id: $node_id, repo_id: $repo_id}})
            CALL {{
                WITH start
                MATCH path = (start)-[r:CALLS|IMPORTS|EXTENDS|IMPLEMENTS*1..{depth}]->(dep)
                WHERE dep.repo_id = $repo_id OR dep:ExternalLibrary
                RETURN dep, relationships(path) AS rels, length(path) AS depth
            }}
            RETURN DISTINCT dep.id AS id,
                   head(labels(dep)) AS label,
                   dep.name AS name,
                   dep.file_path AS file_path,
                   head([rel IN rels | type(rel)]) AS relationship,
                   depth
            ORDER BY depth, name
            LIMIT 100
            """,
            {"repo_id": repo_id, "node_id": node_id},
        )
        return [
            DependencyResult(
                id=row["id"],
                label=row.get("label") or "",
                name=row.get("name") or "",
                relationship=row.get("relationship") or "",
                depth=int(row.get("depth") or 0),
                file_path=row.get("file_path"),
            )
            for row in rows
        ]

    def trace_call_chain(
        self,
        repo_id: str,
        *,
        symbol: str | None = None,
        node_id: str | None = None,
        max_depth: int = 8,
    ) -> list[CallChainResult]:
        """Trace outgoing CALLS paths from a starting symbol."""
        if not node_id and symbol:
            node_id = self._resolve_symbol_id(repo_id, symbol)
        if not node_id:
            return []

        depth = max(1, min(max_depth, 12))
        rows = self._graph.run(
            f"""
            MATCH (start {{id: $node_id, repo_id: $repo_id}})
            MATCH path = (start)-[:CALLS*1..{depth}]->(target)
            WHERE all(n IN nodes(path) WHERE n.repo_id = $repo_id OR n = start)
            RETURN [n IN nodes(path) | {{
                id: n.id,
                name: coalesce(n.name, n.route, n.id),
                label: head(labels(n)),
                file_path: n.file_path
            }}] AS nodes,
            length(path) AS depth
            ORDER BY depth DESC
            LIMIT 25
            """,
            {"repo_id": repo_id, "node_id": node_id},
        )
        return [
            CallChainResult(path=row["nodes"], depth=int(row["depth"]))
            for row in rows
        ]

    def detect_architecture_layers(self, repo_id: str) -> list[ArchitectureLayer]:
        """Classify files into architecture layers using path heuristics."""
        rows = self._graph.run(
            """
            MATCH (repo:Repository {repo_id: $repo_id})-[:DEFINES]->(file:File)
            OPTIONAL MATCH (file)-[:DEFINES]->(symbol)
            WHERE symbol:Function OR symbol:Method OR symbol:Class
            WITH file,
                 CASE
                   WHEN toLower(file.path) CONTAINS 'route'
                     OR toLower(file.path) CONTAINS 'controller'
                     OR toLower(file.path) CONTAINS 'handler'
                     OR toLower(file.path) CONTAINS 'api/'
                     THEN 'presentation'
                   WHEN toLower(file.path) CONTAINS 'service'
                     OR toLower(file.path) CONTAINS 'usecase'
                     OR toLower(file.path) CONTAINS 'domain'
                     THEN 'business'
                   WHEN toLower(file.path) CONTAINS 'model'
                     OR toLower(file.path) CONTAINS 'repository'
                     OR toLower(file.path) CONTAINS 'db'
                     OR toLower(file.path) CONTAINS 'schema'
                     OR toLower(file.path) CONTAINS 'migration'
                     THEN 'data'
                   WHEN toLower(file.path) CONTAINS 'util'
                     OR toLower(file.path) CONTAINS 'helper'
                     OR toLower(file.path) CONTAINS 'config'
                     THEN 'infrastructure'
                   ELSE 'other'
                 END AS layer,
                 count(symbol) AS symbol_count
            RETURN layer,
                   count(DISTINCT file) AS file_count,
                   sum(symbol_count) AS symbol_count,
                   collect(DISTINCT file.path)[..5] AS sample_files
            ORDER BY file_count DESC
            """,
            {"repo_id": repo_id},
        )
        return [
            ArchitectureLayer(
                layer=row["layer"],
                file_count=int(row["file_count"]),
                symbol_count=int(row["symbol_count"] or 0),
                sample_files=list(row.get("sample_files") or []),
            )
            for row in rows
        ]

    def cross_layer_calls(self, repo_id: str) -> list[dict[str, str | int]]:
        """Find CALLS edges that cross architecture layers."""
        return self._graph.run(
            """
            MATCH (repo:Repository {repo_id: $repo_id})-[:DEFINES]->(source_file:File)
            MATCH (source_file)-[:DEFINES]->(source)
            WHERE source:Function OR source:Method
            MATCH (source)-[:CALLS]->(target)
            MATCH (target)<-[:DEFINES]-(target_file:File)
            WHERE target_file.repo_id = $repo_id
            WITH source, target, source_file, target_file,
                 CASE
                   WHEN toLower(source_file.path) CONTAINS 'route'
                     OR toLower(source_file.path) CONTAINS 'controller'
                     THEN 'presentation'
                   WHEN toLower(source_file.path) CONTAINS 'service'
                     THEN 'business'
                   WHEN toLower(source_file.path) CONTAINS 'model'
                     OR toLower(source_file.path) CONTAINS 'db'
                     THEN 'data'
                   ELSE 'other'
                 END AS source_layer,
                 CASE
                   WHEN toLower(target_file.path) CONTAINS 'route'
                     OR toLower(target_file.path) CONTAINS 'controller'
                     THEN 'presentation'
                   WHEN toLower(target_file.path) CONTAINS 'service'
                     THEN 'business'
                   WHEN toLower(target_file.path) CONTAINS 'model'
                     OR toLower(target_file.path) CONTAINS 'db'
                     THEN 'data'
                   ELSE 'other'
                 END AS target_layer
            WHERE source_layer <> target_layer
            RETURN source.name AS source,
                   source_layer,
                   target.name AS target,
                   target_layer,
                   source_file.path AS source_file,
                   target_file.path AS target_file
            LIMIT 50
            """,
            {"repo_id": repo_id},
        )

    def repository_stats(self, repo_id: str) -> dict[str, int]:
        """Return node counts grouped by label for a repository."""
        rows = self._graph.run(
            """
            MATCH (n {repo_id: $repo_id})
            RETURN head(labels(n)) AS label, count(n) AS count
            ORDER BY count DESC
            """,
            {"repo_id": repo_id},
        )
        return {row["label"]: int(row["count"]) for row in rows}

    def _resolve_symbol_id(self, repo_id: str, symbol: str) -> str | None:
        rows = self._graph.run(
            """
            MATCH (n {repo_id: $repo_id})
            WHERE n.name = $symbol
               OR n.qualified_name = $symbol
               OR n.id ENDS WITH $suffix
            RETURN n.id AS id
            LIMIT 1
            """,
            {"repo_id": repo_id, "symbol": symbol, "suffix": f"::{symbol}"},
        )
        return rows[0]["id"] if rows else None

    def search_symbols(self, repo_id: str, query: str, *, limit: int = 10) -> list[dict[str, str]]:
        """Find symbols whose names match terms in ``query`` (indexed lookup)."""
        terms = [t.strip("`'\".,?") for t in query.split() if len(t.strip("`'\".,?")) > 2]
        if not terms:
            terms = [query.strip()[:64]]

        rows = self._graph.run(
            """
            UNWIND $terms AS term
            MATCH (n {repo_id: $repo_id})
            WHERE (n:Function OR n:Method OR n:Class OR n:ApiEndpoint)
              AND toLower(n.name) CONTAINS toLower(term)
            RETURN DISTINCT n.id AS id,
                   head(labels(n)) AS label,
                   n.name AS name,
                   coalesce(n.file_path, '') AS file_path,
                   coalesce(n.qualified_name, n.name) AS qualified_name
            LIMIT $limit
            """,
            {"repo_id": repo_id, "terms": terms[:6], "limit": limit},
        )
        return [
            {
                "id": row["id"],
                "label": row.get("label") or "",
                "name": row.get("name") or "",
                "file_path": row.get("file_path") or "",
                "qualified_name": row.get("qualified_name") or row.get("name") or "",
            }
            for row in rows
        ]

    def list_api_endpoints(self, repo_id: str, *, limit: int = 50) -> list[dict[str, str]]:
        """Return API route nodes for a repository."""
        rows = self._graph.run(
            """
            MATCH (e:ApiEndpoint {repo_id: $repo_id})
            RETURN e.route AS route,
                   e.method AS method,
                   e.handler AS handler,
                   coalesce(e.file_path, '') AS file_path
            ORDER BY e.route
            LIMIT $limit
            """,
            {"repo_id": repo_id, "limit": limit},
        )
        return [
            {
                "route": row.get("route") or "",
                "method": row.get("method") or "",
                "handler": row.get("handler") or "",
                "file_path": row.get("file_path") or "",
            }
            for row in rows
        ]

    def list_database_tables(self, repo_id: str, *, limit: int = 30) -> list[dict[str, str]]:
        """Return database table nodes for a repository."""
        rows = self._graph.run(
            """
            MATCH (t:DatabaseTable {repo_id: $repo_id})
            RETURN t.name AS name,
                   coalesce(t.file_path, '') AS file_path
            ORDER BY t.name
            LIMIT $limit
            """,
            {"repo_id": repo_id, "limit": limit},
        )
        return [
            {
                "name": row.get("name") or "",
                "file_path": row.get("file_path") or "",
            }
            for row in rows
        ]

    def get_import_graph(self, repo_id: str, *, limit: int = 100) -> dict[str, list[dict[str, str]]]:
        """Return file-level import nodes and edges for dependency visualization."""
        rows = self._graph.run(
            """
            MATCH (source:File {repo_id: $repo_id})-[r:IMPORTS]->(target)
            RETURN source.path AS source_path,
                   coalesce(target.path, target.name, target.module, target.id) AS target_path,
                   head(labels(target)) AS target_label
            LIMIT $limit
            """,
            {"repo_id": repo_id, "limit": limit},
        )
        nodes: dict[str, dict[str, str]] = {}
        edges: list[dict[str, str]] = []

        def _group(path: str, label: str = "File") -> str:
            lowered = path.lower()
            if label == "ExternalLibrary":
                return "external"
            if any(x in lowered for x in ("route", "controller", "api/", "handler")):
                return "api"
            if "service" in lowered:
                return "service"
            if any(x in lowered for x in ("util", "helper", "config")):
                return "util"
            return "core"

        for row in rows:
            src = row.get("source_path") or ""
            tgt = row.get("target_path") or ""
            tgt_label = row.get("target_label") or "File"
            if not src or not tgt:
                continue
            src_id = f"file:{src}"
            tgt_id = f"{'lib' if tgt_label == 'ExternalLibrary' else 'file'}:{tgt}"
            nodes[src_id] = {"id": src_id, "path": src, "label": _basename(src), "group": _group(src)}
            nodes[tgt_id] = {
                "id": tgt_id,
                "path": tgt,
                "label": _basename(tgt),
                "group": _group(tgt, tgt_label),
            }
            edges.append({"source": src_id, "target": tgt_id, "label": "imports"})

        return {"nodes": list(nodes.values()), "edges": edges}

    def get_class_structure(self, repo_id: str, *, limit: int = 30) -> dict[str, list[dict]]:
        """Return class nodes, methods, and inheritance relationships."""
        class_rows = self._graph.run(
            """
            MATCH (c:Class {repo_id: $repo_id})
            OPTIONAL MATCH (c)-[:DEFINES]->(m:Method)
            RETURN c.name AS name,
                   coalesce(c.file_path, '') AS file_path,
                   collect(DISTINCT m.name)[..8] AS methods
            ORDER BY c.name
            LIMIT $limit
            """,
            {"repo_id": repo_id, "limit": limit},
        )
        rel_rows = self._graph.run(
            """
            MATCH (c:Class {repo_id: $repo_id})-[r:EXTENDS|IMPLEMENTS]->(parent)
            RETURN c.name AS source,
                   parent.name AS target,
                   type(r) AS type
            LIMIT $limit
            """,
            {"repo_id": repo_id, "limit": limit * 2},
        )
        return {
            "classes": [
                {
                    "name": row.get("name") or "",
                    "file_path": row.get("file_path") or "",
                    "methods": list(row.get("methods") or []),
                }
                for row in class_rows
            ],
            "relationships": [
                {
                    "source": row.get("source") or "",
                    "target": row.get("target") or "",
                    "type": row.get("type") or "",
                }
                for row in rel_rows
            ],
        }


def _basename(path: str) -> str:
    return path.replace("\\", "/").rsplit("/", 1)[-1] if path else path
