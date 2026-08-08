"""Smoke tests for the health endpoint and app factory."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


def _client() -> TestClient:
    settings = Settings(environment="test")
    return TestClient(create_app(settings))


def test_health_returns_ok() -> None:
    with _client() as client:
        response = client.get("/api/v1/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["environment"] == "test"
    assert "X-Request-ID" in response.headers


def test_unknown_route_returns_structured_error() -> None:
    with _client() as client:
        response = client.get("/api/v1/does-not-exist")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "http_error"
