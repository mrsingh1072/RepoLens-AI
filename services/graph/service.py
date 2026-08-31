"""Neo4j driver wrapper with indexed batch writes and query helpers."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from types import TracebackType
from typing import Any

logger = logging.getLogger(__name__)

# Schema DDL executed once per process to enable indexed lookups.
_CONSTRAINT_STATEMENTS: tuple[str, ...] = (
    "CREATE CONSTRAINT graph_repository_id IF NOT EXISTS "
    "FOR (n:Repository) REQUIRE n.id IS UNIQUE",
    "CREATE CONSTRAINT graph_file_id IF NOT EXISTS "
    "FOR (n:File) REQUIRE n.id IS UNIQUE",
    "CREATE CONSTRAINT graph_class_id IF NOT EXISTS "
    "FOR (n:Class) REQUIRE n.id IS UNIQUE",
    "CREATE CONSTRAINT graph_function_id IF NOT EXISTS "
    "FOR (n:Function) REQUIRE n.id IS UNIQUE",
    "CREATE CONSTRAINT graph_method_id IF NOT EXISTS "
    "FOR (n:Method) REQUIRE n.id IS UNIQUE",
    "CREATE CONSTRAINT graph_endpoint_id IF NOT EXISTS "
    "FOR (n:ApiEndpoint) REQUIRE n.id IS UNIQUE",
    "CREATE CONSTRAINT graph_table_id IF NOT EXISTS "
    "FOR (n:DatabaseTable) REQUIRE n.id IS UNIQUE",
    "CREATE CONSTRAINT graph_library_id IF NOT EXISTS "
    "FOR (n:ExternalLibrary) REQUIRE n.id IS UNIQUE",
)

# Neo4j 5.x requires a label in CREATE INDEX (bare FOR (n) is invalid).
_REPO_ID_LABELS = ("Repository", "File", "Class", "Function", "Method", "ApiEndpoint", "DatabaseTable")
_NAME_LABELS = ("Repository", "Class", "Function", "Method", "ApiEndpoint", "DatabaseTable", "ExternalLibrary")
_FILE_PATH_LABELS = ("Class", "Function", "Method", "ApiEndpoint", "DatabaseTable")


def _build_index_statements() -> tuple[str, ...]:
    statements: list[str] = []
    for label in _REPO_ID_LABELS:
        slug = label.lower()
        statements.append(
            f"CREATE INDEX graph_{slug}_repo_id IF NOT EXISTS FOR (n:{label}) ON (n.repo_id)",
        )
    for label in _NAME_LABELS:
        slug = label.lower()
        statements.append(
            f"CREATE INDEX graph_{slug}_name IF NOT EXISTS FOR (n:{label}) ON (n.name)",
        )
    for label in _FILE_PATH_LABELS:
        slug = label.lower()
        statements.append(
            f"CREATE INDEX graph_{slug}_file_path IF NOT EXISTS FOR (n:{label}) ON (n.file_path)",
        )
    statements.extend(
        (
            "CREATE INDEX graph_file_path IF NOT EXISTS FOR (n:File) ON (n.path)",
            "CREATE INDEX graph_method_qualified_name IF NOT EXISTS FOR (n:Method) ON (n.qualified_name)",
        ),
    )
    return tuple(statements)


_SCHEMA_STATEMENTS: tuple[str, ...] = _CONSTRAINT_STATEMENTS + _build_index_statements()

_schema_ready = False


@dataclass(slots=True)
class GraphNode:
    """A node in the code knowledge graph."""

    id: str
    label: str
    properties: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class GraphRelationship:
    """A directed relationship between two graph nodes."""

    start_id: str
    end_id: str
    type: str
    properties: dict[str, Any] = field(default_factory=dict)


class GraphServiceError(RuntimeError):
    """Raised when Neo4j operations fail."""


class GraphService:
    """Manage a connection to Neo4j and expose graph operations."""

    def __init__(self, uri: str, user: str, password: str) -> None:
        self._uri = uri
        self._user = user
        self._password = password
        self._driver: Any | None = None

    @property
    def is_connected(self) -> bool:
        return self._driver is not None

    def connect(self) -> None:
        """Open a Neo4j driver connection and ensure schema indexes exist."""
        if self._driver is not None:
            return
        try:
            from neo4j import GraphDatabase
        except ImportError as exc:
            raise GraphServiceError(
                "neo4j package is not installed. Add it to backend/requirements.txt.",
            ) from exc

        try:
            self._driver = GraphDatabase.driver(
                self._uri,
                auth=(self._user, self._password),
            )
            self._driver.verify_connectivity()
            self.ensure_schema()
            logger.info("Connected to Neo4j at %s", self._uri)
        except Exception as exc:
            self._driver = None
            raise GraphServiceError(f"Failed to connect to Neo4j at {self._uri}: {exc}") from exc

    def ensure_schema(self) -> None:
        """Create uniqueness constraints and lookup indexes (idempotent)."""
        global _schema_ready
        if _schema_ready or self._driver is None:
            return
        with self._driver.session() as session:
            for statement in _SCHEMA_STATEMENTS:
                session.run(statement)
        _schema_ready = True
        logger.info("Neo4j graph schema constraints and indexes are ready")

    def close(self) -> None:
        if self._driver is not None:
            self._driver.close()
            self._driver = None

    def upsert_node(self, node: GraphNode) -> None:
        self.upsert_nodes([node])

    def upsert_nodes(self, nodes: list[GraphNode]) -> None:
        if not nodes or self._driver is None:
            return
        grouped: dict[str, list[GraphNode]] = {}
        for node in nodes:
            grouped.setdefault(node.label, []).append(node)

        with self._driver.session() as session:
            for label, batch in grouped.items():
                session.run(
                    f"""
                    UNWIND $rows AS row
                    MERGE (n:{label} {{id: row.id}})
                    SET n += row.props
                    """,
                    rows=[
                        {"id": node.id, "props": {"id": node.id, **node.properties}}
                        for node in batch
                    ],
                )

    def upsert_relationship(self, relationship: GraphRelationship) -> None:
        self.upsert_relationships([relationship])

    def upsert_relationships(self, relationships: list[GraphRelationship]) -> None:
        if not relationships or self._driver is None:
            return
        grouped: dict[str, list[GraphRelationship]] = {}
        for rel in relationships:
            grouped.setdefault(rel.type, []).append(rel)

        with self._driver.session() as session:
            for rel_type, batch in grouped.items():
                session.run(
                    f"""
                    UNWIND $rows AS row
                    MATCH (a {{id: row.start_id}})
                    MATCH (b {{id: row.end_id}})
                    MERGE (a)-[r:{rel_type}]->(b)
                    SET r += row.props
                    """,
                    rows=[
                        {
                            "start_id": rel.start_id,
                            "end_id": rel.end_id,
                            "props": rel.properties,
                        }
                        for rel in batch
                    ],
                )

    def delete_repository(self, repo_id: str) -> int:
        """Remove all nodes belonging to ``repo_id``."""
        if self._driver is None:
            return 0
        with self._driver.session() as session:
            result = session.run(
                """
                MATCH (n {repo_id: $repo_id})
                WITH collect(n) AS nodes, count(n) AS total
                FOREACH (node IN nodes | DETACH DELETE node)
                RETURN total
                """,
                repo_id=repo_id,
            )
            record = result.single()
            return int(record["total"]) if record else 0

    def run(self, cypher: str, parameters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        if self._driver is None:
            raise GraphServiceError("Neo4j driver is not connected.")
        with self._driver.session() as session:
            result = session.run(cypher, parameters or {})
            return [dict(record) for record in result]

    def __enter__(self) -> GraphService:
        self.connect()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.close()
