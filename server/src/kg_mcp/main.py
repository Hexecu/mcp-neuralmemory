"""
Main entry point for the MCP-KG-Memory server.
Runs the MCP server with streamable-http transport.
"""

import logging
import sys
from typing import Optional

from mcp.server.fastmcp import FastMCP

from kg_mcp.config import get_settings
from kg_mcp.mcp.tools import register_tools
from kg_mcp.mcp.resources import register_resources
from kg_mcp.mcp.prompts import register_prompts
from kg_mcp.security.auth import create_auth_middleware
from kg_mcp.security.origin import create_origin_middleware

# Configure logging
settings = get_settings()
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


def create_mcp_server() -> FastMCP:
    """Create and configure the MCP server instance."""
    logger.info("Initializing MCP-KG-Memory Server...")

    # Create FastMCP instance
    mcp = FastMCP(
        "KG Memory Server",
        json_response=True,
        stateless_http=settings.mcp_stateless,
    )

    # Register all MCP components
    register_tools(mcp)
    register_resources(mcp)
    register_prompts(mcp)

    logger.info("MCP server components registered successfully")
    return mcp


def main(host: Optional[str] = None, port: Optional[int] = None) -> None:
    """Main entry point for the MCP server."""
    settings = get_settings()

    host = host or settings.mcp_host
    port = port or settings.mcp_port

    logger.info(f"Starting MCP-KG-Memory Server on {host}:{port}")
    logger.info(f"LLM Model: {settings.llm_model}")
    logger.info(f"Neo4j URI: {settings.neo4j_uri}")

    # Create and run the server
    mcp = create_mcp_server()

    # Configure additional middleware for security
    # Note: In production, these would be added to the ASGI app
    if settings.kg_mcp_token:
        logger.info("Bearer token authentication enabled")
    else:
        logger.warning("⚠️  No authentication token configured! Set KG_MCP_TOKEN in .env")

    # Run with streamable-http transport
    mcp.run(
        transport="streamable-http",
        host=host,
        port=port,
    )


if __name__ == "__main__":
    main()
