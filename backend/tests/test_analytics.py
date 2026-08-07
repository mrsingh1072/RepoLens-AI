"""Tests for repository analytics computation."""

from __future__ import annotations

from services.analytics.computer import AnalyticsComputer


def _sample_parse() -> dict:
    return {
        "job_id": "job-test",
        "repo_id": "acme/demo",
        "files": [
            {
                "file": "backend/app/main.py",
                "language": "python",
                "classes": [],
                "functions": [
                    {
                        "name": "create_app",
                        "parameters": [],
                        "return_type": None,
                        "start_line": 1,
                        "end_line": 40,
                        "docstring": None,
                        "is_method": False,
                        "class_name": None,
                    },
                    {
                        "name": "unused_helper",
                        "parameters": [],
                        "return_type": None,
                        "start_line": 42,
                        "end_line": 55,
                        "docstring": None,
                        "is_method": False,
                        "class_name": None,
                    },
                ],
                "imports": [{"module": "backend.app.routes", "names": ["router"], "is_external": False, "start_line": 1}],
                "api_endpoints": [{"route": "/health", "method": "GET", "handler": "health", "start_line": 10}],
                "calls": [{"caller": "create_app", "callee": "router", "receiver": None, "start_line": 20, "is_method_call": False}],
                "metadata": {"complexity": "high", "lines": 60, "symbol_count": 2},
            },
            {
                "file": "backend/app/routes.py",
                "language": "python",
                "classes": [
                    {
                        "name": "UserService",
                        "methods": [
                            {
                                "name": "get_user",
                                "parameters": [],
                                "return_type": None,
                                "start_line": 5,
                                "end_line": 18,
                                "docstring": None,
                                "is_method": True,
                                "class_name": "UserService",
                            }
                        ],
                        "bases": [],
                        "implements": [],
                        "attributes": [],
                        "start_line": 1,
                        "end_line": 20,
                        "docstring": None,
                    }
                ],
                "functions": [],
                "imports": [],
                "api_endpoints": [],
                "calls": [],
                "metadata": {"complexity": "medium", "lines": 20, "symbol_count": 1},
            },
            {
                "file": "frontend/src/App.tsx",
                "language": "typescript",
                "classes": [],
                "functions": [
                    {
                        "name": "App",
                        "parameters": [],
                        "return_type": None,
                        "start_line": 1,
                        "end_line": 25,
                        "docstring": None,
                        "is_method": False,
                        "class_name": None,
                    }
                ],
                "imports": [],
                "api_endpoints": [],
                "calls": [],
                "metadata": {"complexity": "low", "lines": 25, "symbol_count": 1},
            },
        ],
        "summary": {"symbol_count": 4, "api_endpoint_count": 1, "chunk_count": 8},
    }


def test_compute_core_metrics():
    result = AnalyticsComputer().compute(_sample_parse())
    assert result.file_count == 3
    assert result.function_count == 4
    assert result.class_count == 1
    assert result.most_complex_file is not None
    assert result.most_complex_file.file_path == "backend/app/main.py"
    assert result.largest_function is not None
    assert result.largest_function.lines >= 14


def test_language_distribution():
    result = AnalyticsComputer().compute(_sample_parse())
    langs = {row["language"]: row for row in result.language_distribution}
    assert "python" in langs
    assert "typescript" in langs
    assert sum(row["percentage"] for row in result.language_distribution) == 100.0


def test_dead_code_estimation():
    result = AnalyticsComputer().compute(_sample_parse())
    dead_names = {symbol.name for symbol in result.dead_code_symbols}
    assert "unused_helper" in dead_names
    assert "create_app" not in dead_names


def test_dependency_graph_present():
    result = AnalyticsComputer().compute(_sample_parse())
    assert result.dependency_graph.nodes
    assert result.dependency_depth >= 0
