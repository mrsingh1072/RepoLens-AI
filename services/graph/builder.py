"""Build a deduplicated code graph from Tree-sitter parse output."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from services.graph.models import GraphBuildResult, NodeLabel, RelationshipType
from services.graph.service import GraphNode, GraphRelationship
from services.parser.models import ParsedClass, ParsedFile, ParsedImport

# ORM / SQL heuristics for database table and access detection.
_TABLENAME_RE = re.compile(r"""__tablename__\s*=\s*['"]([^'"]+)['"]""")
_DB_TABLE_CLASS_RE = re.compile(
    r"class\s+(\w+)\s*\([^)]*(?:Model|Base|SQLModel|Document)[^)]*\)",
    re.MULTILINE,
)
_READ_PATTERNS = (
    re.compile(r"\.query\s*\(", re.IGNORECASE),
    re.compile(r"\bSELECT\b", re.IGNORECASE),
    re.compile(r"\.execute\s*\(", re.IGNORECASE),
    re.compile(r"\.find(?:One|Many|Unique)?\s*\(", re.IGNORECASE),
    re.compile(r"\.get\s*\(", re.IGNORECASE),
)
_WRITE_PATTERNS = (
    re.compile(r"\.add\s*\(", re.IGNORECASE),
    re.compile(r"\.delete\s*\(", re.IGNORECASE),
    re.compile(r"\.commit\s*\(", re.IGNORECASE),
    re.compile(r"\.insert\s*\(", re.IGNORECASE),
    re.compile(r"\.update\s*\(", re.IGNORECASE),
    re.compile(r"\bINSERT\b", re.IGNORECASE),
    re.compile(r"\bUPDATE\b", re.IGNORECASE),
    re.compile(r"\.save\s*\(", re.IGNORECASE),
)


@dataclass
class _SymbolIndex:
    """Maps symbol names to graph node ids for call resolution."""

    by_name: dict[str, set[str]] = field(default_factory=dict)
    by_qualified: dict[str, str] = field(default_factory=dict)
    import_aliases: dict[str, dict[str, str]] = field(default_factory=dict)


class GraphBuilder:
    """Convert parsed repository structures into graph nodes and edges."""

    def __init__(self, repo_id: str) -> None:
        self._repo_id = repo_id
        self._nodes: dict[str, GraphNode] = {}
        self._relationships: list[GraphRelationship] = []
        self._relationship_keys: set[tuple[str, str, str]] = set()
        self._index = _SymbolIndex()

    def build(self, parsed_files: list[ParsedFile], sources: dict[str, str] | None = None) -> GraphBuildResult:
        """Build a deduplicated graph for ``repo_id``."""
        sources = sources or {}
        self._add_repository()

        for parsed in parsed_files:
            self._add_file(parsed)
            self._index_import_aliases(parsed)

        for parsed in parsed_files:
            self._add_symbols(parsed, sources.get(parsed.file, ""))

        for parsed in parsed_files:
            self._add_calls(parsed)
            self._add_db_access(parsed, sources.get(parsed.file, ""))

        return GraphBuildResult(
            repo_id=self._repo_id,
            nodes=list(self._nodes.values()),
            relationships=self._relationships,
        )

    # --- Node helpers -------------------------------------------------------
    def _add_node(self, node: GraphNode) -> str:
        existing = self._nodes.get(node.id)
        if existing is not None:
            existing.properties.update(node.properties)
            return existing.id
        self._nodes[node.id] = node
        return node.id

    def _add_relationship(
        self,
        start_id: str,
        end_id: str,
        rel_type: RelationshipType | str,
        **properties: object,
    ) -> None:
        if start_id not in self._nodes or end_id not in self._nodes:
            return
        rel_name = rel_type.value if isinstance(rel_type, RelationshipType) else rel_type
        key = (start_id, end_id, rel_name)
        if key in self._relationship_keys:
            return
        self._relationship_keys.add(key)
        self._relationships.append(
            GraphRelationship(
                start_id=start_id,
                end_id=end_id,
                type=rel_name,
                properties=dict(properties),
            ),
        )

    def _register_symbol(self, node_id: str, name: str, qualified: str | None = None) -> None:
        self._index.by_name.setdefault(name, set()).add(node_id)
        if qualified:
            self._index.by_qualified[qualified] = node_id

    @staticmethod
    def _node_id(label: NodeLabel, *parts: str) -> str:
        return f"{label.value}::{'::'.join(parts)}"

    def _repo_node_id(self) -> str:
        return self._node_id(NodeLabel.REPOSITORY, self._repo_id)

    def _file_node_id(self, file_path: str) -> str:
        return self._node_id(NodeLabel.FILE, self._repo_id, file_path)

    def _class_node_id(self, file_path: str, class_name: str) -> str:
        return self._node_id(NodeLabel.CLASS, self._repo_id, file_path, class_name)

    def _function_node_id(self, file_path: str, fn_name: str) -> str:
        return self._node_id(NodeLabel.FUNCTION, self._repo_id, file_path, fn_name)

    def _method_node_id(self, file_path: str, class_name: str, method_name: str) -> str:
        return self._node_id(NodeLabel.METHOD, self._repo_id, file_path, class_name, method_name)

    def _endpoint_node_id(self, method: str, route: str) -> str:
        return self._node_id(NodeLabel.API_ENDPOINT, self._repo_id, method.upper(), route)

    def _table_node_id(self, table_name: str) -> str:
        return self._node_id(NodeLabel.DATABASE_TABLE, self._repo_id, table_name)

    def _library_node_id(self, module: str) -> str:
        return self._node_id(NodeLabel.EXTERNAL_LIBRARY, module)

    # --- Build steps --------------------------------------------------------
    def _add_repository(self) -> None:
        repo_id = self._repo_node_id()
        self._add_node(
            GraphNode(
                id=repo_id,
                label=NodeLabel.REPOSITORY.value,
                properties={"repo_id": self._repo_id, "name": self._repo_id},
            ),
        )

    def _add_file(self, parsed: ParsedFile) -> None:
        file_id = self._file_node_id(parsed.file)
        self._add_node(
            GraphNode(
                id=file_id,
                label=NodeLabel.FILE.value,
                properties={
                    "repo_id": self._repo_id,
                    "path": parsed.file,
                    "language": parsed.language,
                    "lines": parsed.metadata.lines,
                    "complexity": parsed.metadata.complexity,
                },
            ),
        )
        self._add_relationship(self._repo_node_id(), file_id, RelationshipType.DEFINES)

    def _index_import_aliases(self, parsed: ParsedFile) -> None:
        aliases: dict[str, str] = {}
        for imp in parsed.imports:
            module = imp.module
            for name in imp.names:
                aliases[name] = module
            if imp.names:
                aliases[module.rsplit(".", 1)[-1]] = module
        self._index.import_aliases[parsed.file] = aliases

    def _add_symbols(self, parsed: ParsedFile, source: str) -> None:
        file_id = self._file_node_id(parsed.file)

        for fn in parsed.functions:
            fn_id = self._function_node_id(parsed.file, fn.name)
            self._add_node(
                GraphNode(
                    id=fn_id,
                    label=NodeLabel.FUNCTION.value,
                    properties={
                        "repo_id": self._repo_id,
                        "name": fn.name,
                        "file_path": parsed.file,
                        "start_line": fn.start_line,
                        "end_line": fn.end_line,
                        "return_type": fn.return_type or "",
                    },
                ),
            )
            self._add_relationship(file_id, fn_id, RelationshipType.DEFINES)
            self._register_symbol(fn_id, fn.name, fn.name)

        for cls in parsed.classes:
            self._add_class(parsed.file, file_id, cls, source)

        for endpoint in parsed.api_endpoints:
            ep_id = self._endpoint_node_id(endpoint.method, endpoint.route)
            self._add_node(
                GraphNode(
                    id=ep_id,
                    label=NodeLabel.API_ENDPOINT.value,
                    properties={
                        "repo_id": self._repo_id,
                        "route": endpoint.route,
                        "method": endpoint.method.upper(),
                        "handler": endpoint.handler,
                        "file_path": parsed.file,
                        "start_line": endpoint.start_line,
                    },
                ),
            )
            self._add_relationship(file_id, ep_id, RelationshipType.DEFINES)
            handler_id = self._resolve_symbol(parsed.file, endpoint.handler)
            if handler_id:
                self._add_relationship(ep_id, handler_id, RelationshipType.CALLS)

        for imp in parsed.imports:
            self._add_import(parsed.file, imp)

        self._detect_database_tables(parsed, source)

    def _add_class(self, file_path: str, file_id: str, cls: ParsedClass, source: str) -> None:
        class_id = self._class_node_id(file_path, cls.name)
        self._add_node(
            GraphNode(
                id=class_id,
                label=NodeLabel.CLASS.value,
                properties={
                    "repo_id": self._repo_id,
                    "name": cls.name,
                    "file_path": file_path,
                    "start_line": cls.start_line,
                    "end_line": cls.end_line,
                },
            ),
        )
        self._add_relationship(file_id, class_id, RelationshipType.DEFINES)
        self._register_symbol(class_id, cls.name, cls.name)

        for base in cls.bases:
            base_id = self._resolve_symbol(file_path, base)
            if base_id:
                self._add_relationship(class_id, base_id, RelationshipType.EXTENDS)

        for iface in cls.implements:
            iface_id = self._resolve_symbol(file_path, iface)
            if iface_id:
                self._add_relationship(class_id, iface_id, RelationshipType.IMPLEMENTS)

        for method in cls.methods:
            method_id = self._method_node_id(file_path, cls.name, method.name)
            qualified = f"{cls.name}.{method.name}"
            self._add_node(
                GraphNode(
                    id=method_id,
                    label=NodeLabel.METHOD.value,
                    properties={
                        "repo_id": self._repo_id,
                        "name": method.name,
                        "class_name": cls.name,
                        "qualified_name": qualified,
                        "file_path": file_path,
                        "start_line": method.start_line,
                        "end_line": method.end_line,
                        "return_type": method.return_type or "",
                    },
                ),
            )
            self._add_relationship(class_id, method_id, RelationshipType.DEFINES)
            self._register_symbol(method_id, method.name, qualified)

    def _add_import(self, file_path: str, imp: ParsedImport) -> None:
        file_id = self._file_node_id(file_path)
        if imp.is_external:
            lib_id = self._library_node_id(imp.module)
            self._add_node(
                GraphNode(
                    id=lib_id,
                    label=NodeLabel.EXTERNAL_LIBRARY.value,
                    properties={"name": imp.module, "module": imp.module},
                ),
            )
            self._add_relationship(file_id, lib_id, RelationshipType.IMPORTS, line=imp.start_line)
            return

        for name in imp.names:
            target_id = self._resolve_import_target(name, imp.module)
            if target_id:
                self._add_relationship(file_id, target_id, RelationshipType.IMPORTS, symbol=name)

    def _add_calls(self, parsed: ParsedFile) -> None:
        for call in parsed.calls:
            caller_id = self._resolve_caller(parsed.file, call.caller)
            if caller_id is None:
                continue
            callee_id = self._resolve_call_target(parsed.file, call.callee, call.receiver)
            if callee_id is None:
                continue
            self._add_relationship(
                caller_id,
                callee_id,
                RelationshipType.CALLS,
                line=call.start_line,
            )

    def _add_db_access(self, parsed: ParsedFile, source: str) -> None:
        if not source:
            return
        lines = source.splitlines()
        table_ids = {
            node.properties.get("name", ""): node.id
            for node in self._nodes.values()
            if node.label == NodeLabel.DATABASE_TABLE.value
            and node.properties.get("repo_id") == self._repo_id
            and node.properties.get("file_path") == parsed.file
        }
        if not table_ids:
            return

        for fn in parsed.functions:
            body = _slice_lines(lines, fn.start_line, fn.end_line)
            fn_id = self._function_node_id(parsed.file, fn.name)
            self._link_db_patterns(fn_id, body, table_ids)

        for cls in parsed.classes:
            for method in cls.methods:
                body = _slice_lines(lines, method.start_line, method.end_line)
                method_id = self._method_node_id(parsed.file, cls.name, method.name)
                self._link_db_patterns(method_id, body, table_ids)

    def _link_db_patterns(self, symbol_id: str, body: str, table_ids: dict[str, str]) -> None:
        for table_name, table_id in table_ids.items():
            if table_name.lower() not in body.lower():
                continue
            if any(p.search(body) for p in _READ_PATTERNS):
                self._add_relationship(symbol_id, table_id, RelationshipType.READS_FROM)
            if any(p.search(body) for p in _WRITE_PATTERNS):
                self._add_relationship(symbol_id, table_id, RelationshipType.WRITES_TO)

    def _detect_database_tables(self, parsed: ParsedFile, source: str) -> None:
        file_id = self._file_node_id(parsed.file)
        seen: set[str] = set()

        for match in _TABLENAME_RE.finditer(source):
            table_name = match.group(1)
            if table_name in seen:
                continue
            seen.add(table_name)
            table_id = self._table_node_id(table_name)
            self._add_node(
                GraphNode(
                    id=table_id,
                    label=NodeLabel.DATABASE_TABLE.value,
                    properties={
                        "repo_id": self._repo_id,
                        "name": table_name,
                        "file_path": parsed.file,
                    },
                ),
            )
            self._add_relationship(file_id, table_id, RelationshipType.DEFINES)

        for match in _DB_TABLE_CLASS_RE.finditer(source):
            class_name = match.group(1)
            table_name = _camel_to_snake(class_name)
            if table_name in seen:
                continue
            seen.add(table_name)
            table_id = self._table_node_id(table_name)
            self._add_node(
                GraphNode(
                    id=table_id,
                    label=NodeLabel.DATABASE_TABLE.value,
                    properties={
                        "repo_id": self._repo_id,
                        "name": table_name,
                        "model_class": class_name,
                        "file_path": parsed.file,
                    },
                ),
            )
            self._add_relationship(file_id, table_id, RelationshipType.DEFINES)
            class_id = self._class_node_id(parsed.file, class_name)
            if class_id in self._nodes:
                self._add_relationship(class_id, table_id, RelationshipType.WRITES_TO)

    # --- Symbol resolution --------------------------------------------------
    def _resolve_caller(self, file_path: str, caller: str) -> str | None:
        if caller in self._index.by_qualified:
            return self._index.by_qualified[caller]
        if "." in caller:
            cls_name, method_name = caller.rsplit(".", 1)
            method_id = self._method_node_id(file_path, cls_name, method_name)
            if method_id in self._nodes:
                return method_id
        fn_id = self._function_node_id(file_path, caller)
        return fn_id if fn_id in self._nodes else None

    def _resolve_call_target(
        self,
        file_path: str,
        callee: str,
        receiver: str | None,
    ) -> str | None:
        if receiver:
            for class_node_id in self._index.by_name.get(receiver, ()):
                node = self._nodes.get(class_node_id)
                if node and node.label == NodeLabel.CLASS.value:
                    method_id = self._method_node_id(
                        node.properties["file_path"],
                        node.properties["name"],
                        callee,
                    )
                    if method_id in self._nodes:
                        return method_id

            method_guess = self._resolve_symbol(file_path, f"{receiver}.{callee}")
            if method_guess:
                return method_guess

        resolved = self._resolve_symbol(file_path, callee)
        if resolved:
            return resolved

        alias_module = self._resolve_import_alias(file_path, callee)
        if alias_module and alias_module in {n.properties.get("module") for n in self._nodes.values()}:
            lib_id = self._library_node_id(alias_module)
            if lib_id in self._nodes:
                return lib_id
        return None

    def _resolve_symbol(self, file_path: str, name: str) -> str | None:
        if name in self._index.by_qualified:
            return self._index.by_qualified[name]
        if "." in name:
            cls_name, member = name.rsplit(".", 1)
            method_id = self._method_node_id(file_path, cls_name, member)
            if method_id in self._nodes:
                return method_id
            for node_id in self._index.by_name.get(cls_name, ()):
                node = self._nodes[node_id]
                if node.label == NodeLabel.CLASS.value:
                    mid = self._method_node_id(node.properties["file_path"], cls_name, member)
                    if mid in self._nodes:
                        return mid
        for node_id in self._index.by_name.get(name, ()):
            return node_id
        fn_id = self._function_node_id(file_path, name)
        return fn_id if fn_id in self._nodes else None

    def _resolve_import_target(self, symbol: str, module: str) -> str | None:
        for node_id in self._index.by_name.get(symbol, ()):
            return node_id
        return self._library_node_id(module) if module else None

    def _resolve_import_alias(self, file_path: str, name: str) -> str | None:
        aliases = self._index.import_aliases.get(file_path, {})
        return aliases.get(name)


def _slice_lines(lines: list[str], start_line: int, end_line: int) -> str:
    if start_line <= 0:
        return ""
    return "\n".join(lines[start_line - 1 : end_line])


def _camel_to_snake(name: str) -> str:
    return re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()
