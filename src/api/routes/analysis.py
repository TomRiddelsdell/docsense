from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from src.api.schemas.analysis import (
    AnalysisSessionResponse,
    StartAnalysisRequest,
)
from src.api.dependencies import (
    get_start_analysis_handler,
    get_cancel_analysis_handler,
    get_document_by_id_handler,
    get_container,
)
from src.domain.commands import StartAnalysis, CancelAnalysis
from src.domain.exceptions.document_exceptions import DocumentNotFound, InvalidDocumentState
from src.application.queries.document_queries import GetDocumentById

router = APIRouter()


@router.post("/documents/{document_id}/reset", status_code=status.HTTP_200_OK)
async def reset_document_for_retry(
    document_id: UUID,
):
    container = await get_container()
    
    document = await container.document_repository.get(document_id)
    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID {document_id} not found",
        )

    try:
        document.reset_for_retry(reset_by="user")
    except InvalidDocumentState as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    events = list(document.pending_events)
    await container.document_repository.save(document)

    if events:
        await container.event_publisher.publish_all(events)
    
    return {"message": "Document reset successfully", "document_id": str(document_id), "new_status": "converted"}


@router.post(
    "/documents/{document_id}/analyze",
    response_model=AnalysisSessionResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def start_analysis(
    document_id: UUID,
    request: Optional[StartAnalysisRequest] = None,
    start_handler=Depends(get_start_analysis_handler),
    document_handler=Depends(get_document_by_id_handler),
):
    query = GetDocumentById(document_id=document_id)
    document = await document_handler.handle(query)

    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID {document_id} not found",
        )

    if document.policy_repository_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Document must be assigned to a policy repository before analysis",
        )

    model_provider = request.model_provider if request else "gemini"
    focus_areas = request.focus_areas if request else None

    command = StartAnalysis(
        document_id=document_id,
        policy_repository_id=document.policy_repository_id,
        ai_model=model_provider or "gemini",
        initiated_by="anonymous",
    )

    await start_handler.handle(command)
    
    updated_doc = await document_handler.handle(query)
    
    from datetime import datetime, timezone
    return AnalysisSessionResponse(
        document_id=document_id,
        status=updated_doc.status if updated_doc else "in_progress",
        model_provider=model_provider,
        issues_found=0,
        started_at=datetime.now(timezone.utc),
    )


@router.get("/documents/{document_id}/analysis", response_model=AnalysisSessionResponse)
async def get_analysis_status(
    document_id: UUID,
    document_handler=Depends(get_document_by_id_handler),
):
    query = GetDocumentById(document_id=document_id)
    document = await document_handler.handle(query)

    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID {document_id} not found",
        )

    return AnalysisSessionResponse(
        document_id=document_id,
        status="pending" if document.status != "analyzed" else "completed",
        issues_found=0,
    )


@router.delete("/documents/{document_id}/analysis", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_analysis(
    document_id: UUID,
    handler=Depends(get_cancel_analysis_handler),
):
    command = CancelAnalysis(document_id=document_id, cancelled_by="anonymous")
    await handler.handle(command)
    return None
