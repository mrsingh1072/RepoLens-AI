"""Repository cloning utilities."""

from __future__ import annotations

import asyncio
import shutil
import subprocess
from pathlib import Path

from app.middleware.error_handler import ValidationError

# 500 MB working tree limit before clone is aborted.
MAX_REPO_SIZE_BYTES = 500 * 1024 * 1024


async def clone_repository(
    clone_url: str,
    destination: Path,
    *,
    branch: str | None = None,
    depth: int = 1,
) -> str:
    """Shallow-clone a repository into *destination*.

    Returns the checked-out commit hash.
    """
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        shutil.rmtree(destination)

    cmd = [
        "git",
        "clone",
        "--depth",
        str(depth),
        "--single-branch",
    ]
    if branch:
        cmd.extend(["--branch", branch])
    cmd.extend([clone_url, str(destination)])

    try:
        proc = await asyncio.to_thread(
            subprocess.run,
            cmd,
            capture_output=True,
            text=True,
            timeout=300,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise ValidationError("Repository clone timed out after 5 minutes.") from exc
    except FileNotFoundError as exc:
        raise ValidationError(
            "Git is not installed or not available on PATH.",
        ) from exc

    if proc.returncode != 0:
        stderr = (proc.stderr or proc.stdout or "").strip()
        message = _friendly_clone_error(stderr)
        raise ValidationError(message, details={"stderr": stderr[:500]})

    commit_hash = await asyncio.to_thread(_resolve_head, destination)
    # Keep .git on disk; the file scanner ignores it and the workspace is
    # deleted after ingestion. Removing .git on Windows often fails with
    # PermissionError on pack files.
    return commit_hash


async def extract_zip_archive(archive_path: Path, destination: Path) -> None:
    """Extract a ZIP archive into *destination*."""
    import zipfile

    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        shutil.rmtree(destination)
    destination.mkdir(parents=True)

    def _extract() -> None:
        with zipfile.ZipFile(archive_path, "r") as zf:
            total_size = sum(info.file_size for info in zf.infolist())
            if total_size > MAX_REPO_SIZE_BYTES:
                raise ValidationError(
                    f"Archive exceeds the {MAX_REPO_SIZE_BYTES // (1024 * 1024)} MB size limit.",
                )
            zf.extractall(destination)

        # If the archive contains a single top-level directory, flatten it.
        children = list(destination.iterdir())
        if len(children) == 1 and children[0].is_dir():
            inner = children[0]
            for item in inner.iterdir():
                shutil.move(str(item), str(destination / item.name))
            inner.rmdir()

    await asyncio.to_thread(_extract)


def _resolve_head(repo_path: Path) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo_path), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()
    lowered = stderr.lower()
    if "authentication failed" in lowered or "could not read username" in lowered:
        return "Authentication failed. Provide a valid GitHub token for private repositories."
    if "repository not found" in lowered:
        return "Repository not found or you do not have access."
    if "remote branch" in lowered and "not found" in lowered:
        return "The default branch could not be found on the remote."
    return "Failed to clone the repository."
