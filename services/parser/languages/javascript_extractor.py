"""JavaScript / TypeScript symbol extraction."""

from __future__ import annotations

from tree_sitter import Node

from services.parser.calls import extract_javascript_calls
from services.parser.complexity import file_complexity
from services.parser.frameworks import detect_api_endpoints
from services.parser.languages.base import LanguageExtractor, is_external_import
from services.parser.models import (
    FileMetadata,
    Parameter,
    ParsedClass,
    ParsedCall,
    ParsedFile,
    ParsedFunction,
    ParsedImport,
)
from services.parser.ts_utils import (
    child_by_type,
    count_lines,
    line_range,
    named_child_by_type,
    node_text,
    walk,
)


class JavaScriptExtractor(LanguageExtractor):
    language = "javascript"

    def extract(
        self,
        *,
        rel_path: str,
        language_label: str,
        source: bytes,
        root: Node,
        repo_root_marker: str | None = None,
    ) -> ParsedFile:
        functions: list[ParsedFunction] = []
        classes: list[ParsedClass] = []
        imports: list[ParsedImport] = []
        seen_functions: set[tuple[str, int]] = set()
        seen_classes: set[tuple[str, int]] = set()

        def add_class(cls: ParsedClass | None) -> None:
            if cls and (cls.name, cls.start_line) not in seen_classes:
                seen_classes.add((cls.name, cls.start_line))
                classes.append(cls)

        def add_function(fn: ParsedFunction | None) -> None:
            if fn and (fn.name, fn.start_line) not in seen_functions:
                seen_functions.add((fn.name, fn.start_line))
                functions.append(fn)

        for node in walk(root):
            if node.type == "import_statement":
                imports.extend(_parse_import(source, node, repo_root_marker))
            elif node.type in {"class_declaration", "class"}:
                add_class(_parse_class(source, node))
            elif node.type == "export_statement":
                for child in node.named_children:
                    if child.type in {"class_declaration", "class"}:
                        add_class(_parse_class(source, child))
                    elif child.type == "function_declaration":
                        add_function(_parse_function(source, child))
            elif node.type in {"function_declaration", "generator_function_declaration"}:
                add_function(_parse_function(source, node))
            elif node.type == "method_definition" and _is_class_body_child(node):
                continue
            elif node.type == "lexical_declaration":
                for declarator in [c for c in node.children if c.type == "variable_declarator"]:
                    add_function(_parse_arrow_function(source, declarator))

        symbol_count = len(functions) + sum(len(c.methods) for c in classes) + len(classes)
        ts_lang = "typescript" if language_label.lower() == "typescript" else "javascript"
        calls = _collect_javascript_file_calls(source, root)
        return ParsedFile(
            file=rel_path,
            language=language_label,
            classes=classes,
            functions=functions,
            imports=imports,
            api_endpoints=detect_api_endpoints(ts_lang, source, root),
            calls=calls,
            metadata=FileMetadata(
                complexity=file_complexity(root),
                lines=count_lines(source),
                symbol_count=symbol_count,
            ),
        )


def _is_class_body_child(node: Node) -> bool:
    parent = node.parent
    while parent:
        if parent.type == "class_body":
            return True
        if parent.type in {"program", "statement_block"}:
            return False
        parent = parent.parent
    return False


def _parse_function(source: bytes, node: Node, class_name: str | None = None) -> ParsedFunction | None:
    name_node = (
        named_child_by_type(node, "identifier")
        or named_child_by_type(node, "property_identifier")
        or named_child_by_type(node, "type_identifier")
    )
    if name_node is None:
        return None
    name = node_text(source, name_node)
    params = _parse_parameters(source, node)
    ret = _parse_return_type(source, node)
    start, end = line_range(node)
    return ParsedFunction(
        name=name,
        parameters=params,
        return_type=ret,
        start_line=start,
        end_line=end,
        is_method=class_name is not None,
        class_name=class_name,
    )


def _parse_arrow_function(source: bytes, declarator: Node) -> ParsedFunction | None:
    name_node = named_child_by_type(declarator, "identifier")
    value = None
    for child in declarator.children:
        if child.type == "arrow_function":
            value = child
            break
    if name_node is None or value is None:
        return None
    params = _parse_parameters(source, value)
    ret = _parse_return_type(source, value)
    start, end = line_range(declarator)
    return ParsedFunction(
        name=node_text(source, name_node),
        parameters=params,
        return_type=ret,
        start_line=start,
        end_line=end,
    )


