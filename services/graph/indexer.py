"""Index parsed repositories into Neo4j."""

from __future__ import annotations

import logging

from services.graph.builder import GraphBuilder
from services.graph.models import GraphIndexSummary
from services.graph.service import GraphService
from services.parser.models import ParsedFile

logger = logging.getLogger(__name__)

_BATCH_SIZE = 200


class GraphIndexer:
    """Build and persist a repository code graph in Neo4j."""

    def __init__(
        self,
        *,
        uri: str,
        user: str,
        password: str,
    ) -> None:
        self._uri = uri
        self._user = user
        self._password = password

    def index_repository(
        self,
        repo_id: str,
        parsed_files: list[ParsedFile],
        sources: dict[str, str] | None = None,
    ) -> GraphIndexSummary:
        """Build the graph from parse output and upsert into Neo4j."""
        builder = GraphBuilder(repo_id)
        build = builder.build(parsed_files, sources)

        with GraphService(self._uri, self._user, self._password) as graph:
            deleted = graph.delete_repository(repo_id)
            logger.info(
                "Graph indexing repo=%s nodes=%d relationships=%d (removed %d stale nodes)",
                repo_id,
                build.node_count,
                build.relationship_count,
                deleted,
            )

            for start in range(0, len(build.nodes), _BATCH_SIZE):
                graph.upsert_nodes(build.nodes[start : start + _BATCH_SIZE])

            for start in range(0, len(build.relationships), _BATCH_SIZE):
                graph.upsert_relationships(build.relationships[start : start + _BATCH_SIZE])

        return GraphIndexSummary(
            repo_id=repo_id,
            nodes_written=build.node_count,
            relationships_written=build.relationship_count,
            nodes_deleted=deleted,
        )
