"""Registry mapping Tree-sitter languages to extractors."""

from __future__ import annotations

from services.parser.languages.base import LanguageExtractor
from services.parser.languages.generic_extractor import GenericExtractor
from services.parser.languages.javascript_extractor import JavaScriptExtractor
from services.parser.languages.python_extractor import PythonExtractor

_EXTRACTORS: dict[str, LanguageExtractor] = {
    "python": PythonExtractor(),
    "javascript": JavaScriptExtractor(),
    "typescript": JavaScriptExtractor(),
    "tsx": JavaScriptExtractor(),
}

_GENERIC = GenericExtractor()


def get_extractor(ts_language: str) -> LanguageExtractor:
    return _EXTRACTORS.get(ts_language, _GENERIC)