def _parse_class(source: bytes, node: Node) -> ParsedClass | None:
    name_node = named_child_by_type(node, "identifier") or named_child_by_type(node, "type_identifier")
    if name_node is None:
        return None
    name = node_text(source, name_node)
    bases, implements = _parse_heritage(source, node)
    methods: list[ParsedFunction] = []
    attributes: list[str] = []
    body = child_by_type(node, "class_body")
    if body:
        for child in body.children:
            if child.type == "method_definition":
                fn = _parse_function(source, child, class_name=name)
                if fn:
                    methods.append(fn)
            elif child.type in {"public_field_definition", "field_definition"}:
                name_n = named_child_by_type(child, "property_identifier") or named_child_by_type(child, "identifier")
                if name_n:
                    attributes.append(node_text(source, name_n))
    start, end = line_range(node)
    return ParsedClass(
        name=name,
        methods=methods,
        bases=bases,
        implements=implements,
        attributes=attributes,
        start_line=start,
        end_line=end,
    )


def _parse_parameters(source: bytes, node: Node) -> list[Parameter]:
    params: list[Parameter] = []
    params_node = child_by_type(node, "formal_parameters")
    if params_node is None:
        return params
    for child in params_node.children:
        if child.type == "identifier":
            params.append(Parameter(name=node_text(source, child)))
        elif child.type == "required_parameter":
            name_n = named_child_by_type(child, "identifier")
            type_n = child_by_type(child, "type_annotation")
            if name_n:
                ptype = node_text(source, type_n).lstrip(": ") if type_n else None
                params.append(Parameter(name=node_text(source, name_n), type=ptype))
        elif child.type == "optional_parameter":
            name_n = named_child_by_type(child, "identifier")
            if name_n:
                params.append(Parameter(name=node_text(source, name_n)))
    return params


def _parse_return_type(source: bytes, node: Node) -> str | None:
    type_node = child_by_type(node, "type_annotation")
    return node_text(source, type_node).lstrip(": ") if type_node else None


def _parse_heritage(source: bytes, node: Node) -> tuple[list[str], list[str]]:
    clause = child_by_type(node, "class_heritage")
    if clause is None:
        return [], []
    extends: list[str] = []
    implements: list[str] = []
    for child in clause.children:
        if child.type == "extends_clause":
            extends.extend(
                node_text(source, c)
                for c in walk(child)
                if c.type in {"identifier", "type_identifier"}
            )
        elif child.type == "implements_clause":
            implements.extend(
                node_text(source, c)
                for c in walk(child)
                if c.type in {"identifier", "type_identifier"}
            )
    if not extends and not implements:
        extends = _parse_bases(source, node)
    return extends, implements


def _parse_bases(source: bytes, node: Node) -> list[str]:
    clause = child_by_type(node, "class_heritage")
    if clause is None:
        return []
    identifiers = [node_text(source, c) for c in walk(clause) if c.type == "identifier"]
    return identifiers


def _parse_import(source: bytes, node: Node, repo_root_marker: str | None) -> list[ParsedImport]:
    start, _ = line_range(node)
    module = ""
    names: list[str] = []
    for child in node.children:
        if child.type == "string":
            module = node_text(source, child).strip("'\"")
        elif child.type == "import_clause":
            for part in walk(child):
                if part.type == "identifier":
                    names.append(node_text(source, part))
    if not module:
        text = node_text(source, node)
        if "from" in text:
            module = text.split("from", 1)[1].strip().strip("'\";")
    return [
        ParsedImport(
            module=module,
            names=names or ["default"],
            is_external=is_external_import(module, repo_root_marker),
            start_line=start,
        )
    ]


def _collect_javascript_file_calls(source: bytes, root: Node) -> list[ParsedCall]:
    calls: list[ParsedCall] = []

    def walk_defs(node: Node) -> None:
        if node.type in {
            "function_declaration",
            "generator_function_declaration",
            "method_definition",
            "arrow_function",
        }:
            name_node = (
                named_child_by_type(node, "identifier")
                or named_child_by_type(node, "property_identifier")
            )
            if name_node is None and node.type != "arrow_function":
                return
            fn_name = node_text(source, name_node) if name_node else "<anonymous>"
            class_name = _enclosing_js_class_name(node, source)
            caller = f"{class_name}.{fn_name}" if class_name else fn_name
            body = child_by_type(node, "statement_block") or child_by_type(node, "body")
            if body is None and node.type == "arrow_function":
                body = node
            calls.extend(extract_javascript_calls(source, caller=caller, body_node=body))
        for child in node.children:
            walk_defs(child)

    walk_defs(root)
    return calls


def _enclosing_js_class_name(node: Node, source: bytes) -> str | None:
    parent = node.parent
    while parent is not None:
        if parent.type in {"class_declaration", "class"}:
            name_node = named_child_by_type(parent, "identifier") or named_child_by_type(
                parent, "type_identifier",
            )
            return node_text(source, name_node) if name_node else None
        parent = parent.parent
    return None
