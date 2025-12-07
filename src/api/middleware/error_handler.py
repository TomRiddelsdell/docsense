import logging
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from src.domain.exceptions.document_exceptions import (
    DocumentNotFound,
    InvalidDocumentFormat,
    InvalidDocumentState,
)
from src.domain.exceptions.policy_exceptions import PolicyRepositoryNotFound
from src.domain.exceptions.feedback_exceptions import (
    FeedbackSessionNotFound,
    FeedbackNotFound,
    ChangeAlreadyProcessed,
)

logger = logging.getLogger(__name__)


def add_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(DocumentNotFound)
    async def document_not_found_handler(
        request: Request, exc: DocumentNotFound
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "error": "not_found",
                "message": f"Document with ID {exc.document_id} not found",
            },
        )

    @app.exception_handler(PolicyRepositoryNotFound)
    async def policy_repository_not_found_handler(
        request: Request, exc: PolicyRepositoryNotFound
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "error": "not_found",
                "message": f"Policy repository with ID {exc.repository_id} not found",
            },
        )

    @app.exception_handler(FeedbackSessionNotFound)
    async def feedback_session_not_found_handler(
        request: Request, exc: FeedbackSessionNotFound
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "error": "not_found",
                "message": f"Feedback session with ID {exc.session_id} not found",
            },
        )

    @app.exception_handler(FeedbackNotFound)
    async def feedback_not_found_handler(
        request: Request, exc: FeedbackNotFound
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "error": "not_found",
                "message": f"Feedback with ID {exc.feedback_id} not found",
            },
        )

    @app.exception_handler(InvalidDocumentFormat)
    async def invalid_document_format_handler(
        request: Request, exc: InvalidDocumentFormat
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "error": "invalid_format",
                "message": f"Invalid document format: {exc.provided_format}",
                "supported_formats": exc.supported_formats,
            },
        )

    @app.exception_handler(InvalidDocumentState)
    async def invalid_document_state_handler(
        request: Request, exc: InvalidDocumentState
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "error": "invalid_state",
                "message": str(exc),
                "detail": f"Cannot {exc.operation}: document status is {exc.current_status}, requires {exc.required_status}",
            },
        )

    @app.exception_handler(ChangeAlreadyProcessed)
    async def change_already_processed_handler(
        request: Request, exc: ChangeAlreadyProcessed
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={
                "error": "conflict",
                "message": f"Change with ID {exc.feedback_id} has already been processed",
            },
        )

    @app.exception_handler(ValueError)
    async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "error": "validation_error",
                "message": str(exc),
            },
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        import traceback
        tb = traceback.format_exc()
        logger.error(f"Unhandled exception: {exc}\n{tb}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "internal_error",
                "message": f"An unexpected error occurred: {str(exc)}",
            },
        )
