"""Resolve parse artifacts for a repository."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def parse_output_dir(workspace_path: Path) -> Path:
    return workspace_path.parent / "parsed"


def resolve_parse_data(workspace_path: Path, repo_or_job_id: str) -> dict[str, Any] | None:
    """Load parse JSON by job id or repository slug (owner/name)."""
    parse_dir = parse_output_dir(workspace_path)
    if not parse_dir.is_dir():
        return None

    candidate = parse_dir / f"{repo_or_job_id}.json"
    if candidate.is_file():
        return json.loads(candidate.read_text(encoding="utf-8"))

    for path in sorted(parse_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        data = json.loads(path.read_text(encoding="utf-8"))
        repo_id = data.get("repo_id")
        if isinstance(repo_id, str) and repo_id == repo_or_job_id:
            return data
        owner = data.get("owner")
        name = data.get("name")
        if owner and name and f"{owner}/{name}" == repo_or_job_id:
            return data
    return None
