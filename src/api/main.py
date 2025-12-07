import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .middleware.error_handler import add_exception_handlers
from .middleware.request_id import RequestIdMiddleware
from .routes import documents, analysis, feedback, policies, audit, health, chat, parameters
from .dependencies import Container

STATIC_DIR = Path(__file__).parent.parent.parent / "client" / "dist"


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
    app.include_router(chat.router, prefix="/api/v1", tags=["chat"])
    app.include_router(parameters.router, prefix="/api/v1", tags=["parameters"])

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


app = create_app()
