"""Compute repository analytics from parse artifacts."""

from __future__ import annotations

import hashlib
import re
from collections import defaultdict
from typing import Any

from services.analytics.models import (
    DependencyGraph,
    DuplicateCluster,
    HeatmapCell,
    RepositoryAnalytics,
    SymbolRef,
)
_COMPLEXITY_SCORE = {"low": 3, "medium": 8, "high": 15}
_ENTRY_HINTS = frozenset({"main", "__init__", "create_app", "handler", "app", "run", "setup", "configure"})
_SKIP_DEAD = frozenset({"__init__", "__str__", "__repr__", "__eq__", "__hash__"})


class AnalyticsComputer:
    """Aggregate code metrics from persisted parse JSON."""

    def compute(self, parse_data: dict[str, Any]) -> RepositoryAnalytics:
        files = parse_data.get("files") or []
        repo_id = str(parse_data.get("repo_id") or "")
        if not repo_id:
            owner = parse_data.get("owner") or ""
            name = parse_data.get("name") or ""
            if owner and name:
                repo_id = f"{owner}/{name}"
        job_id = str(parse_data.get("job_id") or "")

        symbols = self._collect_symbols(files)
        function_count = sum(1 for s in symbols if s.kind in {"function", "method"})
        class_count = sum(len(f.get("classes") or []) for f in files)

        language_distribution = self._language_distribution(files)
        complexity_distribution = self._complexity_distribution(files)
        heatmap = self._build_heatmap(files)
        most_complex_file = self._most_complex_file(files)
        largest_function = self._largest_symbol(symbols)

        import_graph = self._build_import_graph(files)
        dependency_depth = self._max_import_depth(import_graph)
        dependency_graph = self._to_vis_graph(import_graph, limit=60)

        duplicate_clusters = self._find_duplicates(symbols)
        duplicate_estimate = sum(c.count for c in duplicate_clusters)

        dead_symbols = self._estimate_dead_code(files, symbols)
        dead_code_estimate = len(dead_symbols)

        summary = parse_data.get("summary") if isinstance(parse_data.get("summary"), dict) else {}

        return RepositoryAnalytics(
            repo_id=repo_id,
            job_id=job_id,
            file_count=len(files),
            function_count=function_count,
            class_count=class_count,
            dependency_depth=dependency_depth,
            most_complex_file=most_complex_file,
            largest_function=largest_function,
            duplicate_clusters=duplicate_clusters[:12],
            duplicate_estimate=duplicate_estimate,
            dead_code_symbols=dead_symbols[:20],
            dead_code_estimate=dead_code_estimate,
            language_distribution=language_distribution,
            complexity_distribution=complexity_distribution,
            heatmap=heatmap,
            dependency_graph=dependency_graph,
            summary={
                "symbol_count": summary.get("symbol_count"),
                "api_endpoint_count": summary.get("api_endpoint_count"),
                "chunk_count": summary.get("chunk_count"),
            },
        )

    def _collect_symbols(self, files: list[dict[str, Any]]) -> list[SymbolRef]:
        symbols: list[SymbolRef] = []
        for file_data in files:
            path = str(file_data.get("file") or "")
            meta = file_data.get("metadata") or {}
            file_complexity = _COMPLEXITY_SCORE.get(str(meta.get("complexity") or "low"), 3)

            for fn in file_data.get("functions") or []:
                start = int(fn.get("start_line") or 1)
                end = int(fn.get("end_line") or start)
                symbols.append(
                    SymbolRef(
                        name=str(fn.get("name") or ""),
                        file_path=path,
                        start_line=start,
                        end_line=end,
                        kind="function",
                        lines=max(1, end - start + 1),
                        complexity_score=file_complexity,
                    ),
                )

            for cls in file_data.get("classes") or []:
                for method in cls.get("methods") or []:
                    start = int(method.get("start_line") or 1)
                    end = int(method.get("end_line") or start)
                    symbols.append(
                        SymbolRef(
                            name=str(method.get("name") or ""),
                            file_path=path,
                            start_line=start,
                            end_line=end,
                            kind="method",
                            lines=max(1, end - start + 1),
                            complexity_score=file_complexity,
                        ),
                    )
        return symbols

    def _language_distribution(self, files: list[dict[str, Any]]) -> list[dict[str, Any]]:
        by_lang: dict[str, dict[str, int]] = defaultdict(lambda: {"files": 0, "lines": 0})
        total_lines = 0
        for file_data in files:
            lang = str(file_data.get("language") or "unknown")
            lines = int((file_data.get("metadata") or {}).get("lines") or 0)
            by_lang[lang]["files"] += 1
            by_lang[lang]["lines"] += lines
            total_lines += lines

        result = []
        for lang, stats in sorted(by_lang.items(), key=lambda item: item[1]["lines"], reverse=True):
            pct = round((stats["lines"] / total_lines) * 100, 1) if total_lines else 0.0
            result.append(
                {
                    "language": lang,
                    "files": stats["files"],
                    "lines": stats["lines"],
                    "percentage": pct,
                },
            )
        return result

    def _complexity_distribution(self, files: list[dict[str, Any]]) -> list[dict[str, Any]]:
        counts = {"low": 0, "medium": 0, "high": 0}
        for file_data in files:
            label = str((file_data.get("metadata") or {}).get("complexity") or "low")
            counts[label if label in counts else "low"] += 1
        return [{"level": level, "count": counts[level]} for level in ("low", "medium", "high")]

    def _build_heatmap(self, files: list[dict[str, Any]]) -> list[HeatmapCell]:
        cells: list[HeatmapCell] = []
        for file_data in files:
            path = str(file_data.get("file") or "")
            meta = file_data.get("metadata") or {}
            label = str(meta.get("complexity") or "low")
            lines = int(meta.get("lines") or 0)
            symbol_count = int(meta.get("symbol_count") or 0)
            directory = path.rsplit("/", 1)[0] if "/" in path else "."
            cells.append(
                HeatmapCell(
                    path=path,
                    directory=directory,
                    language=str(file_data.get("language") or "unknown"),
                    lines=lines,
                    complexity_score=_COMPLEXITY_SCORE.get(label, 3),
                    symbol_count=symbol_count,
                    complexity_label=label,
                ),
            )
        cells.sort(key=lambda c: c.complexity_score * c.lines, reverse=True)
        return cells[:80]

    def _most_complex_file(self, files: list[dict[str, Any]]) -> SymbolRef | None:
        best: SymbolRef | None = None
        best_score = -1
        for file_data in files:
            path = str(file_data.get("file") or "")
            meta = file_data.get("metadata") or {}
            label = str(meta.get("complexity") or "low")
            score = _COMPLEXITY_SCORE.get(label, 3)
            lines = int(meta.get("lines") or 0)
            weighted = score * max(lines, 1)
            if weighted > best_score:
                best_score = weighted
                best = SymbolRef(
                    name=path.rsplit("/", 1)[-1],
                    file_path=path,
                    start_line=1,
                    end_line=lines,
                    kind="file",
                    lines=lines,
                    complexity_score=score,
                )
        return best

    def _largest_symbol(self, symbols: list[SymbolRef]) -> SymbolRef | None:
        if not symbols:
            return None
        return max(symbols, key=lambda s: s.lines)

    def _build_import_graph(self, files: list[dict[str, Any]]) -> dict[str, set[str]]:
        file_paths = {str(f.get("file") or "") for f in files}
        graph: dict[str, set[str]] = defaultdict(set)

        for file_data in files:
            src = str(file_data.get("file") or "")
            for imp in file_data.get("imports") or []:
                if imp.get("is_external"):
                    module = str(imp.get("module") or "")
                    if module:
                        graph[src].add(f"ext:{module}")
                    continue
                for name in imp.get("names") or []:
                    target = self._resolve_internal_import(name, file_paths)
                    if target:
                        graph[src].add(target)
                module = str(imp.get("module") or "")
                if module:
                    target = self._resolve_module_path(module, file_paths)
                    if target:
                        graph[src].add(target)
        return graph

    @staticmethod
    def _resolve_internal_import(name: str, file_paths: set[str]) -> str | None:
        name = name.split(".")[-1]
        matches = [p for p in file_paths if p.endswith(f"/{name}.py") or p.endswith(f"/{name}.ts") or p.endswith(f"/{name}.tsx")]
        return matches[0] if len(matches) == 1 else None

    @staticmethod
    def _resolve_module_path(module: str, file_paths: set[str]) -> str | None:
        path_like = module.replace(".", "/")
        candidates = [p for p in file_paths if p.endswith(f"{path_like}.py") or path_like in p]
        return candidates[0] if len(candidates) == 1 else None

    def _max_import_depth(self, graph: dict[str, set[str]]) -> int:
        if not graph:
            return 0
        memo: dict[str, int] = {}

        def depth(node: str, visiting: set[str]) -> int:
            if node in memo:
                return memo[node]
            if node in visiting:
                return 1
            visiting.add(node)
            children = [c for c in graph.get(node, set()) if not c.startswith("ext:")]
            if not children:
                memo[node] = 1
            else:
                memo[node] = 1 + max(depth(child, visiting) for child in children)
            visiting.remove(node)
            return memo[node]

        return max(depth(node, set()) for node in graph) if graph else 0

    def _to_vis_graph(self, graph: dict[str, set[str]], *, limit: int) -> DependencyGraph:
        nodes: dict[str, dict[str, str]] = {}
        edges: list[dict[str, str]] = []

        def node_id(path: str) -> str:
            return hashlib.md5(path.encode()).hexdigest()[:10]

        count = 0
        for src, targets in graph.items():
            if count >= limit:
                break
            src_id = node_id(src)
            nodes[src_id] = {
                "id": src_id,
                "label": src.rsplit("/", 1)[-1],
                "path": src,
                "group": "internal",
            }
            for tgt in sorted(targets):
                if count >= limit:
                    break
                if tgt.startswith("ext:"):
                    tgt_id = node_id(tgt)
                    nodes[tgt_id] = {
                        "id": tgt_id,
                        "label": tgt.removeprefix("ext:"),
                        "path": tgt,
                        "group": "external",
                    }
                else:
                    tgt_id = node_id(tgt)
                    nodes[tgt_id] = {
                        "id": tgt_id,
                        "label": tgt.rsplit("/", 1)[-1],
                        "path": tgt,
                        "group": "internal",
                    }
                edges.append({"source": src_id, "target": tgt_id, "label": "imports"})
                count += 1

        return DependencyGraph(
            nodes=list(nodes.values()),
            edges=edges,
            max_depth=self._max_import_depth(graph),
        )

    def _fingerprint(self, symbol: SymbolRef) -> str:
        param_hint = f"{symbol.kind}:{symbol.lines}"
        normalized = re.sub(r"[^a-z0-9]+", "", symbol.name.lower())
        raw = f"{normalized}|{param_hint}"
        return hashlib.sha1(raw.encode()).hexdigest()[:12]

    def _find_duplicates(self, symbols: list[SymbolRef]) -> list[DuplicateCluster]:
        buckets: dict[str, list[SymbolRef]] = defaultdict(list)
        for symbol in symbols:
            if symbol.lines < 4:
                continue
            buckets[self._fingerprint(symbol)].append(symbol)

        clusters: list[DuplicateCluster] = []
        for fingerprint, group in buckets.items():
            if len(group) < 2:
                continue
            clusters.append(
                DuplicateCluster(
                    fingerprint=fingerprint,
                    count=len(group),
                    symbols=group[:6],
                    similarity=0.72 + min(0.25, len(group) * 0.03),
                ),
            )
        clusters.sort(key=lambda c: c.count, reverse=True)
        return clusters

    def _estimate_dead_code(self, files: list[dict[str, Any]], symbols: list[SymbolRef]) -> list[SymbolRef]:
        callees: set[str] = set()
        api_handlers: set[str] = set()

        for file_data in files:
            for endpoint in file_data.get("api_endpoints") or []:
                handler = str(endpoint.get("handler") or "")
                if handler:
                    api_handlers.add(handler)
            for call in file_data.get("calls") or []:
                callee = str(call.get("callee") or "")
                if callee:
                    callees.add(callee)

        dead: list[SymbolRef] = []
        for symbol in symbols:
            name = symbol.name
            if not name or name in _SKIP_DEAD:
                continue
            if name in api_handlers or name in _ENTRY_HINTS:
                continue
            if name.startswith("test_") or name.endswith("_test"):
                continue
            if name in callees:
                continue
            if symbol.kind == "method" and name.startswith("_") and not name.startswith("__"):
                continue
            dead.append(symbol)

        dead.sort(key=lambda s: s.lines, reverse=True)
        return dead
