from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, HTTPException, status

from src.api.schemas.audit import AuditEntry, AuditTrailResponse
from src.api.dependencies import (
    get_audit_trail_handler,
    get_document_audit_handler,
    get_document_by_id_handler,
)
from src.application.queries.document_queries import GetDocumentById
from src.application.queries.audit_queries import GetRecentAuditLogs, GetAuditLogByDocument
from src.application.queries.base import PaginationParams

router = APIRouter()


@router.get("/audit", response_model=AuditTrailResponse)
async def get_global_audit_trail(
    event_type: Optional[str] = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
    handler=Depends(get_audit_trail_handler),
):
    """Get global audit trail with optional filtering."""
    pagination = PaginationParams(
        limit=per_page,
        offset=(page - 1) * per_page,
    )
    
    query = GetRecentAuditLogs(
        event_type=event_type,
        pagination=pagination,
    )

    entries = await handler.handle(query)

    return AuditTrailResponse(
        entries=[
            AuditEntry(
                id=entry.id,
                event_type=entry.event_type,
                document_id=entry.document_id,
                user_id=entry.user_id,
                details=entry.details,
                timestamp=entry.timestamp,
            )
            for entry in entries
        ],
        total=len(entries),
        page=page,
        per_page=per_page,
    )


@router.get("/documents/{document_id}/audit", response_model=AuditTrailResponse)
async def get_document_audit_trail(
    document_id: UUID,
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
    document_handler=Depends(get_document_by_id_handler),
    audit_handler=Depends(get_document_audit_handler),
):
    """Get audit trail for a specific document."""
    doc_query = GetDocumentById(document_id=document_id)
    document = await document_handler.handle(doc_query)

    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID {document_id} not found",
        )

    pagination = PaginationParams(
        limit=per_page,
        offset=(page - 1) * per_page,
    )

    query = GetAuditLogByDocument(
        document_id=document_id,
        pagination=pagination,
    )

    entries = await audit_handler.handle(query)

    return AuditTrailResponse(
        entries=[
            AuditEntry(
                id=entry.id,
                event_type=entry.event_type,
                document_id=entry.document_id,
                user_id=entry.user_id,
                details=entry.details,
                timestamp=entry.timestamp,
            )
            for entry in entries
        ],
        total=len(entries),
        page=page,
        per_page=per_page,
    )
