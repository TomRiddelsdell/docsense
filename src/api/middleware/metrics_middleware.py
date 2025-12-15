"""
Metrics collection middleware.

This middleware automatically tracks HTTP request metrics:
- Request count by method, endpoint, and status code
- Request duration histograms
- Requests in progress gauge
"""
import time
import logging
from typing import Callable
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from src.api.metrics import (
    http_requests_total,
    http_request_duration_seconds,
    http_requests_in_progress
)

logger = logging.getLogger(__name__)


class MetricsMiddleware(BaseHTTPMiddleware):
    """
    Middleware to collect HTTP request metrics.

    Tracks:
    - Total requests by method, endpoint, status code
    - Request duration histograms
    - Requests currently in progress
    """

    # Paths to exclude from metrics (internal endpoints)
    EXCLUDE_PATHS = {
        "/metrics",  # Don't track metrics endpoint itself
        "/favicon.ico",
    }

    def _get_endpoint_label(self, path: str) -> str:
        """
        Convert path to a metric label.

        Replaces dynamic path parameters (UUIDs, IDs) with placeholders
        to avoid high cardinality in metrics.

        Examples:
            /api/v1/documents/123e4567-e89b-12d3-a456-426614174000 -> /api/v1/documents/{id}
            /api/v1/analysis/42 -> /api/v1/analysis/{id}
        """
        import re

        # Replace UUIDs
        path = re.sub(
            r'/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}',
            '/{id}',
            path,
            flags=re.IGNORECASE
        )

        # Replace numeric IDs
        path = re.sub(r'/\d+(?=/|$)', '/{id}', path)

        return path

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip metrics for excluded paths
        if request.url.path in self.EXCLUDE_PATHS:
            return await call_next(request)

        method = request.method
        endpoint = self._get_endpoint_label(str(request.url.path))

        # Track request in progress
        http_requests_in_progress.labels(method=method, endpoint=endpoint).inc()

        start_time = time.time()

        try:
            # Process request
            response = await call_next(request)
            status_code = response.status_code

        except Exception as e:
            # Track error response
            status_code = 500
            logger.error(
                f"Request failed: {method} {endpoint}",
                exc_info=True,
                extra={
                    'method': method,
                    'endpoint': endpoint,
                    'exception_type': type(e).__name__,
                }
            )
            raise

        finally:
            # Calculate duration
            duration = time.time() - start_time

            # Record metrics
            http_requests_total.labels(
                method=method,
                endpoint=endpoint,
                status_code=status_code
            ).inc()

            http_request_duration_seconds.labels(
                method=method,
                endpoint=endpoint
            ).observe(duration)

            # Decrement in-progress counter
            http_requests_in_progress.labels(method=method, endpoint=endpoint).dec()

        return response
