import os
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

# Structured logging will be configured in create_app() after loading settings
# Configure minimal logging for startup
logging.basicConfig(level=logging.INFO)
logging.getLogger('pdfminer').setLevel(logging.WARNING)
logging.getLogger('pdfplumber').setLevel(logging.WARNING)

from .middleware.error_handler import add_exception_handlers
from .middleware.request_id import RequestIdMiddleware
from .middleware.authentication import KerberosAuthMiddleware
from .routes import (
    documents, analysis, feedback, policies, audit, health,
    chat, parameters, analysis_logs, projection_health, projection_admin, auth, testing, metrics
)
from .dependencies import Container

STATIC_DIR = Path(__file__).parent.parent.parent / "client" / "dist"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # Validate configuration at startup using Pydantic Settings
    from .config import get_settings
    from pydantic import ValidationError

    try:
        settings = get_settings()
        # Settings are automatically validated by Pydantic
        # log_startup_info() is called in get_settings()
    except ValidationError as e:
        logging.critical("Configuration validation failed:")
        for error in e.errors():
            field = " -> ".join(str(loc) for loc in error['loc'])
            logging.critical(f"  {field}: {error['msg']}")
        raise
    except Exception as e:
        logging.critical(f"Configuration initialization failed: {e}")
        raise

    container = await Container.get_instance()
    
    # Development mode: Show warning and load test data
    if settings.ENVIRONMENT == "development" and settings.DEV_AUTH_BYPASS:
        logger = logging.getLogger(__name__)
        logger.warning("=" * 60)
        logger.warning("🚨 DEVELOPMENT MODE: Auth bypass enabled")
        logger.warning(f"   Test User: {settings.DEV_TEST_USER_KERBEROS}")
        logger.warning(f"   Groups: {settings.DEV_TEST_USER_GROUPS}")
        logger.warning("   All requests without auth headers use test user")
        logger.warning("=" * 60)
        
        # Load test documents
        try:
            from src.infrastructure.dev import TestDataLoader
            test_loader = TestDataLoader()
            await test_loader.ensure_test_data_loaded(
                user_kerberos_id=settings.DEV_TEST_USER_KERBEROS,
                max_documents=10
            )
        except Exception as e:
            logger.warning(f"Failed to load test data: {e}")
            logger.warning("Continuing without test data...")
    
    yield
    await container.close()


def create_app() -> FastAPI:
    # Get validated settings first
    from .config import get_settings
    settings = get_settings()

    # Configure structured logging
    from .logging_config import setup_logging
    setup_logging(log_level=settings.LOG_LEVEL, log_format=settings.LOG_FORMAT)

    app = FastAPI(
        title="Trading Algorithm Document Analyzer API",
        description="API for analyzing trading algorithm documentation with AI-powered feedback.",
        version="1.0.0",
        lifespan=lifespan,
    )

    # CORS configuration from validated settings
    cors_origins = settings.get_cors_origins_list()

    # Security validation: cannot use wildcard with credentials
    if "*" in cors_origins:
        error_msg = (
            "CORS Security Error: Cannot use allow_origins=['*'] with allow_credentials=True. "
            "This violates CORS security policy. "
            "Set CORS_ORIGINS to specific origins (e.g., 'http://localhost:5000,https://app.example.com')."
        )
        if settings.ENVIRONMENT == "production":
            raise ValueError(error_msg)
        else:
            logging.error(error_msg)
            # In development, disable credentials if wildcard is used
            allow_credentials = False
            logging.warning("allow_credentials disabled due to wildcard origin in development mode")
    else:
        allow_credentials = True

    # Log CORS configuration at startup
    logging.info(f"CORS Configuration:")
    logging.info(f"  Environment: {settings.ENVIRONMENT}")
    logging.info(f"  Allowed Origins: {cors_origins}")
    logging.info(f"  Allow Credentials: {allow_credentials}")
    logging.info(f"  Allowed Methods: GET, POST, PUT, DELETE, PATCH")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=allow_credentials,
        allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
        allow_headers=["*"],
    )

    # Add correlation ID tracking for request tracing
    from .middleware.correlation import CorrelationIDMiddleware
    app.add_middleware(CorrelationIDMiddleware)

    # Add request/response logging with performance tracking
    from .middleware.request_logging import RequestLoggingMiddleware
    app.add_middleware(RequestLoggingMiddleware)

    # Add Prometheus metrics collection
    from .middleware.metrics_middleware import MetricsMiddleware
    app.add_middleware(MetricsMiddleware)

    app.add_middleware(RequestIdMiddleware)
    app.add_middleware(KerberosAuthMiddleware)

    # Add audit logging middleware
    # Note: Audit middleware is conditionally added based on configuration
    # In test environments or when an event loop is already running,
    # audit middleware initialization is skipped
    from src.api.middleware.audit import AuditMiddleware
    from src.api.dependencies import get_container
    import asyncio
    try:
        # Try to get the event loop - if one exists, we're likely in a test
        try:
            loop = asyncio.get_running_loop()
            # Already in an event loop (test environment), skip audit middleware
            logging.info("Event loop already running, skipping audit middleware initialization")
        except RuntimeError:
            # No event loop running, safe to use asyncio.run
            container = asyncio.run(get_container())
            if container.audit_logger:
                app.add_middleware(AuditMiddleware, audit_logger=container.audit_logger)
                logging.info("Audit middleware initialized successfully")
    except Exception as e:
        # If we can't initialize audit middleware, log and continue
        # The app can still function without audit logging
        logging.warning(f"Could not initialize audit middleware: {e}")

    add_exception_handlers(app)

    # Metrics endpoint (no prefix - accessible at /metrics)
    app.include_router(metrics.router, tags=["metrics"])

    app.include_router(health.router, prefix="/api/v1", tags=["health"])
    app.include_router(auth.router, prefix="/api/v1", tags=["authentication"])
    app.include_router(documents.router, prefix="/api/v1", tags=["documents"])
    app.include_router(analysis.router, prefix="/api/v1", tags=["analysis"])
    app.include_router(feedback.router, prefix="/api/v1", tags=["feedback"])
    app.include_router(policies.router, prefix="/api/v1", tags=["policies"])
    app.include_router(audit.router, prefix="/api/v1", tags=["audit"])
    app.include_router(chat.router, prefix="/api/v1", tags=["chat"])
    app.include_router(parameters.router, prefix="/api/v1", tags=["parameters"])
    app.include_router(analysis_logs.router, prefix="/api/v1", tags=["analysis-logs"])
    app.include_router(projection_health.router, prefix="/api/v1", tags=["projection-health"])
    app.include_router(projection_admin.router, prefix="/api/v1", tags=["projection-admin"])
    app.include_router(testing.router, prefix="/api/v1", tags=["testing"])

    if STATIC_DIR.exists():
        app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")

        @app.get("/{full_path:path}")
        async def serve_spa(request: Request, full_path: str):
            file_path = STATIC_DIR / full_path
            if file_path.exists() and file_path.is_file():
                return FileResponse(file_path)
            return FileResponse(STATIC_DIR / "index.html")
    else:
        @app.get("/", tags=["health"])
        async def root_health_check() -> dict:
            return {"status": "healthy", "version": "1.0.0"}

    return app


# Only create app at module level if not running tests
# This allows tests to set up environment variables before validation
import sys
if "pytest" not in sys.modules:
    app = create_app()
else:
    # In test mode, create a minimal app that will be replaced by test fixtures
    app = None  # type: ignore
