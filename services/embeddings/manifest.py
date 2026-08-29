"""Incremental indexing manifest for repository embeddings."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class RepoManifest:
    """Tracks per-file content hashes for incremental re-indexing."""

    repo_id: str
    files: dict[str, str] = field(default_factory=dict)
    chunk_ids: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "repo_id": self.repo_id,
            "files": self.files,
            "chunk_ids": self.chunk_ids,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RepoManifest:
        return cls(
            repo_id=data.get("repo_id", ""),
            files=dict(data.get("files", {})),
            chunk_ids=list(data.get("chunk_ids", [])),
        )


def manifest_path(manifest_dir: Path, repo_id: str) -> Path:
    safe_id = repo_id.replace("/", "__").replace("\\", "__")
    return manifest_dir / f"{safe_id}.json"


def load_manifest(manifest_dir: Path, repo_id: str) -> RepoManifest | None:
    path = manifest_path(manifest_dir, repo_id)
    if not path.is_file():
        return None
    return RepoManifest.from_dict(json.loads(path.read_text(encoding="utf-8")))


def save_manifest(manifest_dir: Path, manifest: RepoManifest) -> Path:
    manifest_dir.mkdir(parents=True, exist_ok=True)
    path = manifest_path(manifest_dir, manifest.repo_id)
    path.write_text(json.dumps(manifest.to_dict(), indent=2), encoding="utf-8")
    return path


def diff_files(
    previous: dict[str, str],
    current: dict[str, str],
) -> tuple[set[str], set[str], set[str]]:
    """Return ``(unchanged, changed, removed)`` file path sets."""
    prev_keys = set(previous)
    curr_keys = set(current)
    removed = prev_keys - curr_keys
    added = curr_keys - prev_keys
    common = prev_keys & curr_keys
    changed = {path for path in common if previous[path] != current[path]}
    changed |= added
    unchanged = common - changed
    return unchanged, changed, removed
