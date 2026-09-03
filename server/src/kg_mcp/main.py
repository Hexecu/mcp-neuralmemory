"""Command-line entry point for Neural Memory."""

from __future__ import annotations

import argparse
import logging
import sys
from contextlib import asynccontextmanager

import uvicorn

from kg_mcp.api import create_api_app
from kg_mcp.config import get_settings
from kg_mcp.kg.client import close_neo4j, init_neo4j

logger = logging.getLogger(__name__)


def setup_logging(transport: str) -> logging.Logger:
    settings = get_settings()
    handler = logging.StreamHandler(sys.stderr if transport == "stdio" else sys.stdout)
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))
    return logging.getLogger(__name__)


@asynccontextmanager
async def http_lifespan(app):
    await init_neo4j()
    try:
        yield
    finally:
        await close_neo4j()


def create_mcp_server(*, lifespan=None):
    from mcp.server.fastmcp import FastMCP

    from kg_mcp.mcp.prompts import register_prompts
    from kg_mcp.mcp.resources import register_resources
    from kg_mcp.mcp.tools import register_tools

    mcp = FastMCP("Neural Memory", json_response=True, stateless_http=True, lifespan=lifespan)
    register_tools(mcp)
    register_resources(mcp)
    register_prompts(mcp)
    return mcp


def run_stdio() -> None:
    setup_logging("stdio")
    create_mcp_server().run(transport="stdio")


def run_http(host: str | None = None, port: int | None = None) -> None:
    settings = get_settings()
    setup_logging("http")
    app = create_api_app(lifespan=http_lifespan)
    uvicorn.run(app, host=host or settings.mcp_host, port=port or settings.mcp_port)


def main() -> None:
    settings = get_settings()
    parser = argparse.ArgumentParser(description="Local-first memory for people and AI agents")
    parser.add_argument("--transport", "-t", choices=["stdio", "http"], default="http")
    parser.add_argument("--host", default=settings.mcp_host)
    parser.add_argument("--port", type=int, default=settings.mcp_port)
    args = parser.parse_args()
    if args.transport == "stdio":
        run_stdio()
    else:
        run_http(args.host, args.port)


if __name__ == "__main__":
    main()
