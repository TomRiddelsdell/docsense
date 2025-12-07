from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, HTTPException, status

from src.api.schemas.feedback import (
    FeedbackItemResponse,
    FeedbackListResponse,
    RejectFeedbackRequest,
)
from src.api.dependencies import (
    get_accept_change_handler,
    get_reject_change_handler,
    get_feedback_by_document_handler,
    get_feedback_by_id_handler,
    get_count_feedback_handler,
    get_document_by_id_handler,
)
from src.domain.commands import AcceptChange, RejectChange
from src.application.queries.document_queries import GetDocumentById
from src.application.queries.feedback_queries import (
    GetFeedbackByDocument,
    GetFeedbackById,
    CountFeedbackByDocument,
)

router = APIRouter()


@router.get("/documents/{document_id}/feedback", response_model=FeedbackListResponse)
async def get_document_feedback(
    document_id: UUID,
    status_filter: Optional[str] = Query(None, alias="status"),
    document_handler=Depends(get_document_by_id_handler),
    feedback_handler=Depends(get_feedback_by_document_handler),
    count_handler=Depends(get_count_feedback_handler),
):
    query = GetDocumentById(document_id=document_id)
    document = await document_handler.handle(query)

    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID {document_id} not found",
        )

    feedback_query = GetFeedbackByDocument(
        document_id=document_id,
        status=status_filter,
    )
    feedback_items = await feedback_handler.handle(feedback_query)

    pending_query = CountFeedbackByDocument(document_id=document_id, status="pending")
    accepted_query = CountFeedbackByDocument(document_id=document_id, status="accepted")
    rejected_query = CountFeedbackByDocument(document_id=document_id, status="rejected")

    pending_count = await count_handler.handle(pending_query)
    accepted_count = await count_handler.handle(accepted_query)
    rejected_count = await count_handler.handle(rejected_query)

    return FeedbackListResponse(
        items=[
            FeedbackItemResponse(
                id=item.id,
                document_id=item.document_id,
                section_id=item.section_id,
                status=item.status,
                category=item.category,
                severity=item.severity,
                original_text=item.original_text,
                suggestion=item.suggestion,
                explanation=item.explanation,
                confidence_score=item.confidence_score,
                policy_reference=item.policy_reference,
                rejection_reason=item.rejection_reason,
                processed_at=item.processed_at,
                created_at=item.created_at,
            )
            for item in feedback_items
        ],
        total=len(feedback_items),
        pending_count=pending_count,
        accepted_count=accepted_count,
        rejected_count=rejected_count,
    )


@router.get("/documents/{document_id}/feedback/{feedback_id}", response_model=FeedbackItemResponse)
async def get_feedback_item(
    document_id: UUID,
    feedback_id: UUID,
    feedback_handler=Depends(get_feedback_by_id_handler),
):
    query = GetFeedbackById(feedback_id=feedback_id)
    feedback = await feedback_handler.handle(query)

    if feedback is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Feedback with ID {feedback_id} not found",
        )

    if feedback.document_id != document_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Feedback with ID {feedback_id} not found for document {document_id}",
        )

    return FeedbackItemResponse(
        id=feedback.id,
        document_id=feedback.document_id,
        section_id=feedback.section_id,
        status=feedback.status,
        category=feedback.category,
        severity=feedback.severity,
        original_text=feedback.original_text,
        suggestion=feedback.suggestion,
        explanation=feedback.explanation,
        confidence_score=feedback.confidence_score,
        policy_reference=feedback.policy_reference,
        rejection_reason=feedback.rejection_reason,
        processed_at=feedback.processed_at,
        created_at=feedback.created_at,
    )


@router.post("/documents/{document_id}/feedback/{feedback_id}/accept", response_model=FeedbackItemResponse)
async def accept_feedback(
    document_id: UUID,
    feedback_id: UUID,
    accept_handler=Depends(get_accept_change_handler),
    feedback_handler=Depends(get_feedback_by_id_handler),
):
    command = AcceptChange(
        document_id=document_id,
        feedback_id=feedback_id,
        accepted_by="anonymous",
    )
    await accept_handler.handle(command)

    query = GetFeedbackById(feedback_id=feedback_id)
    feedback = await feedback_handler.handle(query)

    if feedback is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Feedback with ID {feedback_id} not found",
        )

    return FeedbackItemResponse(
        id=feedback.id,
        document_id=feedback.document_id,
        section_id=feedback.section_id,
        status="accepted",
        category=feedback.category,
        severity=feedback.severity,
        original_text=feedback.original_text,
        suggestion=feedback.suggestion,
        explanation=feedback.explanation,
        confidence_score=feedback.confidence_score,
        policy_reference=feedback.policy_reference,
        rejection_reason=feedback.rejection_reason,
        processed_at=feedback.processed_at,
        created_at=feedback.created_at,
    )


@router.post("/documents/{document_id}/feedback/{feedback_id}/reject", response_model=FeedbackItemResponse)
async def reject_feedback(
    document_id: UUID,
    feedback_id: UUID,
    request: Optional[RejectFeedbackRequest] = None,
    reject_handler=Depends(get_reject_change_handler),
    feedback_handler=Depends(get_feedback_by_id_handler),
):
    command = RejectChange(
        document_id=document_id,
        feedback_id=feedback_id,
        rejected_by="anonymous",
        reason=request.reason if request else None,
    )
    await reject_handler.handle(command)

    query = GetFeedbackById(feedback_id=feedback_id)
    feedback = await feedback_handler.handle(query)

    if feedback is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Feedback with ID {feedback_id} not found",
        )

    return FeedbackItemResponse(
        id=feedback.id,
        document_id=feedback.document_id,
        section_id=feedback.section_id,
        status="rejected",
        category=feedback.category,
        severity=feedback.severity,
        original_text=feedback.original_text,
        suggestion=feedback.suggestion,
        explanation=feedback.explanation,
        confidence_score=feedback.confidence_score,
        policy_reference=feedback.policy_reference,
        rejection_reason=request.reason if request else None,
        processed_at=feedback.processed_at,
        created_at=feedback.created_at,
    )
