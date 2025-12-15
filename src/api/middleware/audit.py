"""Audit middleware for automatic access logging.

Automatically logs all document access attempts to the audit log.
Captures both successful and denied access for complete audit trail.
"""

import logging
import re
from typing import Optional
from uuid import UUID

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.status import HTTP_403_FORBIDDEN, HTTP_404_NOT_FOUND

from src.infrastructure.audit import AuditLogger

logger = logging.getLogger(__name__)


# Regex pattern to extract document ID from URL paths
DOCUMENT_ID_PATTERN = re.compile(
    r'/api/v1/documents/([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})',
    re.IGNORECASE
)

# Map HTTP methods and paths to actions
ACTION_MAPPING = {
    ('GET', r'/documents/[^/]+$'): 'view',
    ('GET', r'/documents/[^/]+/content'): 'view',
    ('GET', r'/documents/[^/]+/download'): 'download',
    ('GET', r'/documents/[^/]+/semantic-ir'): 'view',
    ('PATCH', r'/documents/[^/]+'): 'edit',
    ('PUT', r'/documents/[^/]+'): 'edit',
    ('DELETE', r'/documents/[^/]+'): 'delete',
    ('POST', r'/documents/[^/]+/share'): 'share',
    ('POST', r'/documents/[^/]+/make-private'): 'share',
    ('POST', r'/documents/[^/]+/export'): 'export',
    ('POST', r'/documents/[^/]+/analyze'): 'analyze',
}


class AuditMiddleware(BaseHTTPMiddleware):
    """Middleware to automatically log document access.
    
    Logs all requests to document endpoints, capturing:
    - Successful access (200-299 status codes)
    - Denied access (403 Forbidden)
    - User identity, action, IP address, user agent
    
    Does not log 404 Not Found (document doesn't exist).
    """
    
    def __init__(self, app, audit_logger: AuditLogger):
        """Initialize audit middleware.
        
        Args:
            app: FastAPI application
            audit_logger: AuditLogger instance for writing logs
        """
        super().__init__(app)
        self._audit_logger = audit_logger
    
    def _extract_document_id(self, path: str) -> Optional[UUID]:
        """Extract document ID from URL path.
        
        Args:
            path: URL path
            
        Returns:
            Document UUID if found in path, None otherwise
        """
        match = DOCUMENT_ID_PATTERN.search(path)
        if match:
            try:
                return UUID(match.group(1))
            except ValueError:
                return None
        return None
    
    def _determine_action(self, method: str, path: str) -> Optional[str]:
        """Determine action type from HTTP method and path.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            path: URL path
            
        Returns:
            Action name (view, edit, delete, etc.) or None if not a document action
        """
        # Normalize path for pattern matching
        normalized_path = path.replace('/api/v1', '')
        
        for (pattern_method, pattern_path), action in ACTION_MAPPING.items():
            if method == pattern_method and re.search(pattern_path, normalized_path):
                return action
        
        return None
    
    def _get_client_ip(self, request: Request) -> Optional[str]:
        """Extract client IP address from request.
        
        Checks X-Forwarded-For header first (for proxies), then falls back
        to direct client connection.
        
        Args:
            request: FastAPI request
            
        Returns:
            Client IP address or None
        """
        # Check for X-Forwarded-For header (proxy/load balancer)
        forwarded = request.headers.get('X-Forwarded-For')
        if forwarded:
            # Take first IP if multiple proxies
            return forwarded.split(',')[0].strip()
        
        # Fall back to direct client
        if request.client:
            return request.client.host
        
        return None
    
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """Process request and log document access.
        
        Args:
            request: Incoming HTTP request
            call_next: Next middleware/endpoint in chain
            
        Returns:
            HTTP response
        """
        # Extract document ID from path
        document_id = self._extract_document_id(request.url.path)
        
        # Skip if not a document endpoint
        if not document_id:
            return await call_next(request)
        
        # Determine action type
        action = self._determine_action(request.method, request.url.path)
        if not action:
            return await call_next(request)
        
        # Extract user identity (set by authentication middleware)
        user_kerberos_id = getattr(request.state, 'kerberos_id', None)
        
        # Skip audit logging if no user (shouldn't happen, but be safe)
        if not user_kerberos_id:
            return await call_next(request)
        
        # Get client info
        ip_address = self._get_client_ip(request)
        user_agent = request.headers.get('User-Agent')
        
        # Process request
        response = await call_next(request)
        
        # Log based on response status
        if 200 <= response.status_code < 300:
            # Successful access
            await self._audit_logger.log_access(
                user_kerberos_id=user_kerberos_id,
                document_id=document_id,
                action=action,
                result='allowed',
                reason=None,
                ip_address=ip_address,
                user_agent=user_agent,
            )
        elif response.status_code == HTTP_403_FORBIDDEN:
            # Access denied - extract reason from response if available
            reason = "Access forbidden"
            # Note: We can't easily read response body here without buffering,
            # so we use a generic message. Specific denial reasons should be
            # logged by the authorization service itself if needed.
            await self._audit_logger.log_access(
                user_kerberos_id=user_kerberos_id,
                document_id=document_id,
                action=action,
                result='denied',
                reason=reason,
                ip_address=ip_address,
                user_agent=user_agent,
            )
        # Don't log 404s - document doesn't exist
        
        return response
