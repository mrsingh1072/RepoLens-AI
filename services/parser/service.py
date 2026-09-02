"""Language-aware source parser using Tree-sitter."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from services.parser.chunking import ParsedChunk, chunk_repository, chunks_from_parsed
from services.parser.languages import get_extractor
from services.parser.models import ParsedFile
from services.parser.ts_utils import get_parser, map_extension_to_ts_language, parse_bytes


@dataclass(slots=True)
class ParseSummary:
    """Aggregate statistics from a repository parse run."""

    files_parsed: int
    files_skipped: int
    chunk_count: int
    symbol_count: int
    api_endpoint_count: int


class ParserService:
    """Parse source files into structured semantic units and chunks.

    Uses Tree-sitter grammars via ``tree-sitter-language-pack``. Grammars are
    loaded lazily and cached per process.
    """

    def __init__(self) -> None:
        self._ready = True

    @property
    def is_ready(self) -> bool:
        return self._ready

    def supported_languages(self) -> Sequence[str]:
        return (
            "python",
            "javascript",
            "typescript",
            "tsx",
            "java",
            "go",
            "rust",
            "cpp",
            "c",
            "ruby",
            "php",
            "kotlin",
            "scala",
            "c_sharp",
        )

    def parse_file(
        self,
        path: str | Path,
        *,
        repo_root: Path | None = None,
        language: str | None = None,
    ) -> ParsedFile | None:
        """Parse a single file into structured symbols."""
        file_path = Path(path)
        if not file_path.is_file():
            return None

        source_bytes = file_path.read_bytes()
        rel_path = (
            file_path.relative_to(repo_root).as_posix()
            if repo_root and file_path.is_relative_to(repo_root)
            else file_path.as_posix()
        )
        ext = file_path.suffix.lower()
        language_label = language or ext.lstrip(".") or "unknown"
        ts_language = map_extension_to_ts_language(language_label, ext)

        tree = parse_bytes(ts_language, source_bytes)
        if tree is None:
            return None

        marker = repo_root.name if repo_root else None
        extractor = get_extractor(ts_language)
        return extractor.extract(
            rel_path=rel_path,
            language_label=language_label,
            source=source_bytes,
            root=tree.root_node,
            repo_root_marker=marker,
        )

    def parse_files(
        self,
        files: Sequence[str | Path],
        *,
        repo_root: Path,
        languages: dict[str, str] | None = None,
    ) -> list[ParsedFile]:
        """Parse multiple files under *repo_root*."""
        results: list[ParsedFile] = []
        lang_map = languages or {}
        for item in files:
            path = Path(item)
            if not path.is_absolute():
                path = repo_root / path
            lang = lang_map.get(path.as_posix()) or lang_map.get(path.name)
            parsed = self.parse_file(path, repo_root=repo_root, language=lang)
            if parsed is not None:
                results.append(parsed)
        return results

    def to_chunks(self, parsed: ParsedFile, source: str | None = None) -> list[ParsedChunk]:
        """Convert a :class:`ParsedFile` into semantic chunks."""
        if source is None:
            return []
        return chunks_from_parsed(parsed, source)

    def parse_repository(
        self,
        repo_root: Path,
        file_entries: Sequence[tuple[str, str]],
    ) -> tuple[list[ParsedFile], list[ParsedChunk], ParseSummary]:
        """Parse an entire repository.

        Args:
            repo_root: Root directory of the cloned repository.
            file_entries: ``(relative_path, language_label)`` pairs from scanning.

        Returns:
            Parsed files, semantic chunks, and summary statistics.
        """
        parsed_files: list[ParsedFile] = []
        sources: dict[str, str] = {}
        skipped = 0
        api_count = 0
        symbol_count = 0

        for rel_path, language_label in file_entries:
            abs_path = repo_root / rel_path
            parsed = self.parse_file(abs_path, repo_root=repo_root, language=language_label)
            if parsed is None:
                skipped += 1
                continue
            parsed_files.append(parsed)
            sources[parsed.file] = abs_path.read_text(encoding="utf-8", errors="replace")
            api_count += len(parsed.api_endpoints)
            symbol_count += parsed.metadata.symbol_count

        chunks = chunk_repository(parsed_files, sources)
        summary = ParseSummary(
            files_parsed=len(parsed_files),
            files_skipped=skipped,
            chunk_count=len(chunks),
            symbol_count=symbol_count,
            api_endpoint_count=api_count,
        )
        return parsed_files, chunks, summary

    def warmup(self, languages: Sequence[str] | None = None) -> None:
        """Pre-load grammars to avoid latency on the first parse."""
        for lang in languages or self.supported_languages():
            get_parser(lang)
