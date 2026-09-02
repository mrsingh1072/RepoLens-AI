"""Python symbol extraction."""

from __future__ import annotations

from tree_sitter import Node

from services.parser.calls import extract_javascript_calls, extract_python_calls
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
    children_by_type,
    count_lines,
    extract_docstring,
    line_range,
    named_child_by_type,
    node_text,
    walk,
)


class PythonExtractor(LanguageExtractor):
    language = "python"

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

        for node in root.children:
            if node.type in {"function_definition", "async_function_definition"}:
                fn = _parse_function(source, node)
                if fn:
                    functions.append(fn)
            elif node.type == "class_definition":
                cls = _parse_class(source, node)
                if cls:
                    classes.append(cls)
            elif node.type == "decorated_definition":
                inner = next((c for c in node.children if c.type in {
                    "function_definition", "async_function_definition", "class_definition"
                }), None)
                if inner is None:
                    continue
                if inner.type == "class_definition":
                    cls = _parse_class(source, inner)
                    if cls:
                        classes.append(cls)
                else:
                    fn = _parse_function(source, inner)
                    if fn:
                        functions.append(fn)
            elif node.type == "import_statement":
                imports.extend(_parse_import(source, node, repo_root_marker))
            elif node.type == "import_from_statement":
                imports.extend(_parse_import_from(source, node, repo_root_marker))

        symbol_count = len(functions) + sum(len(c.methods) for c in classes) + len(classes)
        calls = _collect_python_file_calls(source, functions, classes)
        return ParsedFile(
            file=rel_path,
            language=language_label,
            classes=classes,
            functions=functions,
            imports=imports,
            api_endpoints=detect_api_endpoints(self.language, source, root),
            calls=calls,
            metadata=FileMetadata(
                complexity=file_complexity(root),
                lines=count_lines(source),
                symbol_count=symbol_count,
            ),
        )


def _parse_function(source: bytes, node: Node, class_name: str | None = None) -> ParsedFunction | None:
    name_node = named_child_by_type(node, "identifier")
    if name_node is None:
        return None
    name = node_text(source, name_node)
    params = _parse_parameters(source, node)
    ret = _parse_return_type(source, node)
    body = child_by_type(node, "block")
    doc = extract_docstring(source, body)
    start, end = line_range(node)
    return ParsedFunction(
        name=name,
        parameters=params,
        return_type=ret,
        start_line=start,
        end_line=end,
        docstring=doc,
        is_method=class_name is not None,
        class_name=class_name,
    )


def _parse_class(source: bytes, node: Node) -> ParsedClass | None:
    name_node = named_child_by_type(node, "identifier")
    if name_node is None:
        return None
    name = node_text(source, name_node)
    bases = _parse_bases(source, node)
    body = child_by_type(node, "block")
    methods: list[ParsedFunction] = []
    attributes: list[str] = []
    if body:
        for child in body.children:
            if child.type in {"function_definition", "async_function_definition"}:
                fn = _parse_function(source, child, class_name=name)
                if fn:
                    methods.append(fn)
            elif child.type == "expression_statement":
                assign = child_by_type(child, "assignment")
                if assign:
                    target = assign.children[0] if assign.children else None
                    if target is not None and target.type == "identifier":
                        attributes.append(node_text(source, target))
    doc = extract_docstring(source, body)
    start, end = line_range(node)
    return ParsedClass(
        name=name,
        methods=methods,
        bases=bases,
        attributes=attributes,
        start_line=start,
        end_line=end,
        docstring=doc,
    )


def _parse_parameters(source: bytes, node: Node) -> list[Parameter]:
    params: list[Parameter] = []
    params_node = child_by_type(node, "parameters")
    if params_node is None:
        return params
    for child in params_node.children:
        if child.type in {"identifier", "typed_parameter", "typed_default_parameter", "default_parameter"}:
            if child.type == "identifier":
                params.append(Parameter(name=node_text(source, child)))
            elif child.type == "typed_parameter":
                name_n = named_child_by_type(child, "identifier")
                type_n = child_by_type(child, "type")
                if name_n:
                    params.append(
                        Parameter(
                            name=node_text(source, name_n),
                            type=node_text(source, type_n) if type_n else None,
                        )
                    )
            elif child.type in {"default_parameter", "typed_default_parameter"}:
                name_n = named_child_by_type(child, "identifier")
                type_n = child_by_type(child, "type")
                if name_n:
                    params.append(
                        Parameter(
                            name=node_text(source, name_n),
                            type=node_text(source, type_n) if type_n else None,
                        )
                    )
    return params


def _parse_return_type(source: bytes, node: Node) -> str | None:
    type_node = child_by_type(node, "type")
    return node_text(source, type_node) if type_node else None


def _parse_bases(source: bytes, node: Node) -> list[str]:
    arg_list = child_by_type(node, "argument_list")
    if arg_list is None:
        return []
    return [node_text(source, c) for c in arg_list.children if c.type not in {",", "(", ")"}]


def _parse_import(source: bytes, node: Node, repo_root_marker: str | None) -> list[ParsedImport]:
    start, _ = line_range(node)
    results: list[ParsedImport] = []
    for child in node.children:
        if child.type == "dotted_name":
            module = node_text(source, child)
            results.append(
                ParsedImport(
                    module=module,
                    names=[module.rsplit(".", 1)[-1]],
                    is_external=is_external_import(module, repo_root_marker),
                    start_line=start,
                )
            )
        elif child.type == "aliased_import":
            name = child_by_type(child, "dotted_name")
            if name:
                module = node_text(source, name)
                results.append(
                    ParsedImport(
                        module=module,
                        names=[module.rsplit(".", 1)[-1]],
                        is_external=is_external_import(module, repo_root_marker),
                        start_line=start,
                    )
                )
    return results


def _parse_import_from(source: bytes, node: Node, repo_root_marker: str | None) -> list[ParsedImport]:
    start, _ = line_range(node)
    module_node = child_by_type(node, "dotted_name") or child_by_type(node, "relative_import")
    module = node_text(source, module_node) if module_node else ""
    names = [
        node_text(source, c)
        for c in node.children
        if c.type == "identifier"
    ]
    return [
        ParsedImport(
            module=module,
            names=names or ["*"],
            is_external=is_external_import(module, repo_root_marker),
            start_line=start,
        )
    ]


def _collect_python_file_calls(
    source: bytes,
    functions: list[ParsedFunction],
    classes: list[ParsedClass],
) -> list[ParsedCall]:
    """Re-walk the module AST to attach call sites to parsed symbols."""
    from services.parser.ts_utils import parse_bytes

    tree = parse_bytes("python", source)
    if tree is None:
        return []

    calls: list[ParsedCall] = []

    def walk_defs(node: Node) -> None:
        if node.type in {"function_definition", "async_function_definition"}:
            name_node = named_child_by_type(node, "identifier")
            if name_node is None:
                return
            fn_name = node_text(source, name_node)
            class_name = _enclosing_class_name(node, source)
            caller = f"{class_name}.{fn_name}" if class_name else fn_name
            body = child_by_type(node, "block")
            calls.extend(extract_python_calls(source, caller=caller, body_node=body))
        for child in node.children:
            walk_defs(child)

    walk_defs(tree.root_node)
    return calls


def _enclosing_class_name(node: Node, source: bytes) -> str | None:
    parent = node.parent
    while parent is not None:
        if parent.type == "class_definition":
            name_node = named_child_by_type(parent, "identifier")
            return node_text(source, name_node) if name_node else None
        parent = parent.parent
    return None
