"""File filtering for repository ingestion."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

IGNORED_DIR_NAMES = frozenset(
    {
        "node_modules",
        "dist",
        "build",
        "venv",
        ".venv",
        "env",
        ".env",
        ".next",
        ".git",
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".tox",
        "target",
        "vendor",
        ".idea",
        ".vscode",
        "coverage",
        ".nyc_output",
    }
)

CODE_EXTENSIONS = frozenset(
    {
        ".py",
        ".js",
        ".jsx",
        ".ts",
        ".tsx",
        ".mjs",
        ".cjs",
        ".java",
        ".kt",
        ".kts",
        ".scala",
        ".groovy",
        ".cpp",
        ".cc",
        ".cxx",
        ".c",
        ".h",
        ".hpp",
        ".hh",
        ".go",
        ".rs",
        ".rb",
        ".php",
        ".swift",
        ".cs",
        ".fs",
        ".vb",
        ".vue",
        ".svelte",
        ".lua",
        ".r",
        ".R",
        ".sql",
        ".sh",
        ".bash",
        ".zsh",
        ".ps1",
        ".dart",
        ".ex",
        ".exs",
        ".erl",
        ".hrl",
        ".clj",
        ".cljs",
        ".hs",
        ".ml",
        ".mli",
        ".toml",
        ".yaml",
        ".yml",
        ".json",
        ".md",
        ".rst",
    }
)

EXTENSION_TO_LANGUAGE: dict[str, str] = {
    ".py": "Python",
    ".js": "JavaScript",
    ".jsx": "JavaScript",
    ".mjs": "JavaScript",
    ".cjs": "JavaScript",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".java": "Java",
    ".kt": "Kotlin",
    ".kts": "Kotlin",
    ".scala": "Scala",
    ".groovy": "Groovy",
    ".cpp": "C++",
    ".cc": "C++",
    ".cxx": "C++",
    ".c": "C",
    ".h": "C",
    ".hpp": "C++",
    ".hh": "C++",
    ".go": "Go",
    ".rs": "Rust",
    ".rb": "Ruby",
    ".php": "PHP",
    ".swift": "Swift",
    ".cs": "C#",
    ".fs": "F#",
    ".vb": "Visual Basic",
    ".vue": "Vue",
    ".svelte": "Svelte",
    ".lua": "Lua",
    ".r": "R",
    ".R": "R",
    ".sql": "SQL",
    ".sh": "Shell",
    ".bash": "Shell",
    ".zsh": "Shell",
    ".ps1": "PowerShell",
    ".dart": "Dart",
    ".ex": "Elixir",
    ".exs": "Elixir",
    ".erl": "Erlang",
    ".hrl": "Erlang",
    ".clj": "Clojure",
    ".cljs": "Clojure",
    ".hs": "Haskell",
    ".ml": "OCaml",
    ".mli": "OCaml",
}


@dataclass(slots=True)
class ScannedFile:
    """A code file discovered during repository scanning."""

    path: str
    extension: str
    language: str
    size_bytes: int


@dataclass(slots=True)
class ScanResult:
    """Aggregated scan output for a repository working tree."""

    files: list[ScannedFile]
    total_size_bytes: int
    languages: dict[str, int]

    @property
    def file_count(self) -> int:
        return len(self.files)

    @property
    def primary_language(self) -> str:
        if not self.languages:
            return "Unknown"
        return max(self.languages, key=self.languages.get)  # type: ignore[arg-type]

    def language_percentages(self) -> dict[str, float]:
        total = sum(self.languages.values()) or 1
        return {lang: round(count / total * 100, 1) for lang, count in self.languages.items()}


def should_skip_dir(dir_name: str) -> bool:
    return dir_name in IGNORED_DIR_NAMES


def is_code_file(path: Path) -> bool:
    return path.suffix.lower() in CODE_EXTENSIONS


def scan_repository(root: Path) -> ScanResult:
    """Walk *root* and collect code files, skipping ignored directories."""
    files: list[ScannedFile] = []
    languages: dict[str, int] = {}
    total_size = 0

    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if any(should_skip_dir(part) for part in path.relative_to(root).parts[:-1]):
            continue
        if not is_code_file(path):
            continue

        ext = path.suffix.lower()
        language = EXTENSION_TO_LANGUAGE.get(ext, "Other")
        rel_path = path.relative_to(root).as_posix()
        size = path.stat().st_size
        files.append(ScannedFile(path=rel_path, extension=ext, language=language, size_bytes=size))
        languages[language] = languages.get(language, 0) + 1
        total_size += size

    files.sort(key=lambda f: f.path)
    return ScanResult(files=files, total_size_bytes=total_size, languages=languages)
