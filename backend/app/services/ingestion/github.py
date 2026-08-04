"""GitHub URL validation and metadata fetching."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

import httpx

from app.middleware.error_handler import NotFoundError, ValidationError

GITHUB_URL_RE = re.compile(
    r"^(?:https?://)?(?:www\.)?github\.com/([\w.-]+)/([\w.-]+?)(?:\.git)?/?$",
    re.IGNORECASE,
)

GITHUB_API_BASE = "https://api.github.com"


@dataclass(slots=True, frozen=True)
class ParsedGitHubUrl:
    """Owner and repository name extracted from a GitHub URL."""

    owner: str
    name: str

    @property
    def slug(self) -> str:
        return f"{self.owner}/{self.name}"

    @property
    def clone_url(self) -> str:
        return f"https://github.com/{self.owner}/{self.name}.git"


@dataclass(slots=True)
class GitHubRepoMetadata:
    """Repository metadata returned by the GitHub REST API."""

    owner: str
    name: str
    full_name: str
    description: str | None
    default_branch: str
    stars: int
    forks: int
    language: str | None
    size_kb: int
    is_private: bool
    clone_url: str


def parse_github_url(url: str) -> ParsedGitHubUrl:
    """Validate and parse a GitHub repository URL."""
    cleaned = url.strip().rstrip("/")
    match = GITHUB_URL_RE.match(cleaned)
    if not match:
        raise ValidationError(
            "Invalid GitHub URL. Expected format: github.com/owner/repository",
            details={"url": url},
        )
    owner, name = match.group(1), match.group(2)
    if name.endswith(".git"):
        name = name[:-4]
    return ParsedGitHubUrl(owner=owner, name=name)


def _auth_headers(token: str | None) -> dict[str, str]:
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


async def fetch_repo_metadata(
    parsed: ParsedGitHubUrl,
    *,
    token: str | None = None,
    timeout: float = 30.0,
) -> GitHubRepoMetadata:
    """Fetch repository metadata from the GitHub REST API."""
    url = f"{GITHUB_API_BASE}/repos/{parsed.owner}/{parsed.name}"
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.get(url, headers=_auth_headers(token))

    if response.status_code == 404:
        raise NotFoundError(
            f"Repository '{parsed.slug}' was not found. "
            "Check the URL or provide a token for private repositories.",
        )
    if response.status_code == 401:
        raise ValidationError("Invalid GitHub token.")
    if response.status_code == 403:
        detail = _extract_rate_limit_message(response)
        raise ValidationError(detail)
    if response.status_code != 200:
        raise ValidationError(
            f"GitHub API returned status {response.status_code}.",
            details={"status_code": response.status_code},
        )

    data: dict[str, Any] = response.json()
    return GitHubRepoMetadata(
        owner=data["owner"]["login"],
        name=data["name"],
        full_name=data["full_name"],
        description=data.get("description"),
        default_branch=data.get("default_branch", "main"),
        stars=data.get("stargazers_count", 0),
        forks=data.get("forks_count", 0),
        language=data.get("language"),
        size_kb=data.get("size", 0),
        is_private=data.get("private", False),
        clone_url=data.get("clone_url", parsed.clone_url),
    )


def build_clone_url(clone_url: str, token: str | None) -> str:
    """Return a clone URL, embedding the token for private repository access."""
    if not token:
        return clone_url
    if clone_url.startswith("https://github.com/"):
        return clone_url.replace("https://", f"https://oauth2:{token}@", 1)
    return clone_url


def _extract_rate_limit_message(response: httpx.Response) -> str:
    try:
        body = response.json()
        message = body.get("message", "")
        if "rate limit" in message.lower():
            return "GitHub API rate limit exceeded. Try again later or provide a token."
        return message or "Access to this repository was denied."
    except Exception:
        return "Access to this repository was denied."
