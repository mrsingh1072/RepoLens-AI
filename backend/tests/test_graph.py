"""Tests for Neo4j code graph builder and query engine."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from services.graph.builder import GraphBuilder
from services.graph.models import RelationshipType
from services.graph.query_engine import GraphQueryEngine
from services.graph.service import GraphNode, GraphService
from services.parser import ParserService


SERVICE_PY = '''\
"""User service module."""
from auth_service import AuthService

class UserController:
    def __init__(self, auth: AuthService):
        self.auth = auth

    def login(self, username: str) -> dict:
        token = self.auth.authenticate(username)
        return {"token": token}

class AuthService:
    def authenticate(self, username: str) -> str:
        return self._issue_token(username)

    def _issue_token(self, username: str) -> str:
        return f"token-{username}"
'''


AUTH_PY = '''\
class JWTService:
    def sign(self, payload: dict) -> str:
        return "signed"
'''


@pytest.fixture
def parser() -> ParserService:
    return ParserService()


class TestGraphBuilder:
    def test_builds_nodes_and_relationships_without_duplicates(self, parser: ParserService, tmp_path: Path) -> None:
        service_path = tmp_path / "user_controller.py"
        auth_path = tmp_path / "auth_service.py"
        service_path.write_text(SERVICE_PY, encoding="utf-8")
        auth_path.write_text(
            'class AuthService:\n    def authenticate(self, user: str) -> str:\n        return "ok"\n',
            encoding="utf-8",
        )

        parsed_service = parser.parse_file(service_path, repo_root=tmp_path)
        parsed_auth = parser.parse_file(auth_path, repo_root=tmp_path)
        assert parsed_service is not None
        assert parsed_auth is not None

        build = GraphBuilder("acme/app").build(
            [parsed_service, parsed_auth],
            {
                "user_controller.py": SERVICE_PY,
                "auth_service.py": auth_path.read_text(encoding="utf-8"),
            },
        )

        node_ids = [node.id for node in build.nodes]
        assert len(node_ids) == len(set(node_ids))
        labels = {node.label for node in build.nodes}
        assert labels >= {"Repository", "File", "Class", "Method"}
        rel_types = {rel.type for rel in build.relationships}
        assert RelationshipType.DEFINES.value in rel_types
        assert RelationshipType.IMPORTS.value in rel_types

    def test_resolves_method_calls(self, parser: ParserService, tmp_path: Path) -> None:
        path = tmp_path / "service.py"
        path.write_text(SERVICE_PY, encoding="utf-8")
        parsed = parser.parse_file(path, repo_root=tmp_path)
        assert parsed is not None
        assert parsed.calls

        build = GraphBuilder("acme/app").build([parsed], {"service.py": SERVICE_PY})
        call_rels = [rel for rel in build.relationships if rel.type == RelationshipType.CALLS.value]
        assert call_rels, "Expected CALLS edges from parsed call sites"

    def test_detects_external_library_imports(self, parser: ParserService, tmp_path: Path) -> None:
        source = 'import fastapi\nfrom pydantic import BaseModel\n\nclass Item(BaseModel):\n    name: str\n'
        path = tmp_path / "models.py"
        path.write_text(source, encoding="utf-8")
        parsed = parser.parse_file(path, repo_root=tmp_path)
        assert parsed is not None

        build = GraphBuilder("acme/app").build([parsed], {"models.py": source})
        labels = {node.label for node in build.nodes}
        assert "ExternalLibrary" in labels
        assert any(rel.type == RelationshipType.IMPORTS.value for rel in build.relationships)


class TestGraphIndexer:
    def test_indexes_via_neo4j_service(self, parser: ParserService, tmp_path: Path) -> None:
        from services.graph.indexer import GraphIndexer

        path = tmp_path / "service.py"
        path.write_text(SERVICE_PY, encoding="utf-8")
        parsed = parser.parse_file(path, repo_root=tmp_path)
        assert parsed is not None

        mock_graph = MagicMock()
        mock_graph.delete_repository.return_value = 0
        mock_graph.__enter__ = MagicMock(return_value=mock_graph)
        mock_graph.__exit__ = MagicMock(return_value=False)

        with patch("services.graph.indexer.GraphService", return_value=mock_graph):
            summary = GraphIndexer(uri="bolt://localhost:7687", user="neo4j", password="pw").index_repository(
                "acme/app",
                [parsed],
                {"service.py": SERVICE_PY},
            )

        assert summary.nodes_written > 0
        assert summary.relationships_written > 0
        mock_graph.delete_repository.assert_called_once_with("acme/app")
        assert mock_graph.upsert_nodes.call_count >= 1


class TestGraphQueryEngine:
    def test_find_dependencies(self) -> None:
        graph = MagicMock(spec=GraphService)
        graph.run.side_effect = [
            [{"id": "Method::acme/app::service.py::UserController.login"}],
            [
                {
                    "id": "Method::acme/app::service.py::AuthService.authenticate",
                    "label": "Method",
                    "name": "authenticate",
                    "file_path": "service.py",
                    "relationship": "CALLS",
                    "depth": 1,
                }
            ],
        ]
        engine = GraphQueryEngine(graph)
        deps = engine.find_dependencies("acme/app", symbol="login")
        assert len(deps) == 1
        assert deps[0].name == "authenticate"
        assert deps[0].relationship == "CALLS"

    def test_trace_call_chain(self) -> None:
        graph = MagicMock(spec=GraphService)
        graph.run.side_effect = [
            [{"id": "Method::acme/app::service.py::UserController.login"}],
            [
                {
                    "nodes": [
                        {"id": "1", "name": "login", "label": "Method", "file_path": "service.py"},
                        {"id": "2", "name": "authenticate", "label": "Method", "file_path": "service.py"},
                    ],
                    "depth": 2,
                }
            ],
        ]
        engine = GraphQueryEngine(graph)
        chains = engine.trace_call_chain("acme/app", symbol="login")
        assert len(chains) == 1
        assert chains[0].depth == 2
        assert len(chains[0].path) == 2

    def test_detect_architecture_layers(self) -> None:
        graph = MagicMock(spec=GraphService)
        graph.run.return_value = [
            {
                "layer": "presentation",
                "file_count": 2,
                "symbol_count": 5,
                "sample_files": ["routes/users.py"],
            }
        ]
        engine = GraphQueryEngine(graph)
        layers = engine.detect_architecture_layers("acme/app")
        assert layers[0].layer == "presentation"
        assert layers[0].file_count == 2


class TestGraphSchema:
    def test_index_statements_use_neo4j5_label_syntax(self) -> None:
        from services.graph.service import _SCHEMA_STATEMENTS

        for statement in _SCHEMA_STATEMENTS:
            if not statement.startswith("CREATE INDEX"):
                continue
            assert "FOR (n:" in statement, f"Index must specify a label: {statement}"
            assert "FOR (n) ON" not in statement, f"Label-less index is invalid in Neo4j 5: {statement}"
