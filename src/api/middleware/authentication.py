"""Kerberos authentication middleware for FastAPI."""

import logging
from typing import Callable, Set

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from src.api.config import get_settings

logger = logging.getLogger(__name__)


class KerberosAuthMiddleware(BaseHTTPMiddleware):
    """Middleware to extract Kerberos authentication from HTTP headers.
    
    Extracts authentication information from HTTP headers and attaches
    to request state for downstream dependency injection.
    
    In production: Strict authentication required (X-User-Kerberos header)
    In development (DEV_AUTH_BYPASS=true): Auto-injects test user if no header present
    
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
    - dev_mode: bool (True if using dev bypass)
    
    See ADR-021 and ADR-023 for authentication architecture details.
    """
    
    def __init__(self, app):
        super().__init__(app)
        self.settings = get_settings()
    
    async def dispatch(
        self, request: Request, call_next: Callable
    ) -> Response:
        """Extract authentication headers and attach to request state."""
        
        settings = self.settings
        
        # Production mode: Strict authentication required
        if settings.ENVIRONMENT == "production":
            kerberos_id = request.headers.get("X-User-Kerberos")
            
            if not kerberos_id:
                logger.warning(f"Unauthenticated request to production: {request.url.path}")
                return JSONResponse(
                    status_code=401,
                    content={
                        "detail": "Authentication required",
                        "error": "X-User-Kerberos header missing"
                    },
                    headers={"WWW-Authenticate": "Kerberos"}
                )
            
            # Set request state
            request.state.kerberos_id = kerberos_id.strip()
            request.state.user_groups = self._extract_groups(request)
            request.state.display_name = self._extract_display_name(request, kerberos_id)
            request.state.email = self._extract_email(request, kerberos_id)
            request.state.dev_mode = False
            
            logger.debug(
                f"Authenticated request (production): user={kerberos_id}, "
                f"path={request.url.path}"
            )
        
        # Development mode with bypass enabled
        elif settings.DEV_AUTH_BYPASS:
            kerberos_id = request.headers.get("X-User-Kerberos")
            
            if not kerberos_id:
                # No header: Inject test user
                logger.info(
                    f"DEV MODE: Using test user '{settings.DEV_TEST_USER_KERBEROS}' "
                    f"(no auth header) for {request.url.path}"
                )
                
                request.state.kerberos_id = settings.DEV_TEST_USER_KERBEROS
                request.state.user_groups = set(
                    group.strip()
                    for group in settings.DEV_TEST_USER_GROUPS.split(',')
                    if group.strip()
                )
                request.state.display_name = settings.DEV_TEST_USER_NAME
                request.state.email = settings.DEV_TEST_USER_EMAIL
                request.state.dev_mode = True
            else:
                # Header provided: Use that user
                logger.debug(f"DEV MODE: Using provided header user={kerberos_id}")
                request.state.kerberos_id = kerberos_id.strip()
                request.state.user_groups = self._extract_groups(request)
                request.state.display_name = self._extract_display_name(request, kerberos_id)
                request.state.email = self._extract_email(request, kerberos_id)
                request.state.dev_mode = True
        
        # Development mode without bypass: Require headers like production
        else:
            kerberos_id = request.headers.get("X-User-Kerberos")
            
            if not kerberos_id:
                logger.warning(
                    f"Unauthenticated request to development: {request.url.path}. "
                    "Set DEV_AUTH_BYPASS=true for test user."
                )
                return JSONResponse(
                    status_code=401,
                    content={
                        "detail": "Authentication required",
                        "error": "X-User-Kerberos header missing",
                        "hint": "For local development, set DEV_AUTH_BYPASS=true in .env"
                    },
                    headers={"WWW-Authenticate": "Kerberos"}
                )
            
            # Set request state
            request.state.kerberos_id = kerberos_id.strip()
            request.state.user_groups = self._extract_groups(request)
            request.state.display_name = self._extract_display_name(request, kerberos_id)
            request.state.email = self._extract_email(request, kerberos_id)
            request.state.dev_mode = False
        
        # Continue with request processing
        response = await call_next(request)
        
        # Add dev mode indicator headers
        if getattr(request.state, "dev_mode", False):
            response.headers["X-Dev-Mode"] = "enabled"
            response.headers["X-Dev-User"] = request.state.kerberos_id
        
        return response
    
    def _extract_groups(self, request: Request) -> Set[str]:
        """Extract groups from request headers."""
        groups_header = request.headers.get("X-User-Groups", "")
        if groups_header:
            return {
                group.strip()
                for group in groups_header.split(",")
                if group.strip()
            }
        return set()
    
    def _extract_display_name(self, request: Request, kerberos_id: str) -> str:
        """Extract display name from request headers or default to kerberos_id."""
        display_name = request.headers.get("X-User-Display-Name")
        if display_name:
            return display_name.strip()
        return kerberos_id.strip()
    
    def _extract_email(self, request: Request, kerberos_id: str) -> str:
        """Extract email from request headers or default to {kerberos_id}@example.com."""
        email = request.headers.get("X-User-Email")
        if email:
            return email.strip()
        return f"{kerberos_id.strip()}@example.com"
