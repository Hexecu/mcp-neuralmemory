"""
Main entry point for the MCP-KG-Memory server.
Supports both STDIO and Streamable HTTP transports for Antigravity compatibility.

Usage:
    # STDIO mode (for Antigravity command/args config)
    python -m kg_mcp --transport stdio

    # HTTP mode (for Antigravity serverUrl config or standalone)
    python -m kg_mcp --transport http --host 127.0.0.1 --port 8000
"""

import argparse
import logging
import os
import signal
import sys
from typing import Optional

from mcp.server.fastmcp import FastMCP

from kg_mcp.config import get_settings
from kg_mcp.mcp.tools import register_tools
from kg_mcp.mcp.resources import register_resources
from kg_mcp.mcp.prompts import register_prompts


def setup_logging(transport: str) -> logging.Logger:
    """
    Configure logging based on transport mode.

    For STDIO: Log ONLY to stderr (stdout is reserved for MCP protocol)
    For HTTP: Log to stdout
    """
    settings = get_settings()
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)

    # Clear any existing handlers
    root_logger = logging.getLogger()
    root_logger.handlers.clear()

    if transport == "stdio":
        # CRITICAL: In stdio mode, stdout is for MCP protocol ONLY
        # All logs must go to stderr
        handler = logging.StreamHandler(sys.stderr)
    else:
        handler = logging.StreamHandler(sys.stdout)

    handler.setFormatter(
        logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    )
    root_logger.addHandler(handler)
    root_logger.setLevel(log_level)

    return logging.getLogger(__name__)


def create_mcp_server(json_response: bool = True, stateless: bool = True) -> FastMCP:
    """Create and configure the MCP server instance."""
    logger = logging.getLogger(__name__)
    logger.info("Initializing MCP-KG-Memory Server...")

    # Create FastMCP instance
    mcp = FastMCP(
        "KG Memory Server",
        json_response=json_response,
        stateless_http=stateless,
    )

    # Register all MCP components
    register_tools(mcp)
    register_resources(mcp)
    register_prompts(mcp)

    logger.info("MCP server components registered successfully")
    return mcp


def handle_shutdown(signum, frame):
    """Handle graceful shutdown on SIGTERM/SIGINT."""
    logger = logging.getLogger(__name__)
    logger.info(f"Received signal {signum}, shutting down gracefully...")
    sys.exit(0)


def run_stdio():
    """Run server in STDIO mode (for Antigravity command/args config)."""
    logger = setup_logging("stdio")
    logger.info("Starting MCP-KG-Memory Server in STDIO mode")

    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGTERM, handle_shutdown)
    signal.signal(signal.SIGINT, handle_shutdown)

    settings = get_settings()
    if settings.kg_mcp_token:
        logger.info("Token authentication configured")
    else:
        logger.warning("No authentication token configured")

    logger.info(f"LLM Model: {settings.llm_model}")
    logger.info(f"Neo4j URI: {settings.neo4j_uri}")

    # Create and run server
    mcp = create_mcp_server(json_response=True, stateless=True)

    # Run with stdio transport
    mcp.run(transport="stdio")


def run_http(host: str = "127.0.0.1", port: int = 8000, path: str = "/mcp"):
    """Run server in HTTP mode (for Antigravity serverUrl config or standalone)."""
    logger = setup_logging("http")
    logger.info(f"Starting MCP-KG-Memory Server in HTTP mode on {host}:{port}{path}")

    # Register signal handlers
    signal.signal(signal.SIGTERM, handle_shutdown)
    signal.signal(signal.SIGINT, handle_shutdown)

    settings = get_settings()
    if settings.kg_mcp_token:
        logger.info("Bearer token authentication enabled")
    else:
        logger.warning("⚠️  No authentication token configured! Set KG_MCP_TOKEN in .env")

    logger.info(f"LLM Model: {settings.llm_model}")
    logger.info(f"Neo4j URI: {settings.neo4j_uri}")

    # Create and run server
    mcp = create_mcp_server(json_response=True, stateless=True)

    # Run with streamable-http transport
    mcp.run(
        transport="streamable-http",
        host=host,
        port=port,
    )


def main():
    """Main entry point with CLI argument parsing."""
    parser = argparse.ArgumentParser(
        description="MCP-KG-Memory Server - Knowledge Graph Memory for IDE Agents",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # STDIO mode (for Antigravity command config)
  python -m kg_mcp --transport stdio

  # HTTP mode (for Antigravity serverUrl config)
  python -m kg_mcp --transport http --host 127.0.0.1 --port 8000

  # Using console script
  kg-mcp --transport stdio
        """,
    )

    parser.add_argument(
        "--transport",
        "-t",
        choices=["stdio", "http"],
        default="http",
        help="Transport mode: 'stdio' for command-based, 'http' for serverUrl-based (default: http)",
    )

    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host to bind to in HTTP mode (default: 127.0.0.1)",
    )

    parser.add_argument(
        "--port",
        "-p",
        type=int,
        default=8000,
        help="Port to listen on in HTTP mode (default: 8000)",
    )

    parser.add_argument(
        "--path",
        default="/mcp",
        help="MCP endpoint path in HTTP mode (default: /mcp)",
    )

    args = parser.parse_args()

    if args.transport == "stdio":
        run_stdio()
    else:
        run_http(host=args.host, port=args.port, path=args.path)


if __name__ == "__main__":
    main()
