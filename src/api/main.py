from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .middleware.error_handler import add_exception_handlers
from .middleware.request_id import RequestIdMiddleware
from .routes import documents, analysis, feedback, policies, audit, health
from .dependencies import Container


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    container = await Container.get_instance()
    yield
    await container.close()


def create_app() -> FastAPI:
    app = FastAPI(
        title="Trading Algorithm Document Analyzer API",
        description="API for analyzing trading algorithm documentation with AI-powered feedback.",
        version="1.0.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.add_middleware(RequestIdMiddleware)

    add_exception_handlers(app)

    app.include_router(health.router, prefix="/api/v1", tags=["health"])
    app.include_router(documents.router, prefix="/api/v1", tags=["documents"])
    app.include_router(analysis.router, prefix="/api/v1", tags=["analysis"])
    app.include_router(feedback.router, prefix="/api/v1", tags=["feedback"])
    app.include_router(policies.router, prefix="/api/v1", tags=["policies"])
    app.include_router(audit.router, prefix="/api/v1", tags=["audit"])

    return app


app = create_app()
