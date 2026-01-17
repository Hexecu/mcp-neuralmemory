"""
Neo4j driver and session management.
Provides async-compatible driver wrapper with connection pooling.
"""

import logging
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Dict, List, Optional

from neo4j import AsyncGraphDatabase, AsyncDriver, AsyncSession
from neo4j.exceptions import ServiceUnavailable, Neo4jError

from kg_mcp.config import get_settings

logger = logging.getLogger(__name__)


class Neo4jClient:
    """Async Neo4j client with connection management."""

    _instance: Optional["Neo4jClient"] = None
    _driver: Optional[AsyncDriver] = None

    def __new__(cls) -> "Neo4jClient":
        """Singleton pattern for Neo4j client."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    async def connect(self) -> None:
        """Initialize the Neo4j driver connection."""
        if self._driver is not None:
            return

        settings = get_settings()
        try:
            self._driver = AsyncGraphDatabase.driver(
                settings.neo4j_uri,
                auth=(settings.neo4j_user, settings.neo4j_password),
                max_connection_lifetime=3600,
                max_connection_pool_size=50,
                connection_acquisition_timeout=60,
            )
            # Verify connectivity
            await self._driver.verify_connectivity()
            logger.info(f"Connected to Neo4j at {settings.neo4j_uri}")
        except ServiceUnavailable as e:
            logger.error(f"Failed to connect to Neo4j: {e}")
            raise

    async def close(self) -> None:
        """Close the Neo4j driver connection."""
        if self._driver is not None:
            await self._driver.close()
            self._driver = None
            logger.info("Neo4j connection closed")

    @asynccontextmanager
    async def session(self, database: str = "neo4j") -> AsyncGenerator[AsyncSession, None]:
        """Get an async session context manager."""
        if self._driver is None:
            await self.connect()

        session = self._driver.session(database=database)
        try:
            yield session
        finally:
            await session.close()

    async def execute_query(
        self,
        query: str,
        parameters: Optional[Dict[str, Any]] = None,
        database: str = "neo4j",
    ) -> List[Dict[str, Any]]:
        """
        Execute a Cypher query and return results as a list of dicts.

        Args:
            query: Cypher query string
            parameters: Query parameters
            database: Target database name

        Returns:
            List of records as dictionaries
        """
        if self._driver is None:
            await self.connect()

        try:
            result = await self._driver.execute_query(
                query,
                parameters_=parameters or {},
                database_=database,
            )
            return [dict(record) for record in result.records]
        except Neo4jError as e:
            logger.error(f"Query execution failed: {e}")
            raise

    async def execute_write(
        self,
        query: str,
        parameters: Optional[Dict[str, Any]] = None,
        database: str = "neo4j",
    ) -> Dict[str, Any]:
        """
        Execute a write query and return summary.

        Args:
            query: Cypher query string
            parameters: Query parameters
            database: Target database name

        Returns:
            Summary with nodes/relationships created/modified counts
        """
        if self._driver is None:
            await self.connect()

        async with self.session(database) as session:
            result = await session.run(query, parameters or {})
            summary = await result.consume()

            return {
                "nodes_created": summary.counters.nodes_created,
                "nodes_deleted": summary.counters.nodes_deleted,
                "relationships_created": summary.counters.relationships_created,
                "relationships_deleted": summary.counters.relationships_deleted,
                "properties_set": summary.counters.properties_set,
            }


# Singleton instance
_client: Optional[Neo4jClient] = None


def get_neo4j_client() -> Neo4jClient:
    """Get or create the Neo4j client singleton."""
    global _client
    if _client is None:
        _client = Neo4jClient()
    return _client


async def init_neo4j() -> None:
    """Initialize Neo4j connection (call at startup)."""
    client = get_neo4j_client()
    await client.connect()


async def close_neo4j() -> None:
    """Close Neo4j connection (call at shutdown)."""
    client = get_neo4j_client()
    await client.close()
