"""Generic fallback extractor for languages without a dedicated handler."""

from __future__ import annotations

from tree_sitter import Node

from services.parser.complexity import file_complexity
from services.parser.languages.base import LanguageExtractor
from services.parser.models import FileMetadata, Parameter, ParsedClass, ParsedFile, ParsedFunction
from services.parser.ts_utils import line_range, named_child_by_type, node_text, walk

_FUNCTION_TYPES = frozenset(
    {
        "function_definition",
        "function_declaration",
        "function_item",
        "method_declaration",
        "method_definition",
        "constructor_declaration",
        "func_literal",
        "function",
    }
)
_CLASS_TYPES = frozenset(
    {
        "class_definition",
        "class_declaration",
        "class_specifier",
        "impl_item",
    }
)


class GenericExtractor(LanguageExtractor):
    language = "generic"

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
        seen: set[tuple[str, int]] = set()

        for node in walk(root):
            if node.type in _CLASS_TYPES:
                cls = _parse_class_generic(source, node)
                if cls and (cls.name, cls.start_line) not in seen:
                    seen.add((cls.name, cls.start_line))
                    classes.append(cls)
            elif node.type in _FUNCTION_TYPES:
                fn = _parse_function_generic(source, node)
                if fn and (fn.name, fn.start_line) not in seen:
                    seen.add((fn.name, fn.start_line))
                    functions.append(fn)

        symbol_count = len(functions) + len(classes)
        return ParsedFile(
            file=rel_path,
            language=language_label,
            classes=classes,
            functions=functions,
            metadata=FileMetadata(
                complexity=file_complexity(root),
                lines=source.count(b"\n") + (0 if source.endswith(b"\n") else 1),
                symbol_count=symbol_count,
            ),
        )


def _parse_function_generic(source: bytes, node: Node) -> ParsedFunction | None:
    name_node = named_child_by_type(node, "identifier") or named_child_by_type(node, "property_identifier")
    name = node_text(source, name_node) if name_node else "<anonymous>"
    start, end = line_range(node)
    return ParsedFunction(
        name=name,
        parameters=[],
        return_type=None,
        start_line=start,
        end_line=end,
    )


def _parse_class_generic(source: bytes, node: Node) -> ParsedClass | None:
    name_node = named_child_by_type(node, "identifier") or named_child_by_type(node, "type_identifier")
    if name_node is None:
        return None
    start, end = line_range(node)
    return ParsedClass(
        name=node_text(source, name_node),
        methods=[],
        bases=[],
        attributes=[],
        start_line=start,
        end_line=end,
    )
