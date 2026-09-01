"""Semantic chunking at function/class boundaries."""

from __future__ import annotations

from dataclasses import dataclass

from services.parser.models import ParsedClass, ParsedFile, ParsedFunction


@dataclass(slots=True)
class ParsedChunk:
    """A single semantically-meaningful unit extracted from a source file."""

    file_path: str
    language: str
    symbol: str | None
    start_line: int
    end_line: int
    content: str
    kind: str  # "function" | "method" | "class"


def chunks_from_parsed(parsed: ParsedFile, source: str) -> list[ParsedChunk]:
    """Split *source* into semantic chunks using parsed symbol line ranges."""
    lines = source.splitlines()
    chunks: list[ParsedChunk] = []

    def slice_lines(start: int, end: int) -> str:
        if not lines:
            return ""
        start_idx = max(0, start - 1)
        end_idx = min(len(lines), end)
        return "\n".join(lines[start_idx:end_idx])

    for fn in parsed.functions:
        chunks.append(
            ParsedChunk(
                file_path=parsed.file,
                language=parsed.language,
                symbol=fn.name,
                start_line=fn.start_line,
                end_line=fn.end_line,
                content=slice_lines(fn.start_line, fn.end_line),
                kind="function",
            )
        )

    for cls in parsed.classes:
        if cls.methods:
            for method in cls.methods:
                symbol = f"{cls.name}.{method.name}"
                chunks.append(
                    ParsedChunk(
                        file_path=parsed.file,
                        language=parsed.language,
                        symbol=symbol,
                        start_line=method.start_line,
                        end_line=method.end_line,
                        content=slice_lines(method.start_line, method.end_line),
                        kind="method",
                    )
                )
        else:
            chunks.append(
                ParsedChunk(
                    file_path=parsed.file,
                    language=parsed.language,
                    symbol=cls.name,
                    start_line=cls.start_line,
                    end_line=cls.end_line,
                    content=slice_lines(cls.start_line, cls.end_line),
                    kind="class",
                )
            )

    return chunks


def chunk_repository(parsed_files: list[ParsedFile], sources: dict[str, str]) -> list[ParsedChunk]:
    """Build chunks for many files."""
    all_chunks: list[ParsedChunk] = []
    for parsed in parsed_files:
        source = sources.get(parsed.file, "")
        all_chunks.extend(chunks_from_parsed(parsed, source))
    return all_chunks
