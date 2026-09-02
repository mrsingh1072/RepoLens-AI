"""Structured parse result models."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(slots=True)
class Parameter:
    name: str
    type: str | None = None


@dataclass(slots=True)
class ParsedFunction:
    name: str
    parameters: list[Parameter]
    return_type: str | None
    start_line: int
    end_line: int
    docstring: str | None = None
    is_method: bool = False
    class_name: str | None = None


@dataclass(slots=True)
class ParsedCall:
    """A function or method invocation inside a caller symbol."""

    caller: str
    callee: str
    receiver: str | None = None
    start_line: int = 0
    is_method_call: bool = False


@dataclass(slots=True)
class ParsedClass:
    name: str
    methods: list[ParsedFunction]
    bases: list[str]
    implements: list[str] = field(default_factory=list)
    attributes: list[str] = field(default_factory=list)
    start_line: int = 0
    end_line: int = 0
    docstring: str | None = None


@dataclass(slots=True)
class ParsedImport:
    module: str
    names: list[str]
    is_external: bool
    start_line: int


@dataclass(slots=True)
class ParsedApiEndpoint:
    route: str
    method: str
    handler: str
    start_line: int


@dataclass(slots=True)
class FileMetadata:
    complexity: str
    lines: int
    symbol_count: int = 0


@dataclass(slots=True)
class ParsedFile:
    """Structured semantic units extracted from a single source file."""

    file: str
    language: str
    classes: list[ParsedClass] = field(default_factory=list)
    functions: list[ParsedFunction] = field(default_factory=list)
    imports: list[ParsedImport] = field(default_factory=list)
    api_endpoints: list[ParsedApiEndpoint] = field(default_factory=list)
    calls: list[ParsedCall] = field(default_factory=list)
    metadata: FileMetadata = field(default_factory=lambda: FileMetadata(complexity="low", lines=0))

    def to_dict(self) -> dict[str, Any]:
        """Serialize to the canonical JSON-friendly output structure."""
        return {
            "file": self.file,
            "language": self.language,
            "classes": [
                {
                    "name": c.name,
                    "methods": [_function_dict(m) for m in c.methods],
                    "bases": c.bases,
                    "implements": c.implements,
                    "attributes": c.attributes,
                    "start_line": c.start_line,
                    "end_line": c.end_line,
                    "docstring": c.docstring,
                }
                for c in self.classes
            ],
            "functions": [_function_dict(f) for f in self.functions],
            "imports": [
                {
                    "module": i.module,
                    "names": i.names,
                    "is_external": i.is_external,
                    "start_line": i.start_line,
                }
                for i in self.imports
            ],
            "api_endpoints": [asdict(e) for e in self.api_endpoints],
            "calls": [asdict(c) for c in self.calls],
            "metadata": {
                "complexity": self.metadata.complexity,
                "lines": self.metadata.lines,
                "symbol_count": self.metadata.symbol_count,
            },
        }


def _function_dict(fn: ParsedFunction) -> dict[str, Any]:
    return {
        "name": fn.name,
        "parameters": [asdict(p) for p in fn.parameters],
        "return_type": fn.return_type,
        "start_line": fn.start_line,
        "end_line": fn.end_line,
        "docstring": fn.docstring,
        "is_method": fn.is_method,
        "class_name": fn.class_name,
    }
