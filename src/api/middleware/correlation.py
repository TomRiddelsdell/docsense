"""
Correlation ID middleware for request tracking.

This middleware:
- Generates or extracts correlation IDs from requests
- Adds correlation IDs to request state
- Injects correlation IDs into logging context
- Returns correlation IDs in response headers
"""
import uuid
import logging
from typing import Callable
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from src.api.logging_config import set_correlation_id

logger = logging.getLogger(__name__)


class CorrelationIDMiddleware(BaseHTTPMiddleware):
    """
    Middleware to track requests with correlation IDs.

    Correlation IDs are used to trace a single request through the entire system,
    across multiple services and log entries.

    The middleware:
    1. Checks for X-Correlation-ID header in incoming request
    2. Generates a new UUID if not present
    3. Sets the correlation ID in the async context
    4. Adds the correlation ID to the response headers
    5. Makes the ID available to all logs within the request
    """

    HEADER_NAME = "X-Correlation-ID"

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Extract or generate correlation ID
        correlation_id = request.headers.get(
            self.HEADER_NAME,
            request.headers.get(self.HEADER_NAME.lower()),
        )

        if not correlation_id:
            correlation_id = str(uuid.uuid4())

        # Set in async context for logging
        set_correlation_id(correlation_id)

        # Store in request state for handlers
        request.state.correlation_id = correlation_id

        # Log request received
        logger.info(
            f"Request received: {request.method} {request.url.path}",
            extra={
                'method': request.method,
                'path': str(request.url.path),
                'query_params': str(request.url.query),
                'client': request.client.host if request.client else None,
            }
        )

        # Process request
        response = await call_next(request)

        # Add correlation ID to response headers
        response.headers[self.HEADER_NAME] = correlation_id

        # Log response sent
        logger.info(
            f"Response sent: {request.method} {request.url.path}",
            extra={
                'method': request.method,
                'path': str(request.url.path),
                'status_code': response.status_code,
            }
        )

        return response
