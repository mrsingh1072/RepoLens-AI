"""Generate Mermaid diagrams and React-Flow-ready graph payloads from code graph data."""

from __future__ import annotations

import math
import re
from dataclasses import asdict

from services.diagrams.models import DiagramBundle, MermaidDiagrams, VisEdge, VisNode
from services.graph.query_engine import GraphQueryEngine


_SYSTEM_TIER: dict[str, tuple[str, str, float]] = {
    "frontend": ("Frontend", "frontend", 0.08),
    "presentation": ("API Layer", "backend", 0.32),
    "business": ("Services", "service", 0.52),
    "data": ("Database", "database", 0.72),
    "infrastructure": ("Infrastructure", "util", 0.92),
}


def _slug(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9_]", "_", value.strip())
    if not cleaned:
        cleaned = "node"
    if cleaned[0].isdigit():
        cleaned = f"n_{cleaned}"
    return cleaned[:48]


def _mermaid_quote(text: str) -> str:
    """Return a Mermaid-safe quoted string."""
    safe = str(text or "").replace('"', "'").replace("\n", " ").strip()
    return f'"{safe[:120]}"'


def _mermaid_label(text: str) -> str:
    """Return a bracket node label, quoted when needed."""
    safe = str(text or "").replace('"', "'").replace("\n", " ").strip()[:80]
    if re.search(r'[/\[\]():|]', safe):
        return f'["{safe}"]'
    return f"[{safe or 'node'}]"


def _mermaid_method(name: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9_]", "_", str(name or ""))
    return cleaned[:40] or "method"


def _basename(path: str) -> str:
    return path.replace("\\", "/").rsplit("/", 1)[-1] if path else path


