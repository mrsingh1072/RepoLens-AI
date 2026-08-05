"""Persist parsed repository structures to disk."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from services.parser.models import ParsedFile


def save_parse_results(
    output_dir: Path,
    job_id: str,
    parsed_files: list[ParsedFile],
    *,
    extra: dict[str, Any] | None = None,
    owner: str | None = None,
    name: str | None = None,
    repo_id: str | None = None,
) -> Path:
    """Write parsed file structures as JSON for downstream indexing."""
    output_dir.mkdir(parents=True, exist_ok=True)
    payload: dict[str, Any] = {
        "job_id": job_id,
        "files": [pf.to_dict() for pf in parsed_files],
    }
    if owner:
        payload["owner"] = owner
    if name:
        payload["name"] = name
    if repo_id:
        payload["repo_id"] = repo_id
    if extra:
        payload["summary"] = extra
    out_path = output_dir / f"{job_id}.json"
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return out_path


def load_parse_results(output_dir: Path, job_id: str) -> dict[str, Any] | None:
    """Load persisted parse results for an ingestion job."""
    out_path = output_dir / f"{job_id}.json"
    if not out_path.is_file():
        return None
    return json.loads(out_path.read_text(encoding="utf-8"))


def parse_output_dir(workspace_path: Path) -> Path:
    """Return the directory where parse JSON artifacts are stored."""
    return workspace_path.parent / "parsed"
