"""Extract function/method call sites from Tree-sitter ASTs."""

from __future__ import annotations

from tree_sitter import Node

from services.parser.models import ParsedCall
from services.parser.ts_utils import child_by_type, line_range, named_child_by_type, node_text, walk


def extract_python_calls(
    source: bytes,
    *,
    caller: str,
    body_node: Node | None,
) -> list[ParsedCall]:
    """Collect call expressions inside a Python function or method body."""
    if body_node is None:
        return []
    calls: list[ParsedCall] = []
    seen: set[tuple[str, int]] = set()
    for node in walk(body_node):
        if node.type != "call":
            continue
        callee, receiver = _python_call_target(source, node)
        if not callee:
            continue
        start, _ = line_range(node)
        key = (callee, start)
        if key in seen:
            continue
        seen.add(key)
        calls.append(
            ParsedCall(
                caller=caller,
                callee=callee,
                receiver=receiver,
                start_line=start,
                is_method_call=receiver is not None,
            ),
        )
    return calls


def extract_javascript_calls(
    source: bytes,
    *,
    caller: str,
    body_node: Node | None,
) -> list[ParsedCall]:
    """Collect call expressions inside a JS/TS function or method body."""
    if body_node is None:
        return []
    calls: list[ParsedCall] = []
    seen: set[tuple[str, int]] = set()
    for node in walk(body_node):
        if node.type != "call_expression":
            continue
        callee, receiver = _javascript_call_target(source, node)
        if not callee:
            continue
        start, _ = line_range(node)
        key = (callee, start)
        if key in seen:
            continue
        seen.add(key)
        calls.append(
            ParsedCall(
                caller=caller,
                callee=callee,
                receiver=receiver,
                start_line=start,
                is_method_call=receiver is not None,
            ),
        )
    return calls


def _python_call_target(source: bytes, call_node: Node) -> tuple[str | None, str | None]:
    fn = child_by_type(call_node, "function") or child_by_type(call_node, "attribute")
    if fn is None:
        for child in call_node.children:
            if child.type in {"identifier", "attribute"}:
                fn = child
                break
    if fn is None:
        return None, None
    if fn.type == "identifier":
        return node_text(source, fn), None
    if fn.type == "attribute":
        obj = child_by_type(fn, "object") or child_by_type(fn, "identifier")
        attr = named_child_by_type(fn, "identifier") or child_by_type(fn, "attribute")
        if attr is None:
            return None, None
        receiver = node_text(source, obj) if obj is not None else None
        return node_text(source, attr), receiver
    return None, None


def _javascript_call_target(source: bytes, call_node: Node) -> tuple[str | None, str | None]:
    fn = call_node.child_by_field_name("function")
    if fn is None:
        for child in call_node.named_children:
            if child.type in {"identifier", "member_expression"}:
                fn = child
                break
    if fn is None:
        return None, None
    if fn.type == "identifier":
        return node_text(source, fn), None
    if fn.type == "member_expression":
        obj = fn.child_by_field_name("object")
        prop = fn.child_by_field_name("property")
        if prop is None:
            return None, None
        receiver = node_text(source, obj) if obj is not None else None
        return node_text(source, prop), receiver
    return None, None
