"""
Request/Response logging middleware with performance tracking.

This middleware logs:
- Request details (method, path, headers, body size)
- Response details (status code, body size)
- Performance metrics (duration)
- Errors and exceptions
"""
import time
import logging
from typing import Callable
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for detailed request/response logging.

    Logs every HTTP request and response with:
    - Request method and path
    - Response status code
    - Request duration in milliseconds
    - User information (if authenticated)
    - Errors and exceptions
    """

    # Paths to skip logging (to reduce noise)
    SKIP_PATHS = {
        "/health",
        "/metrics",
        "/favicon.ico",
    }

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip logging for certain paths
        if request.url.path in self.SKIP_PATHS:
            return await call_next(request)

        start_time = time.time()

        # Extract request details
        method = request.method
        path = str(request.url.path)
        query = str(request.url.query)
        client_ip = request.client.host if request.client else "unknown"

        # Extract user info if authenticated
        user_id = None
        if hasattr(request.state, 'user'):
            user_id = getattr(request.state.user, 'kerberos_id', None)

        try:
            # Process request
            response = await call_next(request)

            # Calculate duration
            duration_ms = int((time.time() - start_time) * 1000)

            # Log successful request
            log_level = logging.INFO
            if response.status_code >= 500:
                log_level = logging.ERROR
            elif response.status_code >= 400:
                log_level = logging.WARNING

            logger.log(
                log_level,
                f"HTTP {method} {path} -> {response.status_code} ({duration_ms}ms)",
                extra={
                    'method': method,
                    'path': path,
                    'query_params': query if query else None,
                    'status_code': response.status_code,
                    'duration_ms': duration_ms,
                    'client_ip': client_ip,
                    'user_id': user_id,
                    'content_length': response.headers.get('content-length'),
                }
            )

            # Warn on slow requests (>2s)
            if duration_ms > 2000:
                logger.warning(
                    f"Slow request detected: {method} {path} took {duration_ms}ms",
                    extra={
                        'method': method,
                        'path': path,
                        'duration_ms': duration_ms,
                        'status_code': response.status_code,
                    }
                )

            return response

        except Exception as e:
            # Calculate duration even on error
            duration_ms = int((time.time() - start_time) * 1000)

            # Log exception
            logger.error(
                f"HTTP {method} {path} raised exception: {type(e).__name__}: {str(e)}",
                exc_info=True,
                extra={
                    'method': method,
                    'path': path,
                    'query_params': query if query else None,
                    'duration_ms': duration_ms,
                    'client_ip': client_ip,
                    'user_id': user_id,
                    'exception_type': type(e).__name__,
                    'exception_message': str(e),
                }
            )

            # Re-raise to let error handler middleware catch it
            raise
