"""Tests for ingestion job deletion."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    from app.core.config import get_settings

    get_settings.cache_clear()
    monkeypatch.setenv("INGESTION_WORKSPACE_DIR", str(tmp_path / "ingestion"))
    monkeypatch.setenv("NEO4J_ENABLED", "false")
    monkeypatch.setenv("JINA_API_KEY", "test-key")
    app = create_app()
    return TestClient(app)


def test_delete_ingestion_job_not_found(client: TestClient) -> None:
    response = client.delete("/api/v1/ingestion/job-missing")
    assert response.status_code == 404


def test_delete_ingestion_job_removes_artifacts(client: TestClient, tmp_path: Path) -> None:
    workspace = tmp_path / "ingestion"
    job_id = "job-deadbeef"
    parsed_dir = workspace.parent / "parsed"
    parsed_dir.mkdir(parents=True)
    payload = {
        "job_id": job_id,
        "repo_id": "acme/demo",
        "owner": "acme",
        "name": "demo",
        "files": [],
        "summary": {},
    }
    (parsed_dir / f"{job_id}.json").write_text(json.dumps(payload), encoding="utf-8")

    response = client.delete(f"/api/v1/ingestion/{job_id}")
    assert response.status_code == 200
    body = response.json()
    assert body["job_id"] == job_id
    assert body["repo_id"] == "acme/demo"
    assert body["deleted"]["parse_artifact"] is True
    assert not (parsed_dir / f"{job_id}.json").exists()
