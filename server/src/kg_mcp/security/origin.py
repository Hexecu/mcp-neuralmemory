"""
Origin validation middleware for MCP server.
Prevents DNS rebinding attacks by validating Origin headers.
"""

import fnmatch
import logging
from typing import Callable, List, Optional

from kg_mcp.config import get_settings

logger = logging.getLogger(__name__)


class OriginValidationError(Exception):
    """Raised when origin validation fails."""

    pass


def validate_origin(origin: Optional[str], allowed_origins: List[str]) -> bool:
    """
    Validate if an origin is allowed.

    Args:
        origin: The Origin header value
        allowed_origins: List of allowed origin patterns (supports wildcards)

    Returns:
        True if the origin is allowed
    """
    if not origin:
        # No origin header - might be a same-origin request or non-browser client
        # For MCP servers, we typically allow this
        return True

    if not allowed_origins:
        # No allowlist configured - only allow localhost by default
        allowed_origins = ["http://localhost:*", "http://127.0.0.1:*"]

    for pattern in allowed_origins:
        if fnmatch.fnmatch(origin, pattern):
            return True

    return False


def create_origin_middleware() -> Callable:
    """
    Create an origin validation middleware function.

    Returns:
        A middleware function that validates Origin headers
    """

    async def origin_middleware(request, call_next):
        """Middleware to validate Origin headers."""
        settings = get_settings()
        allowed_origins = settings.allowed_origins_list

        origin = request.headers.get("origin")

        if not validate_origin(origin, allowed_origins):
            logger.warning(
                f"Rejected request with disallowed origin: {origin} "
                f"(allowed: {allowed_origins})"
            )
            from starlette.responses import JSONResponse

            return JSONResponse(
                status_code=403,
                content={"error": f"Origin '{origin}' is not allowed"},
            )

        # Add CORS headers for allowed origins
        response = await call_next(request)

        if origin and validate_origin(origin, allowed_origins):
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Credentials"] = "true"
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = "Authorization, Content-Type"

        return response

    return origin_middleware


def is_localhost(host: str) -> bool:
    """
    Check if a host is localhost.

    Args:
        host: The host to check

    Returns:
        True if localhost
    """
    localhost_patterns = [
        "localhost",
        "127.0.0.1",
        "::1",
        "[::1]",
    ]

    # Strip port if present
    if ":" in host and not host.startswith("["):
        host = host.split(":")[0]
    elif host.startswith("[") and "]:" in host:
        host = host.split("]:")[0] + "]"

    return host.lower() in localhost_patterns
