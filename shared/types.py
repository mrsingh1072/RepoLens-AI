"""Shared domain types used across the platform."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Language(str, Enum):
    """Programming languages the platform aims to support."""

    PYTHON = "python"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    JAVA = "java"
    GO = "go"
    RUST = "rust"
    CPP = "cpp"
    C = "c"
    UNKNOWN = "unknown"


@dataclass(slots=True, frozen=True)
class RepositoryRef:
    """A stable reference to a GitHub repository at a given revision."""

    owner: str
    name: str
    ref: str = "main"

    @property
    def slug(self) -> str:
        """Return an ``owner/name`` identifier."""
        return f"{self.owner}/{self.name}"

    @property
    def clone_url(self) -> str:
        """Return the HTTPS clone URL for this repository."""
        return f"https://github.com/{self.owner}/{self.name}.git"
