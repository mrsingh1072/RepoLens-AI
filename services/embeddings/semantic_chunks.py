"""Build semantic chunks with imports context — no naive splitting."""

from __future__ import annotations

import hashlib
import re

from services.embeddings.models import SemanticChunk
from services.parser.models import ParsedClass, ParsedFile

# Classes at or below this line count are embedded as a single unit.
DEFAULT_CLASS_LINE_THRESHOLD = 80
MIN_MODULE_LINES = 3


def build_semantic_chunks(
    parsed: ParsedFile,
    source: str,
    *,
    repo_id: str,
    class_line_threshold: int = DEFAULT_CLASS_LINE_THRESHOLD,
) -> list[SemanticChunk]:
    """Create embedding-ready chunks from a parsed file."""
    lines = source.splitlines()
    imports_ctx = _format_imports(parsed)
    chunks: list[SemanticChunk] = []
    covered = _CoverageTracker(len(lines))

    for fn in parsed.functions:
        code = _slice_lines(lines, fn.start_line, fn.end_line)
        if not code.strip():
            continue
        covered.mark(fn.start_line, fn.end_line)
        chunks.append(
            _make_chunk(
                repo_id=repo_id,
                parsed=parsed,
                chunk_type="function",
                symbol=fn.name,
                class_name=None,
                function_name=fn.name,
                code=code,
                imports_context=imports_ctx,
                start_line=fn.start_line,
                end_line=fn.end_line,
                tags=["function", parsed.language, parsed.metadata.complexity],
            )
        )

    for cls in parsed.classes:
        class_lines = cls.end_line - cls.start_line + 1
        if cls.methods and class_lines <= class_line_threshold:
            code = _slice_lines(lines, cls.start_line, cls.end_line)
            covered.mark(cls.start_line, cls.end_line)
            chunks.append(
                _make_chunk(
                    repo_id=repo_id,
                    parsed=parsed,
                    chunk_type="class",
                    symbol=cls.name,
                    class_name=cls.name,
                    function_name=None,
                    code=code,
                    imports_context=imports_ctx,
                    start_line=cls.start_line,
                    end_line=cls.end_line,
                    tags=["class", "small-class", parsed.language],
                )
            )
        elif cls.methods:
            for method in cls.methods:
                code = _slice_lines(lines, method.start_line, method.end_line)
                if not code.strip():
                    continue
                covered.mark(method.start_line, method.end_line)
                symbol = f"{cls.name}.{method.name}"
                chunks.append(
                    _make_chunk(
                        repo_id=repo_id,
                        parsed=parsed,
                        chunk_type="method",
                        symbol=symbol,
                        class_name=cls.name,
                        function_name=method.name,
                        code=code,
                        imports_context=imports_ctx,
                        start_line=method.start_line,
                        end_line=method.end_line,
                        tags=["method", parsed.language, cls.name],
                    )
                )
        else:
            code = _slice_lines(lines, cls.start_line, cls.end_line)
            covered.mark(cls.start_line, cls.end_line)
            chunks.append(
                _make_chunk(
                    repo_id=repo_id,
                    parsed=parsed,
                    chunk_type="class",
                    symbol=cls.name,
                    class_name=cls.name,
                    function_name=None,
                    code=code,
                    imports_context=imports_ctx,
                    start_line=cls.start_line,
                    end_line=cls.end_line,
                    tags=["class", parsed.language],
                )
            )

    for start, end in covered.uncovered_ranges():
        block = _slice_lines(lines, start, end)
        if not _is_meaningful_module_block(block):
            continue
        chunks.append(
            _make_chunk(
                repo_id=repo_id,
                parsed=parsed,
                chunk_type="module",
                symbol=f"module:{parsed.file}:{start}",
                class_name=None,
                function_name=None,
                code=block,
                imports_context=imports_ctx,
                start_line=start,
                end_line=end,
                tags=["module", parsed.language, "top-level"],
            )
        )

    return chunks


