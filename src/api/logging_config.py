"""
Structured logging configuration with correlation ID tracking.

This module provides:
- JSON structured logging for production
- Human-readable logging for development
- Correlation ID tracking across requests
- Request/response logging middleware
- Context-aware logger with automatic correlation ID injection
"""
import logging
import json
import sys
from datetime import datetime
from typing import Any, Dict, Optional
from contextvars import ContextVar

# Context variable for tracking correlation ID across async operations
correlation_id_var: ContextVar[Optional[str]] = ContextVar('correlation_id', default=None)


class CorrelationIDFilter(logging.Filter):
    """Add correlation ID to log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.correlation_id = correlation_id_var.get() or 'no-correlation-id'
        return True


class JSONFormatter(logging.Formatter):
    """
    JSON formatter for structured logging.

    Outputs logs as JSON objects for easy parsing by log aggregation systems.
    """

    def format(self, record: logging.LogRecord) -> str:
        log_data: Dict[str, Any] = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'correlation_id': getattr(record, 'correlation_id', 'no-correlation-id'),
        }

        # Add extra fields if present
        if hasattr(record, 'request_id'):
            log_data['request_id'] = record.request_id

        if hasattr(record, 'user_id'):
            log_data['user_id'] = record.user_id

        if hasattr(record, 'duration_ms'):
            log_data['duration_ms'] = record.duration_ms

        if hasattr(record, 'status_code'):
            log_data['status_code'] = record.status_code

        if hasattr(record, 'method'):
            log_data['method'] = record.method

        if hasattr(record, 'path'):
            log_data['path'] = record.path

        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = {
                'type': record.exc_info[0].__name__ if record.exc_info[0] else None,
                'message': str(record.exc_info[1]) if record.exc_info[1] else None,
                'traceback': self.formatException(record.exc_info) if record.exc_info else None
            }

        # Add module and function info
        log_data['module'] = record.module
        log_data['function'] = record.funcName
        log_data['line'] = record.lineno

        return json.dumps(log_data)


class HumanReadableFormatter(logging.Formatter):
    """
    Human-readable formatter for development.

    Outputs colorized logs with correlation IDs for easy reading during development.
    """

    # Color codes
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
        'RESET': '\033[0m'
    }

    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
        reset = self.COLORS['RESET']

        correlation_id = getattr(record, 'correlation_id', 'no-correlation-id')

        # Base format
        log_message = (
            f"{color}[{record.levelname}]{reset} "
            f"{datetime.utcnow().isoformat()}Z "
            f"[{correlation_id[:8]}...] "
            f"{record.name} - {record.getMessage()}"
        )

        # Add extra context if available
        extra_fields = []
        if hasattr(record, 'method') and hasattr(record, 'path'):
            extra_fields.append(f"{record.method} {record.path}")

        if hasattr(record, 'status_code'):
            extra_fields.append(f"status={record.status_code}")

        if hasattr(record, 'duration_ms'):
            extra_fields.append(f"duration={record.duration_ms}ms")

        if extra_fields:
            log_message += f" [{', '.join(extra_fields)}]"

        # Add exception info if present
        if record.exc_info:
            log_message += f"\n{self.formatException(record.exc_info)}"

        return log_message


def setup_logging(log_level: str = "INFO", log_format: str = "json") -> None:
    """
    Configure application logging.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_format: Output format - "json" for production, "text" for development
    """
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))

    # Remove existing handlers
    root_logger.handlers.clear()

    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, log_level.upper()))

    # Add correlation ID filter
    correlation_filter = CorrelationIDFilter()
    console_handler.addFilter(correlation_filter)

    # Set formatter based on format preference
    if log_format.lower() == "json":
        formatter = JSONFormatter()
    else:
        formatter = HumanReadableFormatter()

    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # Configure uvicorn loggers to use the same format
    for logger_name in ["uvicorn", "uvicorn.error", "uvicorn.access"]:
        logger = logging.getLogger(logger_name)
        logger.handlers.clear()
        logger.addHandler(console_handler)
        logger.propagate = False

    logging.info(
        "Logging configured successfully",
        extra={
            'log_level': log_level,
            'log_format': log_format
        }
    )


def get_correlation_id() -> Optional[str]:
    """Get the current correlation ID from context."""
    return correlation_id_var.get()


def set_correlation_id(correlation_id: str) -> None:
    """Set the correlation ID in context."""
    correlation_id_var.set(correlation_id)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger with correlation ID support.

    This is a convenience wrapper around logging.getLogger that ensures
    correlation IDs are automatically included in log messages.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Logger instance with correlation ID support
    """
    return logging.getLogger(name)
