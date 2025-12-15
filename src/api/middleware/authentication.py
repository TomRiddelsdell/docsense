"""Kerberos authentication middleware for FastAPI."""

import logging
from typing import Callable, Set

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class KerberosAuthMiddleware(BaseHTTPMiddleware):
    """Middleware to extract Kerberos authentication from HTTP headers.
    
    Extracts authentication information from HTTP headers and attaches
    to request state for downstream dependency injection.
    
    Headers:
    - X-User-Kerberos: 6-character Kerberos username (e.g., "jsmith")
    - X-User-Groups: Comma-separated list of group names (e.g., "equity-trading,risk-mgmt")
    - X-User-Display-Name: Optional display name (defaults to kerberos_id)
    - X-User-Email: Optional email (defaults to {kerberos_id}@example.com)
    
    Sets request.state:
    - kerberos_id: str | None
    - user_groups: Set[str]
    - display_name: str | None
    - email: str | None
    
    See ADR-021 for authentication architecture details.
    """
    
    async def dispatch(
        self, request: Request, call_next: Callable
    ) -> Response:
        """Extract authentication headers and attach to request state."""
        
        # Extract Kerberos ID
        kerberos_id = request.headers.get("X-User-Kerberos")
        request.state.kerberos_id = kerberos_id.strip() if kerberos_id else None
        
        # Extract groups (comma-separated, strip whitespace)
        groups_header = request.headers.get("X-User-Groups", "")
        if groups_header:
            groups = {
                group.strip()
                for group in groups_header.split(",")
                if group.strip()
            }
        else:
            groups = set()
        request.state.user_groups = groups
        
        # Extract optional display name (defaults to kerberos_id)
        display_name = request.headers.get("X-User-Display-Name")
        if display_name:
            request.state.display_name = display_name.strip()
        elif kerberos_id:
            request.state.display_name = kerberos_id.strip()
        else:
            request.state.display_name = None
        
        # Extract optional email (defaults to {kerberos_id}@example.com)
        email = request.headers.get("X-User-Email")
        if email:
            request.state.email = email.strip()
        elif kerberos_id:
            request.state.email = f"{kerberos_id.strip()}@example.com"
        else:
            request.state.email = None
        
        # Log authentication info (for debugging)
        if kerberos_id:
            logger.debug(
                f"Authenticated request: user={kerberos_id}, "
                f"groups={groups}, path={request.url.path}"
            )
        else:
            logger.debug(f"Unauthenticated request: path={request.url.path}")
        
        # Continue with request processing
        response = await call_next(request)
        return response
