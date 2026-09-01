"""Web framework route detection (FastAPI, Flask, Express)."""

from __future__ import annotations

import re

from tree_sitter import Node

from services.parser.models import ParsedApiEndpoint
from services.parser.ts_utils import child_by_type, line_range, node_text, walk

_HTTP_METHODS = frozenset({"get", "post", "put", "patch", "delete", "head", "options"})


def detect_api_endpoints(language: str, source: bytes, root: Node) -> list[ParsedApiEndpoint]:
    if language == "python":
        return _detect_python_endpoints(source, root)
    if language in {"javascript", "typescript", "tsx"}:
        return _detect_js_endpoints(source, root)
    return []


def _detect_python_endpoints(source: bytes, root: Node) -> list[ParsedApiEndpoint]:
    endpoints: list[ParsedApiEndpoint] = []
    for node in walk(root):
        if node.type not in {"function_definition", "async_function_definition"}:
            continue
        name_node = child_by_type(node, "identifier")
        if name_node is None:
            continue
        handler = node_text(source, name_node)
        parent = node.parent
        if parent is None or parent.type != "decorated_definition":
            continue
        for dec in parent.children:
            if dec.type != "decorator":
                continue
            endpoint = _parse_python_decorator(source, dec, handler)
            if endpoint:
                endpoints.append(endpoint)
    return endpoints


def _parse_python_decorator(
    source: bytes, decorator: Node, handler: str
) -> ParsedApiEndpoint | None:
    call = child_by_type(decorator, "call")
    if call is None:
        return None
    func = call.children[0] if call.children else None
    if func is None:
        return None
    func_text = node_text(source, func)
    method = "GET"
    if "." in func_text:
        method = func_text.rsplit(".", 1)[-1].upper()
    if method not in {m.upper() for m in _HTTP_METHODS}:
        if func_text.endswith(".route"):
            method = _flask_methods(source, call)
        else:
            return None
    route = _first_string_arg(source, call)
    if not route:
        return None
    start, _ = line_range(decorator)
    return ParsedApiEndpoint(route=route, method=method.upper(), handler=handler, start_line=start)


def _flask_methods(source: bytes, call: Node) -> str:
    args = child_by_type(call, "argument_list")
    if args is None:
        return "GET"
    text = node_text(source, args)
    match = re.search(r"methods\s*=\s*\[\s*['\"](\w+)['\"]", text)
    return match.group(1).upper() if match else "GET"


def _first_string_arg(source: bytes, call: Node) -> str | None:
    args = child_by_type(call, "argument_list")
    if args is None:
        return None
    for child in args.children:
        if child.type == "string":
            raw = node_text(source, child)
            return raw.strip("'\"") if raw else None
    return None


def _detect_js_endpoints(source: bytes, root: Node) -> list[ParsedApiEndpoint]:
    endpoints: list[ParsedApiEndpoint] = []
    for node in walk(root):
        if node.type != "call_expression":
            continue
        func = node.children[0] if node.children else None
        if func is None or func.type != "member_expression":
            continue
        prop = func.children[-1] if func.children else None
        if prop is None:
            continue
        method_name = node_text(source, prop).lower()
        if method_name not in _HTTP_METHODS:
            continue
        args = child_by_type(node, "arguments")
        if args is None:
            continue
        route = _js_route_arg(source, args)
        handler = _js_handler_arg(source, args)
        if not route:
            continue
        start, _ = line_range(node)
        endpoints.append(
            ParsedApiEndpoint(route=route, method=method_name.upper(), handler=handler or "", start_line=start)
        )
    return endpoints


def _js_route_arg(source: bytes, args: Node) -> str | None:
    strings = [c for c in args.children if c.type == "string"]
    if not strings:
        return None
    raw = node_text(source, strings[0])
    return raw.strip("'\"") if raw else None


def _js_handler_arg(source: bytes, args: Node) -> str | None:
    for child in args.children:
        if child.type == "identifier":
            return node_text(source, child)
        if child.type == "arrow_function":
            return "<anonymous>"
    return None