class DiagramGenerator:
    """Build architecture and dependency visualizations from graph query data."""

    def __init__(self, engine: GraphQueryEngine) -> None:
        self._engine = engine

    def generate(self, repo_id: str) -> DiagramBundle:
        layers = self._engine.detect_architecture_layers(repo_id)
        cross_layer = self._engine.cross_layer_calls(repo_id)
        import_data = self._engine.get_import_graph(repo_id)
        class_data = self._engine.get_class_structure(repo_id)
        endpoints = self._engine.list_api_endpoints(repo_id, limit=12)
        db_tables = self._engine.list_database_tables(repo_id, limit=20)
        stats = self._engine.repository_stats(repo_id)

        system_nodes, system_edges = self._build_system_architecture(
            repo_id,
            layers,
            cross_layer,
            endpoints,
            db_tables,
        )
        dep_nodes, dep_edges = self._build_dependency_graph(import_data)

        mermaid = MermaidDiagrams(
            flowchart=self._mermaid_flowchart(layers, cross_layer, endpoints),
            sequence=self._mermaid_sequence(endpoints, repo_id),
            class_diagram=self._mermaid_class_diagram(class_data),
        )
        markdown = self._to_markdown(repo_id, mermaid, system_nodes, dep_nodes, stats)

        return DiagramBundle(
            repo_id=repo_id,
            mermaid=mermaid,
            system_architecture={
                "nodes": [asdict(n) for n in system_nodes],
                "edges": [asdict(e) for e in system_edges],
            },
            dependency_graph={
                "nodes": [asdict(n) for n in dep_nodes],
                "edges": [asdict(e) for e in dep_edges],
            },
            markdown=markdown,
            stats={
                "layers": len(layers),
                "endpoints": len(endpoints),
                "import_edges": len(import_data.get("edges", [])),
                "classes": len(class_data.get("classes", [])),
                **{f"nodes_{k}": v for k, v in stats.items()},
            },
        )

    def _build_system_architecture(
        self,
        repo_id: str,
        layers: list,
        cross_layer: list[dict],
        endpoints: list[dict],
        db_tables: list[dict],
    ) -> tuple[list[VisNode], list[VisEdge]]:
        nodes: list[VisNode] = []
        edges: list[VisEdge] = []
        tier_ids: dict[str, str] = {}

        has_frontend = any(
            "frontend" in (f or "").lower() or f.endswith((".tsx", ".jsx", ".vue"))
            for layer in layers
            for f in layer.sample_files
        )
        if has_frontend:
            tier_ids["frontend"] = "tier_frontend"
            nodes.append(
                VisNode(
                    id="tier_frontend",
                    label="Frontend",
                    kind="frontend",
                    group="frontend",
                    description="UI / client layer",
                    x=0.08,
                    y=0.5,
                ),
            )

        for layer in layers:
            tier_key = layer.layer
            if tier_key not in _SYSTEM_TIER:
                continue
            label, kind, x = _SYSTEM_TIER[tier_key]
            node_id = f"tier_{tier_key}"
            tier_ids[tier_key] = node_id
            sample = ", ".join(_basename(f) for f in layer.sample_files[:3])
            nodes.append(
                VisNode(
                    id=node_id,
                    label=label,
                    kind=kind,
                    group=tier_key,
                    description=f"{layer.file_count} files · {sample or 'no samples'}",
                    x=x,
                    y=0.5,
                ),
            )

        for i, ep in enumerate(endpoints[:6]):
            node_id = f"ep_{i}"
            nodes.append(
                VisNode(
                    id=node_id,
                    label=f"{ep.get('method', 'GET')} {ep.get('route', '/')}",
                    kind="backend",
                    group="presentation",
                    description=ep.get("handler") or "",
                    file_path=ep.get("file_path") or "",
                    x=0.28,
                    y=0.12 + i * 0.13,
                ),
            )
            if "presentation" in tier_ids:
                edges.append(
                    VisEdge(
                        id=f"ep-tier-{i}",
                        source=node_id,
                        target=tier_ids["presentation"],
                        label="handler",
                    ),
                )

        for i, table in enumerate(db_tables[:5]):
            node_id = f"db_{i}"
            nodes.append(
                VisNode(
                    id=node_id,
                    label=table.get("name") or f"Table {i}",
                    kind="database",
                    group="data",
                    file_path=table.get("file_path") or "",
                    x=0.88,
                    y=0.2 + i * 0.12,
                ),
            )
            if "data" in tier_ids:
                edges.append(
                    VisEdge(
                        id=f"db-tier-{i}",
                        source=tier_ids.get("business", tier_ids.get("data", "")),
                        target=node_id,
                        label="READS/WRITES",
                    ),
                )

        flow = [
            ("frontend", "presentation"),
            ("presentation", "business"),
            ("business", "data"),
        ]
        for src, dst in flow:
            if src in tier_ids and dst in tier_ids:
                edges.append(
                    VisEdge(
                        id=f"flow-{src}-{dst}",
                        source=tier_ids[src],
                        target=tier_ids[dst],
                        label="calls",
                        kind="flow",
                    ),
                )

        seen_edges: set[tuple[str, str]] = set()
        for i, row in enumerate(cross_layer[:12]):
            src_layer = str(row.get("source_layer") or "")
            dst_layer = str(row.get("target_layer") or "")
            src_id = tier_ids.get(src_layer)
            dst_id = tier_ids.get(dst_layer)
            if not src_id or not dst_id or src_id == dst_id:
                continue
            key = (src_id, dst_id)
            if key in seen_edges:
                continue
            seen_edges.add(key)
            edges.append(
                VisEdge(
                    id=f"cross-{i}",
                    source=src_id,
                    target=dst_id,
                    label=f"{row.get('source')} → {row.get('target')}",
                    kind="cross_layer",
                ),
            )

        if not nodes:
            stats_fallback = self._engine.repository_stats(repo_id)
            if stats_fallback:
                nodes.append(
                    VisNode(
                        id="repo_root",
                        label=repo_id,
                        kind="core",
                        group="core",
                        description=f"{sum(stats_fallback.values())} graph nodes indexed",
                        x=0.5,
                        y=0.5,
                    ),
                )

        return nodes, edges

    def _build_dependency_graph(self, import_data: dict) -> tuple[list[VisNode], list[VisEdge]]:
        raw_nodes = import_data.get("nodes") or []
        raw_edges = import_data.get("edges") or []
        if not raw_nodes:
            return [], []

        degree: dict[str, int] = {}
        for edge in raw_edges:
            degree[edge["source"]] = degree.get(edge["source"], 0) + 1
            degree[edge["target"]] = degree.get(edge["target"], 0) + 1

        ids = [n["id"] for n in raw_nodes]
        n = len(ids)
        cx, cy, radius = 0.5, 0.5, 0.38

        nodes: list[VisNode] = []
        for i, item in enumerate(raw_nodes):
            angle = (i / max(n, 1)) * 3.141592653589793 * 2 - 1.5707963267948966
            path = item.get("path") or item.get("label") or item["id"]
            group = item.get("group") or "core"
            nodes.append(
                VisNode(
                    id=item["id"],
                    label=_basename(path) or item.get("label") or item["id"],
                    kind="file",
                    group=group,
                    description=path,
                    file_path=path,
                    x=cx + radius * math.cos(angle),
                    y=cy + radius * math.sin(angle),
                ),
            )

        edges = [
            VisEdge(
                id=f"imp-{i}",
                source=e["source"],
                target=e["target"],
                label=e.get("label") or "imports",
                kind="import",
            )
            for i, e in enumerate(raw_edges)
        ]
        return nodes, edges

    def _mermaid_flowchart(
        self,
        layers: list,
        cross_layer: list[dict],
        endpoints: list[dict],
    ) -> str:
        lines = ["flowchart TB"]
        if not layers:
            lines.append('  empty["No architecture data indexed"]')
            return "\n".join(lines)

        for layer in layers:
            sid = _slug(layer.layer)
            title = f"{layer.layer.title()} layer, {layer.file_count} files"
            lines.append(f"  subgraph {sid} [{title}]")
            for j, sample in enumerate(layer.sample_files[:4]):
                fid = _slug(f"{layer.layer}_{j}")
                lines.append(f"    {fid}{_mermaid_label(_basename(sample))}")
            lines.append("  end")

        tier_order = ["presentation", "business", "data", "infrastructure"]
        present = [layer.layer for layer in layers]
        for i in range(len(tier_order) - 1):
            a, b = tier_order[i], tier_order[i + 1]
            if a in present and b in present:
                lines.append(f"  {_slug(a)} --> {_slug(b)}")

        for i, row in enumerate(cross_layer[:8]):
            src_id = f"cross_src_{i}"
            dst_id = f"cross_dst_{i}"
            src_name = str(row.get("source") or f"src{i}")
            dst_name = str(row.get("target") or f"dst{i}")
            lines.append(f"  {src_id}{_mermaid_label(src_name)}")
            lines.append(f"  {dst_id}{_mermaid_label(dst_name)}")
            lines.append(f"  {src_id} -->|calls| {dst_id}")

        for i, ep in enumerate(endpoints[:4]):
            route = ep.get("route") or "/"
            handler = ep.get("handler") or "handler"
            hid = _slug(f"handler_{handler}_{i}")
            label = f"{ep.get('method', 'GET')} {route}"
            lines.append(f"  client{_mermaid_label('Client')} -->|{_mermaid_quote(label)}| {hid}{_mermaid_label(handler)}")

        return "\n".join(lines)

    def _mermaid_sequence(self, endpoints: list[dict], repo_id: str) -> str:
        lines = ["sequenceDiagram"]
        if not endpoints:
            lines.append('  Note over Client,Repo: No API endpoints found in repository graph')
            return "\n".join(lines)

        ep = endpoints[0]
        handler = ep.get("handler") or "Handler"
        route = ep.get("route") or "/"
        method = ep.get("method") or "GET"
        handler_id = _slug(handler)
        lines.append("  participant Client")
        lines.append("  participant API")
        lines.append(f"  participant {handler_id} as {_mermaid_quote(handler)}")
        lines.append("  participant Service")
        lines.append("  participant DB")
        lines.append(f"  Client->>+API: {_mermaid_quote(f'{method} {route}')}")
        lines.append(f"  API->>+{handler_id}: {_mermaid_quote('invoke')}")
        lines.append(f"  {handler_id}->>+Service: {_mermaid_quote('business logic')}")

        chains = self._engine.trace_call_chain(repo_id, symbol=handler, max_depth=4)
        seen_participants: set[str] = {handler_id, "Client", "API", "Service", "DB"}
        for chain in chains[:2]:
            names = [n.get("name") for n in chain.path if n.get("name")]
            for j in range(len(names) - 1):
                a = _slug(str(names[j]))
                b = _slug(str(names[j + 1]))
                if a not in seen_participants:
                    lines.insert(4, f"  participant {a} as {_mermaid_quote(str(names[j]))}")
                    seen_participants.add(a)
                if b not in seen_participants:
                    lines.insert(4, f"  participant {b} as {_mermaid_quote(str(names[j + 1]))}")
                    seen_participants.add(b)
                lines.append(f"  {a}->>{b}: {_mermaid_quote('call')}")

        lines.append(f"  Service->>+DB: {_mermaid_quote('query')}")
        lines.append("  DB-->>-Service: rows")
        lines.append(f"  Service-->>-{handler_id}: result")
        lines.append(f"  {handler_id}-->>-API: response")
        lines.append("  API-->>-Client: JSON")
        return "\n".join(lines)

    def _mermaid_class_diagram(self, class_data: dict) -> str:
        lines = ["classDiagram"]
        classes = class_data.get("classes") or []
        relations = class_data.get("relationships") or []
        if not classes:
            lines.append("  class EmptyGraph {")
            lines.append("    +no classes indexed")
            lines.append("  }")
            return "\n".join(lines)

        for cls in classes[:20]:
            name = _slug(cls.get("name") or "Class")
            lines.append(f"  class {name} {{")
            for method in (cls.get("methods") or [])[:6]:
                lines.append(f"    +{_mermaid_method(method)}()")
            lines.append("  }")

        for rel in relations[:25]:
            src = _slug(rel.get("source") or "A")
            dst = _slug(rel.get("target") or "B")
            rtype = rel.get("type") or "ASSOCIATION"
            if rtype == "EXTENDS":
                lines.append(f"  {dst} <|-- {src}")
            elif rtype == "IMPLEMENTS":
                lines.append(f"  {dst} <|.. {src}")
            else:
                lines.append(f"  {src} --> {dst}")

        return "\n".join(lines)

    def _to_markdown(
        self,
        repo_id: str,
        mermaid: MermaidDiagrams,
        system_nodes: list[VisNode],
        dep_nodes: list[VisNode],
        stats: dict[str, int],
    ) -> str:
        total_nodes = len(system_nodes) + len(dep_nodes)
        return f"""# Architecture Diagrams — `{repo_id}`

Auto-generated from the repository knowledge graph ({sum(stats.values())} indexed nodes).

## System overview

Frontend → API → Services → Database

| Component | Count |
|-----------|-------|
| System nodes | {len(system_nodes)} |
| Dependency nodes | {len(dep_nodes)} |
| Graph labels | {", ".join(f"{k}: {v}" for k, v in list(stats.items())[:6])} |

## Flowchart

```mermaid
{mermaid.flowchart}
```

## Sequence diagram

```mermaid
{mermaid.sequence}
```

## Class diagram

```mermaid
{mermaid.class_diagram}
```

---
*Generated by GitHub Codebase RAG System*
"""
