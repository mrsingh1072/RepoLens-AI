"""Tests for semantic embedding pipeline."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from services.embeddings.manifest import RepoManifest, diff_files, load_manifest, save_manifest
from services.embeddings.models import SemanticChunk
from services.embeddings.semantic_chunks import build_semantic_chunks, chunk_content_hash, file_content_hash
from services.parser.models import FileMetadata, ParsedClass, ParsedFile, ParsedFunction, ParsedImport, Parameter


SAMPLE_SOURCE = '''\
"""Service module."""
import os
from fastapi import APIRouter

router = APIRouter()
CONFIG = {"debug": True}

def top_level_helper(value: int) -> int:
    """Double a value."""
    return value * 2

class UserService:
    """User operations."""

    def get(self, user_id: int) -> dict:
        return {"id": user_id}

    def delete(self, user_id: int) -> None:
        if user_id < 0:
            raise ValueError("bad id")
'''


def _parsed_file() -> ParsedFile:
    return ParsedFile(
        file="app/service.py",
        language="Python",
        imports=[
            ParsedImport(module="os", names=["os"], is_external=True, start_line=2),
            ParsedImport(module="fastapi", names=["APIRouter"], is_external=True, start_line=3),
        ],
        functions=[
            ParsedFunction(
                name="top_level_helper",
                parameters=[Parameter(name="value", type="int")],
                return_type="int",
                start_line=9,
                end_line=11,
                docstring="Double a value.",
            )
        ],
        classes=[
            ParsedClass(
                name="UserService",
                methods=[
                    ParsedFunction(
                        name="get",
                        parameters=[Parameter(name="user_id", type="int")],
                        return_type="dict",
                        start_line=16,
                        end_line=17,
                        is_method=True,
                        class_name="UserService",
                    ),
                    ParsedFunction(
                        name="delete",
                        parameters=[Parameter(name="user_id", type="int")],
                        return_type="None",
                        start_line=19,
                        end_line=21,
                        is_method=True,
                        class_name="UserService",
                    ),
                ],
                bases=[],
                attributes=[],
                start_line=13,
                end_line=21,
                docstring="User operations.",
            )
        ],
        metadata=FileMetadata(complexity="low", lines=22, symbol_count=3),
    )


class TestSemanticChunks:
    def test_builds_function_method_and_module_chunks(self) -> None:
        parsed = _parsed_file()
        # Large threshold forces per-method chunks instead of whole-class chunk.
        chunks = build_semantic_chunks(parsed, SAMPLE_SOURCE, repo_id="acme/app", class_line_threshold=5)
        types = {c.chunk_type for c in chunks}
        assert "function" in types
        assert "method" in types
        assert "module" in types

    def test_chunks_include_imports_context(self) -> None:
        parsed = _parsed_file()
        chunks = build_semantic_chunks(parsed, SAMPLE_SOURCE, repo_id="acme/app")
        assert all("fastapi" in c.imports_context for c in chunks)
        assert all(c.document.startswith("# File:") for c in chunks)

    def test_content_hash_is_stable(self) -> None:
        h1 = chunk_content_hash("repo", "f.py", "fn", "code", 1)
        h2 = chunk_content_hash("repo", "f.py", "fn", "code", 1)
        assert h1 == h2
        assert h1 != chunk_content_hash("repo", "f.py", "fn", "code2", 1)

    def test_small_class_becomes_single_chunk(self) -> None:
        parsed = _parsed_file()
        chunks = build_semantic_chunks(parsed, SAMPLE_SOURCE, repo_id="acme/app", class_line_threshold=80)
        class_chunks = [c for c in chunks if c.chunk_type == "class"]
        method_chunks = [c for c in chunks if c.chunk_type == "method"]
        assert len(class_chunks) == 1
        assert len(method_chunks) == 0


class TestManifest:
    def test_diff_detects_changed_and_removed_files(self) -> None:
        prev = {"a.py": "hash1", "b.py": "hash2"}
        curr = {"a.py": "hash1", "b.py": "hash3", "c.py": "hash4"}
        unchanged, changed, removed = diff_files(prev, curr)
        assert unchanged == {"a.py"}
        assert changed == {"b.py", "c.py"}
        assert removed == set()

    def test_save_and_load_manifest(self, tmp_path: Path) -> None:
        manifest = RepoManifest(repo_id="acme/app", files={"main.py": "abc"}, chunk_ids=["id1"])
        save_manifest(tmp_path, manifest)
        loaded = load_manifest(tmp_path, "acme/app")
        assert loaded is not None
        assert loaded.files["main.py"] == "abc"


class TestEmbeddingIndexer:
    def test_incremental_index_skips_unchanged(self, tmp_path: Path) -> None:
        from services.embeddings.indexer import EmbeddingIndexer

        parsed = _parsed_file()
        sources = {"app/service.py": SAMPLE_SOURCE}
        manifest_dir = tmp_path / "manifests"
        chroma_path = tmp_path / "chroma"

        mock_provider = MagicMock()
        mock_provider.name = "openai"
        mock_provider.dimension = 3
        mock_provider.embed_texts.side_effect = lambda texts: [[0.1, 0.2, 0.3] for _ in texts]

        with patch("services.embeddings.indexer.create_embedding_provider", return_value=mock_provider):
            indexer = EmbeddingIndexer(
                provider_name="openai",
                openai_api_key="test-key",
                chroma_persistent_path=chroma_path,
                manifest_dir=manifest_dir,
                batch_size=16,
            )
            summary1 = indexer.index_repository("acme/app", [parsed], sources)
            assert summary1.chunks_indexed > 0
            assert mock_provider.embed_texts.call_count >= 1

            calls_after_first = mock_provider.embed_texts.call_count
            summary2 = indexer.index_repository("acme/app", [parsed], sources)
            assert summary2.chunks_indexed == 0
            assert summary2.chunks_embedded > 0
            assert summary2.files_unchanged == 1
            assert mock_provider.embed_texts.call_count == calls_after_first

    def test_failed_batch_does_not_abort_and_resumes_next_run(self, tmp_path: Path) -> None:
        from services.embeddings.indexer import EmbeddingIndexer

        parsed = _parsed_file()
        sources = {"app/service.py": SAMPLE_SOURCE}
        manifest_dir = tmp_path / "manifests"
        chroma_path = tmp_path / "chroma"

        call_count = {"n": 0}

        def embed_side_effect(texts: list[str]) -> list[list[float]]:
            call_count["n"] += 1
            # First run's batch fails permanently; later runs succeed.
            if call_count["n"] == 1:
                raise RuntimeError("jina batch failed after 3 attempts")
            return [[0.1, 0.2, 0.3] for _ in texts]

        mock_provider = MagicMock()
        mock_provider.name = "jina"
        mock_provider.embed_texts.side_effect = embed_side_effect

        with patch("services.embeddings.indexer.create_embedding_provider", return_value=mock_provider):
            indexer = EmbeddingIndexer(
                provider_name="jina",
                jina_api_key="test-key",
                chroma_persistent_path=chroma_path,
                manifest_dir=manifest_dir,
                batch_size=64,
            )
            # Failing batch must NOT raise — indexing continues and reports failures.
            summary1 = indexer.index_repository("acme/app", [parsed], sources)
            assert summary1.chunks_indexed == 0
            assert summary1.chunks_failed > 0

            # A subsequent run re-embeds the chunks that failed before.
            summary2 = indexer.index_repository("acme/app", [parsed], sources)
            assert summary2.chunks_indexed > 0
            assert summary2.chunks_embedded == summary2.chunks_total

    def test_changed_file_triggers_reindex(self, tmp_path: Path) -> None:
        from services.embeddings.indexer import EmbeddingIndexer

        parsed = _parsed_file()
        sources_v1 = {"app/service.py": SAMPLE_SOURCE}
        sources_v2 = {"app/service.py": SAMPLE_SOURCE + "\n# changed\n"}
        manifest_dir = tmp_path / "manifests"
        chroma_path = tmp_path / "chroma"

        mock_provider = MagicMock()
        mock_provider.name = "openai"
        mock_provider.dimension = 3
        mock_provider.embed_texts.side_effect = lambda texts: [[0.1, 0.2, 0.3] for _ in texts]

        with patch("services.embeddings.indexer.create_embedding_provider", return_value=mock_provider):
            indexer = EmbeddingIndexer(
                provider_name="openai",
                openai_api_key="test-key",
                chroma_persistent_path=chroma_path,
                manifest_dir=manifest_dir,
            )
            indexer.index_repository("acme/app", [parsed], sources_v1)
            first_calls = mock_provider.embed_texts.call_count
            summary = indexer.index_repository("acme/app", [parsed], sources_v2)
            assert summary.files_changed == 1
            assert mock_provider.embed_texts.call_count > first_calls

    def test_dimension_mismatch_purges_stale_vectors(self, tmp_path: Path) -> None:
        from services.embeddings.indexer import EmbeddingIndexer

        parsed = _parsed_file()
        sources = {"app/service.py": SAMPLE_SOURCE}
        manifest_dir = tmp_path / "manifests"
        chroma_path = tmp_path / "chroma"

        mock_provider = MagicMock()
        mock_provider.name = "jina"
        mock_provider.dimension = 1024
        mock_provider.embed_texts.side_effect = lambda texts: [[0.1] * 1024 for _ in texts]

        with patch("services.embeddings.indexer.create_embedding_provider", return_value=mock_provider):
            indexer = EmbeddingIndexer(
                provider_name="jina",
                jina_api_key="test-key",
                chroma_persistent_path=chroma_path,
                manifest_dir=manifest_dir,
            )
            summary1 = indexer.index_repository("acme/app", [parsed], sources)
            assert summary1.chunks_indexed > 0

            mock_provider.dimension = 3072
            mock_provider.embed_texts.side_effect = lambda texts: [[0.2] * 3072 for _ in texts]
            summary2 = indexer.index_repository("acme/app", [parsed], sources)
            assert summary2.chunks_indexed > 0
            assert summary2.chunks_skipped == 0
            assert mock_provider.embed_texts.call_count >= 2


class TestJinaEmbeddingService:
    @staticmethod
    def _fake_response(vectors: list[list[float]]) -> MagicMock:
        response = MagicMock()
        response.status_code = 200
        response.raise_for_status = MagicMock()
        response.json.return_value = {
            "data": [{"index": i, "embedding": vec} for i, vec in enumerate(vectors)],
        }
        return response

    def test_requires_api_key(self) -> None:
        from services.embeddings.embedding_service import JinaEmbeddingError, JinaEmbeddingService

        with pytest.raises(JinaEmbeddingError):
            JinaEmbeddingService("")

    def test_embed_texts_batches_and_orders(self) -> None:
        from services.embeddings.embedding_service import JinaEmbeddingService

        session = MagicMock()
        captured_payloads: list[dict] = []

        def post(url: str, json: dict) -> MagicMock:
            captured_payloads.append(json)
            n = len(json["input"])
            # Return out-of-order to verify the service re-sorts by index.
            vecs = [[float(i)] * 3 for i in range(n)]
            resp = MagicMock()
            resp.status_code = 200
            resp.raise_for_status = MagicMock()
            resp.json.return_value = {
                "data": list(reversed([{"index": i, "embedding": v} for i, v in enumerate(vecs)])),
            }
            return resp

        session.post.side_effect = post
        service = JinaEmbeddingService("key", batch_size=2, session=session)

        vectors = service.embed_texts(["a", "b", "c"])
        assert len(vectors) == 3
        assert vectors[0] == [0.0, 0.0, 0.0]
        assert session.post.call_count == 2  # batch sizes 2 + 1
        assert all(payload.get("truncate") is True for payload in captured_payloads)

    def test_embed_text_single(self) -> None:
        from services.embeddings.embedding_service import JinaEmbeddingService

        session = MagicMock()
        session.post.return_value = self._fake_response([[0.1, 0.2, 0.3]])
        service = JinaEmbeddingService("key", session=session)

        assert service.embed_text("hello") == [0.1, 0.2, 0.3]

    def test_retries_then_succeeds(self) -> None:
        from services.embeddings.embedding_service import JinaEmbeddingService

        session = MagicMock()
        calls = {"n": 0}

        def post(url: str, json: dict) -> MagicMock:
            calls["n"] += 1
            if calls["n"] == 1:
                raise RuntimeError("transient 500")
            resp = self._fake_response([[0.5, 0.5, 0.5]])
            return resp

        session.post.side_effect = post
        with patch("services.embeddings.embedding_service.time.sleep"):
            service = JinaEmbeddingService("key", max_retries=3, session=session)
            vectors = service.embed_texts(["a"])

        assert vectors == [[0.5, 0.5, 0.5]]
        assert calls["n"] == 2

    def test_raises_after_max_retries(self) -> None:
        from services.embeddings.embedding_service import JinaEmbeddingError, JinaEmbeddingService

        session = MagicMock()
        session.post.side_effect = RuntimeError("boom")
        with patch("services.embeddings.embedding_service.time.sleep"):
            service = JinaEmbeddingService("key", max_retries=2, session=session)
            with pytest.raises(JinaEmbeddingError):
                service.embed_texts(["a"])


class TestChromaMetadata:
    def test_chunk_maps_to_schema(self) -> None:
        from services.embeddings.chroma_store import _chroma_metadata

        chunk = SemanticChunk(
            repo_id="acme/app",
            file_path="main.py",
            language="Python",
            chunk_type="function",
            class_name=None,
            function_name="main",
            symbol="main",
            code="def main(): pass",
            document="# doc",
            start_line=1,
            end_line=1,
            imports_context="import os",
            tags=["function"],
            content_hash=chunk_content_hash("acme/app", "main.py", "main", "def main(): pass", 1),
        )
        meta = _chroma_metadata(chunk)
        assert meta["repo_id"] == "acme/app"
        assert meta["file"] == "main.py"
        assert meta["function"] == "main"
        assert meta["type"] == "function"
        assert meta["language"] == "Python"