def build_repository_chunks(
    repo_id: str,
    parsed_files: list[ParsedFile],
    sources: dict[str, str],
    *,
    class_line_threshold: int = DEFAULT_CLASS_LINE_THRESHOLD,
) -> list[SemanticChunk]:
    all_chunks: list[SemanticChunk] = []
    for parsed in parsed_files:
        source = sources.get(parsed.file, "")
        if not source:
            continue
        all_chunks.extend(
            build_semantic_chunks(
                parsed,
                source,
                repo_id=repo_id,
                class_line_threshold=class_line_threshold,
            )
        )
    return all_chunks


def file_content_hash(source: str) -> str:
    return hashlib.sha256(source.encode("utf-8")).hexdigest()


def chunk_content_hash(repo_id: str, file_path: str, symbol: str, code: str, start_line: int) -> str:
    payload = f"{repo_id}|{file_path}|{symbol}|{start_line}|{code}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _make_chunk(
    *,
    repo_id: str,
    parsed: ParsedFile,
    chunk_type: str,
    symbol: str,
    class_name: str | None,
    function_name: str | None,
    code: str,
    imports_context: str,
    start_line: int,
    end_line: int,
    tags: list[str],
) -> SemanticChunk:
    document = _format_document(
        file_path=parsed.file,
        language=parsed.language,
        imports_context=imports_context,
        symbol=symbol,
        chunk_type=chunk_type,
        code=code,
    )
    content_hash = chunk_content_hash(repo_id, parsed.file, symbol, code, start_line)
    return SemanticChunk(
        repo_id=repo_id,
        file_path=parsed.file,
        language=parsed.language,
        chunk_type=chunk_type,
        class_name=class_name,
        function_name=function_name,
        symbol=symbol,
        code=code,
        document=document,
        start_line=start_line,
        end_line=end_line,
        imports_context=imports_context,
        tags=tags,
        content_hash=content_hash,
    )


def _format_document(
    *,
    file_path: str,
    language: str,
    imports_context: str,
    symbol: str,
    chunk_type: str,
    code: str,
) -> str:
    header = [
        f"# File: {file_path}",
        f"# Language: {language}",
        f"# Type: {chunk_type}",
        f"# Symbol: {symbol}",
    ]
    if imports_context:
        header.append(f"# Imports:\n{imports_context}")
    return "\n".join(header) + "\n\n" + code


def _format_imports(parsed: ParsedFile) -> str:
    if not parsed.imports:
        return ""
    lines: list[str] = []
    for imp in parsed.imports:
        names = ", ".join(imp.names)
        if imp.module:
            lines.append(f"from {imp.module} import {names}" if names != "*" else f"import {imp.module}")
        else:
            lines.append(f"import {names}")
    return "\n".join(lines)


def _slice_lines(lines: list[str], start: int, end: int) -> str:
    if not lines:
        return ""
    start_idx = max(0, start - 1)
    end_idx = min(len(lines), end)
    return "\n".join(lines[start_idx:end_idx])


class _CoverageTracker:
    def __init__(self, line_count: int) -> None:
        self._lines = [False] * max(line_count, 0)

    def mark(self, start: int, end: int) -> None:
        for i in range(max(0, start - 1), min(len(self._lines), end)):
            self._lines[i] = True

    def uncovered_ranges(self) -> list[tuple[int, int]]:
        ranges: list[tuple[int, int]] = []
        start: int | None = None
        for idx, covered in enumerate(self._lines):
            line_no = idx + 1
            if not covered:
                if start is None:
                    start = line_no
            elif start is not None:
                ranges.append((start, line_no - 1))
                start = None
        if start is not None:
            ranges.append((start, len(self._lines)))
        return ranges


_IMPORT_RE = re.compile(r"^(import |from .+ import |#|//|/\*|\*|$)")


def _is_meaningful_module_block(block: str) -> bool:
    substantive = [ln for ln in block.splitlines() if ln.strip() and not _IMPORT_RE.match(ln.strip())]
    return len(substantive) >= MIN_MODULE_LINES
