"""
Apply Neo4j schema constraints and indexes.
Run this script to initialize the database schema.
"""

import asyncio
import logging
import sys
from pathlib import Path

from kg_mcp.kg.neo4j import get_neo4j_client, init_neo4j, close_neo4j

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def apply_schema() -> None:
    """Read and apply schema.cypher to Neo4j."""
    logger.info("Connecting to Neo4j...")
    await init_neo4j()

    client = get_neo4j_client()

    # Read schema file
    schema_path = Path(__file__).parent / "schema.cypher"
    if not schema_path.exists():
        logger.error(f"Schema file not found: {schema_path}")
        sys.exit(1)

    logger.info(f"Reading schema from {schema_path}")
    schema_content = schema_path.read_text()

    # Split into individual statements (skip comments and empty lines)
    statements = []
    for line in schema_content.split("\n"):
        line = line.strip()
        # Skip comments and empty lines
        if not line or line.startswith("//"):
            continue
        statements.append(line)

    # Join multi-line statements
    full_statements = []
    current_stmt = []
    for line in statements:
        current_stmt.append(line)
        if line.endswith(";"):
            full_stmt = " ".join(current_stmt).rstrip(";")
            full_statements.append(full_stmt)
            current_stmt = []

    logger.info(f"Found {len(full_statements)} schema statements")

    # Execute each statement
    success_count = 0
    error_count = 0

    for i, stmt in enumerate(full_statements, 1):
        if not stmt.strip():
            continue

        try:
            logger.debug(f"Executing statement {i}: {stmt[:80]}...")
            await client.execute_query(stmt)
            success_count += 1
            logger.info(f"✓ Statement {i} applied successfully")
        except Exception as e:
            error_msg = str(e)
            # Ignore "already exists" errors for constraints/indexes
            if "already exists" in error_msg.lower() or "equivalent" in error_msg.lower():
                logger.info(f"⊘ Statement {i} skipped (already exists)")
                success_count += 1
            else:
                logger.error(f"✗ Statement {i} failed: {e}")
                error_count += 1

    logger.info(f"\nSchema application complete:")
    logger.info(f"  ✓ Success: {success_count}")
    logger.info(f"  ✗ Errors:  {error_count}")

    await close_neo4j()


def main() -> None:
    """Entry point for schema application."""
    asyncio.run(apply_schema())


if __name__ == "__main__":
    main()
