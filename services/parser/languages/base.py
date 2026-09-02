"""Language-specific Tree-sitter extractors."""

from __future__ import annotations

from abc import ABC, abstractmethod

from tree_sitter import Node

from services.parser.models import ParsedClass, ParsedFile, ParsedFunction, ParsedImport


class LanguageExtractor(ABC):
    """Extract structured symbols from a parsed syntax tree."""

    language: str

    @abstractmethod
    def extract(
        self,
        *,
        rel_path: str,
        language_label: str,
        source: bytes,
        root: Node,
        repo_root_marker: str | None = None,
    ) -> ParsedFile:
        """Return structured parse output for a single file."""


def is_external_import(module: str, repo_root_marker: str | None) -> bool:
    """Heuristic: treat stdlib/third-party as external, project paths as internal."""
    if not module:
        return True
    if module.startswith("."):
        return False
    if repo_root_marker and repo_root_marker in module.replace("/", "."):
        return False
    stdlib_hints = ("app.", "src.", "lib.", "backend.", "frontend.", "services.")
    if any(module.startswith(h) for h in stdlib_hints):
        return False
    # Relative project packages often lack dots
    if "." not in module and repo_root_marker:
        return module not in repo_root_marker
    return True
