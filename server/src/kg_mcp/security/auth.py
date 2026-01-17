"""
Authentication middleware for MCP server.
Validates Bearer tokens for incoming requests.
"""

import logging
from typing import Callable, Optional

from kg_mcp.config import get_settings

logger = logging.getLogger(__name__)


class AuthenticationError(Exception):
    """Raised when authentication fails."""

    pass


def validate_bearer_token(token: str) -> bool:
    """
    Validate a bearer token against the configured token.

    Args:
        token: The token to validate

    Returns:
        True if valid, False otherwise
    """
    settings = get_settings()

    if not settings.kg_mcp_token:
        # No token configured - authentication disabled
        logger.warning("No authentication token configured - all requests allowed")
        return True

    return token == settings.kg_mcp_token


def extract_bearer_token(authorization_header: Optional[str]) -> Optional[str]:
    """
    Extract the bearer token from an Authorization header.

    Args:
        authorization_header: The full Authorization header value

    Returns:
        The token if present and properly formatted, None otherwise
    """
    if not authorization_header:
        return None

    parts = authorization_header.split()
    if len(parts) != 2:
        return None

    scheme, token = parts
    if scheme.lower() != "bearer":
        return None

    return token


def create_auth_middleware() -> Callable:
    """
    Create an authentication middleware function.

    Returns:
        A middleware function that validates requests
    """

    async def auth_middleware(request, call_next):
        """Middleware to check authentication on all requests."""
        settings = get_settings()

        # Skip auth if no token configured
        if not settings.kg_mcp_token:
            return await call_next(request)

        # Extract and validate token
        auth_header = request.headers.get("authorization")
        token = extract_bearer_token(auth_header)

        if not token:
            logger.warning(f"Missing or invalid Authorization header from {request.client.host}")
            # Return 401 Unauthorized
            from starlette.responses import JSONResponse

            return JSONResponse(
                status_code=401,
                content={"error": "Missing or invalid Authorization header"},
            )

        if not validate_bearer_token(token):
            logger.warning(f"Invalid token from {request.client.host}")
            return JSONResponse(
                status_code=403,
                content={"error": "Invalid authentication token"},
            )

        return await call_next(request)

    return auth_middleware


def require_auth(func: Callable) -> Callable:
    """
    Decorator to require authentication for a function.

    This is a simple decorator for individual functions,
    not for use with the full middleware system.
    """
    import functools

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        # In the context of MCP tools, auth is handled at the transport level
        # This decorator is a placeholder for additional auth checks if needed
        return await func(*args, **kwargs)

    return wrapper
