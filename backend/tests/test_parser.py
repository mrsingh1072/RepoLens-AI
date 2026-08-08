"""Tests for Tree-sitter parser service."""

from __future__ import annotations

from pathlib import Path

import pytest

from services.parser import ParserService


SAMPLE_PY = '''\
"""Module docstring."""
import os
from fastapi import APIRouter

router = APIRouter()

@router.get("/health")
async def health_check() -> dict:
    """Return service health."""
    return {"status": "ok"}

class UserService:
    """Manage users."""

    def __init__(self, db):
        self.db = db

    def get_user(self, user_id: int) -> dict | None:
        if user_id < 0:
            return None
        return {"id": user_id}
'''


SAMPLE_TS = '''\
import express from "express";

const app = express();

app.get("/api/users", (req, res) => {
  res.json([]);
});

export class UserStore {
  private users: string[] = [];

  add(name: string): void {
    this.users.push(name);
  }
}

export function createStore(): UserStore {
  return new UserStore();
}
'''


@pytest.fixture
def parser() -> ParserService:
    return ParserService()


class TestPythonParser:
    def test_extracts_functions_classes_imports(self, parser: ParserService, tmp_path: Path) -> None:
        path = tmp_path / "api.py"
        path.write_text(SAMPLE_PY, encoding="utf-8")
        result = parser.parse_file(path, repo_root=tmp_path)
        assert result is not None
        assert result.file == "api.py"
        assert len(result.functions) == 1
        assert result.functions[0].name == "health_check"
        assert result.functions[0].return_type == "dict"
        assert result.functions[0].docstring == "Return service health."
        assert len(result.classes) == 1
        assert result.classes[0].name == "UserService"
        assert len(result.classes[0].methods) == 2
        assert len(result.imports) >= 2
        assert len(result.api_endpoints) == 1
        assert result.api_endpoints[0].route == "/health"
        assert result.api_endpoints[0].method == "GET"

    def test_semantic_chunks(self, parser: ParserService, tmp_path: Path) -> None:
        path = tmp_path / "api.py"
        path.write_text(SAMPLE_PY, encoding="utf-8")
        parsed = parser.parse_file(path, repo_root=tmp_path)
        assert parsed is not None
        source = path.read_text(encoding="utf-8")
        chunks = parser.to_chunks(parsed, source)
        assert len(chunks) >= 3  # health_check + 2 methods
        assert all(c.start_line > 0 for c in chunks)
        assert all(c.content for c in chunks)
        symbols = {c.symbol for c in chunks}
        assert "health_check" in symbols
        assert "UserService.get_user" in symbols

    def test_output_structure(self, parser: ParserService, tmp_path: Path) -> None:
        path = tmp_path / "api.py"
        path.write_text(SAMPLE_PY, encoding="utf-8")
        parsed = parser.parse_file(path, repo_root=tmp_path)
        assert parsed is not None
        data = parsed.to_dict()
        assert data["file"] == "api.py"
        assert "classes" in data
        assert "functions" in data
        assert "imports" in data
        assert "metadata" in data
        assert data["metadata"]["lines"] > 0
        assert data["metadata"]["complexity"] in {"low", "medium", "high"}


class TestJavaScriptParser:
    def test_extracts_express_routes(self, parser: ParserService, tmp_path: Path) -> None:
        path = tmp_path / "server.ts"
        path.write_text(SAMPLE_TS, encoding="utf-8")
        result = parser.parse_file(path, repo_root=tmp_path, language="typescript")
        assert result is not None
        assert len(result.api_endpoints) >= 1
        assert result.api_endpoints[0].route == "/api/users"
        assert len(result.classes) == 1
        assert len(result.functions) >= 1
