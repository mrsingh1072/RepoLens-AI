"""Tests for architecture diagram generation."""

from __future__ import annotations

from unittest.mock import MagicMock

from services.diagrams.generator import DiagramGenerator
from services.graph.models import ArchitectureLayer


def _engine() -> MagicMock:
    engine = MagicMock()
    engine.detect_architecture_layers.return_value = [
        ArchitectureLayer("presentation", 3, 5, ["backend/app/routes/query.py"]),
        ArchitectureLayer("business", 2, 4, ["services/retrieval/pipeline.py"]),
        ArchitectureLayer("data", 1, 2, ["services/embeddings/chroma_store.py"]),
    ]
    engine.cross_layer_calls.return_value = [
        {
            "source": "ask_repository",
            "source_layer": "presentation",
            "target": "query",
            "target_layer": "business",
            "source_file": "routes/query.py",
            "target_file": "pipeline.py",
        },
    ]
    engine.get_import_graph.return_value = {
        "nodes": [
            {"id": "file:a.py", "path": "a.py", "label": "a.py", "group": "api"},
            {"id": "file:b.py", "path": "b.py", "label": "b.py", "group": "service"},
        ],
        "edges": [{"source": "file:a.py", "target": "file:b.py", "label": "imports"}],
    }
    engine.get_class_structure.return_value = {
        "classes": [{"name": "UserService", "file_path": "services/user.py", "methods": ["get_user"]}],
        "relationships": [{"source": "UserController", "target": "BaseController", "type": "EXTENDS"}],
    }
    engine.list_api_endpoints.return_value = [
        {"route": "/api/v1/query", "method": "POST", "handler": "ask_repository", "file_path": "routes/query.py"},
    ]
    engine.list_database_tables.return_value = [{"name": "users", "file_path": "models/user.py"}]
    engine.repository_stats.return_value = {"File": 10, "Function": 20, "Class": 3}
    engine.trace_call_chain.return_value = []
    return engine


class TestDiagramGenerator:
    def test_generates_mermaid_flowchart(self) -> None:
        bundle = DiagramGenerator(_engine()).generate("owner/repo")
        assert "flowchart TB" in bundle.mermaid.flowchart
        assert "presentation" in bundle.mermaid.flowchart.lower()

    def test_generates_sequence_diagram(self) -> None:
        bundle = DiagramGenerator(_engine()).generate("owner/repo")
        assert "sequenceDiagram" in bundle.mermaid.sequence
        assert "POST" in bundle.mermaid.sequence

    def test_generates_class_diagram(self) -> None:
        bundle = DiagramGenerator(_engine()).generate("owner/repo")
        assert "classDiagram" in bundle.mermaid.class_diagram
        assert "UserService" in bundle.mermaid.class_diagram

    def test_system_architecture_nodes(self) -> None:
        bundle = DiagramGenerator(_engine()).generate("owner/repo")
        nodes = bundle.system_architecture["nodes"]
        assert any(n["kind"] == "backend" for n in nodes)
        assert len(bundle.system_architecture["edges"]) >= 1

    def test_dependency_graph(self) -> None:
        bundle = DiagramGenerator(_engine()).generate("owner/repo")
        assert len(bundle.dependency_graph["nodes"]) == 2
        assert len(bundle.dependency_graph["edges"]) == 1

    def test_mermaid_avoids_invalid_class_stereotype_syntax(self) -> None:
        bundle = DiagramGenerator(_engine()).generate("owner/repo")
        assert "<<" not in bundle.mermaid.class_diagram
        assert '["' in bundle.mermaid.flowchart or "[" in bundle.mermaid.flowchart

    def test_markdown_export(self) -> None:
        bundle = DiagramGenerator(_engine()).generate("owner/repo")
        assert "# Architecture Diagrams" in bundle.markdown
        assert "```mermaid" in bundle.markdown
