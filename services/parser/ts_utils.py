"""Tree-sitter parsing utilities."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from functools import lru_cache
from typing import TYPE_CHECKING

from tree_sitter import Language, Node, Parser, Tree

if TYPE_CHECKING:
    pass

_PARSER_CACHE: dict[str, Parser] = {}


@lru_cache(maxsize=32)
def _load_language(language: str) -> Language | None:
    try:
        from tree_sitter_language_pack import get_language

        return get_language(language)
    except Exception:
        return None


def get_parser(language: str) -> Parser | None:
    """Return a cached Tree-sitter parser for *language*, or ``None`` if unavailable."""
    if language in _PARSER_CACHE:
        return _PARSER_CACHE[language]
    lang = _load_language(language)
    if lang is None:
        return None
    parser = Parser(lang)
    _PARSER_CACHE[language] = parser
    return parser


def parse_bytes(language: str, source: bytes) -> Tree | None:
    parser = get_parser(language)
    if parser is None:
        return None
    return parser.parse(source)


def node_text(source: bytes, node: Node) -> str:
    return source[node.start_byte : node.end_byte].decode("utf-8", errors="replace")


def line_range(node: Node) -> tuple[int, int]:
    """Return 1-indexed inclusive start/end line numbers."""
    return node.start_point[0] + 1, node.end_point[0] + 1


def walk(node: Node) -> Iterator[Node]:
    stack = [node]
    while stack:
        current = stack.pop()
        yield current
        for child in reversed(current.children):
            stack.append(child)


def child_by_type(node: Node, node_type: str) -> Node | None:
    for child in node.children:
        if child.type == node_type:
            return child
    return None


def children_by_type(node: Node, node_type: str) -> list[Node]:
    return [c for c in node.children if c.type == node_type]


def named_child_by_type(node: Node, node_type: str) -> Node | None:
    for child in node.named_children:
        if child.type == node_type:
            return child
    return None


def strip_quotes(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] in {"'", '"'} and value[-1] == value[0]:
        return value[1:-1]
    return value


def extract_docstring(source: bytes, body_node: Node | None) -> str | None:
    """Extract a leading docstring from a function/class body block."""
    if body_node is None:
        return None
    block = child_by_type(body_node, "block") or body_node
    for child in block.children:
        if child.type != "expression_statement":
            break
        expr = child_by_type(child, "string")
        if expr is not None:
            return _clean_string_literal(node_text(source, expr))
        break
    return None


def _clean_string_literal(raw: str) -> str:
    text = raw.strip()
    if text.startswith('"""') and text.endswith('"""'):
        return text[3:-3]
    if text.startswith("'''") and text.endswith("'''"):
        return text[3:-3]
    return strip_quotes(text)


def count_lines(source: bytes) -> int:
    if not source:
        return 0
    return source.count(b"\n") + (0 if source.endswith(b"\n") else 1)


def map_extension_to_ts_language(language_label: str, extension: str) -> str:
    """Map a human-readable language label / extension to a Tree-sitter grammar name."""
    ext = extension.lower()
    mapping = {
        ".py": "python",
        ".js": "javascript",
        ".jsx": "javascript",
        ".mjs": "javascript",
        ".cjs": "javascript",
        ".ts": "typescript",
        ".tsx": "tsx",
        ".java": "java",
        ".go": "go",
        ".rs": "rust",
        ".cpp": "cpp",
        ".cc": "cpp",
        ".cxx": "cpp",
        ".h": "c",
        ".hpp": "cpp",
        ".c": "c",
        ".rb": "ruby",
        ".php": "php",
        ".swift": "swift",
        ".kt": "kotlin",
        ".scala": "scala",
        ".cs": "c_sharp",
    }
    if ext in mapping:
        return mapping[ext]
    label = language_label.lower()
    aliases = {
        "python": "python",
        "javascript": "javascript",
        "typescript": "typescript",
        "java": "java",
        "go": "go",
        "rust": "rust",
        "c++": "cpp",
        "c": "c",
        "ruby": "ruby",
        "php": "php",
        "kotlin": "kotlin",
        "scala": "scala",
        "c#": "c_sharp",
    }
    return aliases.get(label, "python")


def visit_nodes(node: Node, predicate: Callable[[Node], bool]) -> Iterator[Node]:
    for child in walk(node):
        if predicate(child):
            yield child
