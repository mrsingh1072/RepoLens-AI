"""Tests for repository ingestion."""

from __future__ import annotations

import io
import zipfile
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from app.services.ingestion.filter import scan_repository
from app.services.ingestion.github import parse_github_url


def _client() -> TestClient:
    settings = Settings(environment="test", ingestion_workspace_dir="data/test-ingestion")
    return TestClient(create_app(settings))


class TestGitHubUrlParsing:
    def test_full_https_url(self) -> None:
        parsed = parse_github_url("https://github.com/facebook/react")
        assert parsed.owner == "facebook"
        assert parsed.name == "react"

    def test_short_url(self) -> None:
        parsed = parse_github_url("github.com/torvalds/linux")
        assert parsed.slug == "torvalds/linux"

    def test_git_suffix(self) -> None:
        parsed = parse_github_url("https://github.com/owner/repo.git")
        assert parsed.name == "repo"

    def test_invalid_url_raises(self) -> None:
        with pytest.raises(Exception) as exc:
            parse_github_url("https://gitlab.com/owner/repo")
        assert "Invalid GitHub URL" in str(exc.value)


class TestFileFilter:
    def test_scan_filters_ignored_dirs(self, tmp_path: Path) -> None:
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "main.py").write_text("print('hi')")
        (tmp_path / "node_modules").mkdir()
        (tmp_path / "node_modules" / "pkg.js").write_text("module.exports = {}")
        (tmp_path / "dist").mkdir()
        (tmp_path / "dist" / "bundle.js").write_text("bundled")

        result = scan_repository(tmp_path)
        assert result.file_count == 1
        assert result.files[0].path == "src/main.py"
        assert result.primary_language == "Python"


class TestIngestionApi:
    def test_github_ingestion_returns_job_id(self) -> None:
        client = _client()
        with patch(
            "app.services.ingestion.pipeline.IngestionPipeline.start_github_ingestion",
            new_callable=AsyncMock,
        ) as mock_start:
            from app.services.ingestion.store import IngestionJob

            mock_start.return_value = IngestionJob(
                id="job-test123",
                source="github",
                owner="octocat",
                name="Hello-World",
            )
            response = client.post(
                "/api/v1/ingestion/github",
                json={"url": "https://github.com/octocat/Hello-World"},
            )

        assert response.status_code == 202
        assert response.json()["job_id"] == "job-test123"

    def test_zip_upload_requires_zip_extension(self) -> None:
        client = _client()
        response = client.post(
            "/api/v1/ingestion/upload",
            files={"file": ("archive.tar.gz", b"data", "application/gzip")},
            data={"name": "my-repo"},
        )
        assert response.status_code == 422
        body = response.json()
        assert body["error"]["code"] == "validation_error"

    def test_get_unknown_job_returns_404(self) -> None:
        client = _client()
        response = client.get("/api/v1/ingestion/job-nonexistent")
        assert response.status_code == 404

    def test_get_parse_results_not_found(self) -> None:
        client = _client()
        response = client.get("/api/v1/ingestion/job-nonexistent/parse")
        assert response.status_code == 404


class TestZipExtraction:
    def test_extract_flatten_single_root(self, tmp_path: Path) -> None:
        import asyncio

        from app.services.ingestion.clone import extract_zip_archive

        archive = tmp_path / "repo.zip"
        dest = tmp_path / "extracted"
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("my-repo/src/app.py", "x = 1")
        archive.write_bytes(buf.getvalue())

        asyncio.run(extract_zip_archive(archive, dest))
        assert (dest / "src" / "app.py").exists()
