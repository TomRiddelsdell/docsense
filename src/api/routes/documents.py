from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, UploadFile, File, Form, Query, HTTPException, status
from fastapi.responses import StreamingResponse

from src.api.schemas.documents import (
    DocumentResponse,
    DocumentDetailResponse,
    DocumentListResponse,
    DocumentContentResponse,
    DocumentUpdateRequest,
    ExportDocumentRequest,
)
from src.api.dependencies import (
    get_upload_document_handler,
    get_export_document_handler,
    get_delete_document_handler,
    get_assign_document_handler,
    get_document_by_id_handler,
    get_list_documents_handler,
    get_count_documents_handler,
)
from src.domain.commands import UploadDocument, ExportDocument, DeleteDocument
from src.application.queries.document_queries import GetDocumentById, ListDocuments
from src.application.queries.base import PaginationParams

router = APIRouter()


@router.post("/documents", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    title: str = Form(...),
    description: Optional[str] = Form(None),
    policy_repository_id: Optional[UUID] = Form(None),
    upload_handler=Depends(get_upload_document_handler),
    query_handler=Depends(get_document_by_id_handler),
):
    content = await file.read()

    command = UploadDocument(
        filename=file.filename or title,
        content=content,
        content_type=file.content_type or "application/octet-stream",
        uploaded_by="anonymous",
        policy_repository_id=policy_repository_id,
    )

    document_id = await upload_handler.handle(command)
    
    query = GetDocumentById(document_id=document_id.value)
    document = await query_handler.handle(query)
    
    if document is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Document created but could not be retrieved",
        )

    return DocumentResponse(
        id=document.id,
        title=document.title or title,
        description=document.description or description,
        status=document.status,
        version=document.version,
        original_format=document.original_format,
        compliance_status=document.compliance_status,
        created_at=document.created_at,
        updated_at=document.updated_at,
    )


@router.get("/documents", response_model=DocumentListResponse)
async def list_documents(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    status_filter: Optional[str] = Query(None, alias="status"),
    policy_repository_id: Optional[UUID] = None,
    list_handler=Depends(get_list_documents_handler),
    count_handler=Depends(get_count_documents_handler),
):
    from src.application.queries.document_queries import ListDocuments, CountDocuments

    pagination = PaginationParams(limit=per_page, offset=(page - 1) * per_page)
    query = ListDocuments(
        status=status_filter,
        policy_repository_id=policy_repository_id,
        pagination=pagination,
    )
    count_query = CountDocuments(
        status=status_filter,
        policy_repository_id=policy_repository_id,
    )

    documents = await list_handler.handle(query)
    total = await count_handler.handle(count_query)

    return DocumentListResponse(
        documents=[
            DocumentResponse(
                id=doc.id,
                title=doc.title,
                description=doc.description,
                status=doc.status,
                version=doc.version,
                original_format=doc.original_format,
                compliance_status=doc.compliance_status,
                created_at=doc.created_at,
                updated_at=doc.updated_at,
            )
            for doc in documents
        ],
        total=total,
        page=page,
        per_page=per_page,
    )


@router.get("/documents/{document_id}", response_model=DocumentDetailResponse)
async def get_document(
    document_id: UUID,
    handler=Depends(get_document_by_id_handler),
):
    query = GetDocumentById(document_id=document_id)
    document = await handler.handle(query)

    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID {document_id} not found",
        )

    sections = None
    if document.sections:
        from src.api.schemas.documents import SectionResponse
        sections = [
            SectionResponse(
                title=s.get("title", ""),
                content=s.get("content", ""),
                level=s.get("level", 1),
            )
            for s in document.sections
            if isinstance(s, dict)
        ]

    return DocumentDetailResponse(
        id=document.id,
        title=document.title,
        description=document.description,
        status=document.status,
        version=document.version,
        original_format=document.original_format,
        markdown_content=document.markdown_content,
        sections=sections,
        metadata=document.metadata,
        compliance_status=document.compliance_status,
        created_at=document.created_at,
        updated_at=document.updated_at,
    )


@router.patch("/documents/{document_id}", response_model=DocumentResponse)
async def update_document(
    document_id: UUID,
    request: DocumentUpdateRequest,
    handler=Depends(get_document_by_id_handler),
):
    query = GetDocumentById(document_id=document_id)
    document = await handler.handle(query)

    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID {document_id} not found",
        )

    return DocumentResponse(
        id=document.id,
        title=request.title or document.title,
        description=request.description or document.description,
        status=document.status,
        version=document.version,
        original_format=document.original_format,
        compliance_status=document.compliance_status,
        created_at=document.created_at,
        updated_at=document.updated_at,
    )


@router.delete("/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: UUID,
    handler=Depends(get_delete_document_handler),
):
    command = DeleteDocument(document_id=document_id, deleted_by="anonymous")
    await handler.handle(command)
    return None


@router.get("/documents/{document_id}/content", response_model=DocumentContentResponse)
async def get_document_content(
    document_id: UUID,
    format: str = Query("markdown", pattern="^(markdown|original)$"),
    handler=Depends(get_document_by_id_handler),
):
    query = GetDocumentById(document_id=document_id)
    document = await handler.handle(query)

    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID {document_id} not found",
        )

    sections = None
    if document.sections:
        from src.api.schemas.documents import SectionResponse
        sections = [
            SectionResponse(
                title=s.get("title", ""),
                content=s.get("content", ""),
                level=s.get("level", 1),
            )
            for s in document.sections
            if isinstance(s, dict)
        ]

    return DocumentContentResponse(
        document_id=document.id,
        format=format,
        content=document.markdown_content or "",
        sections=sections,
    )


@router.post("/documents/{document_id}/export")
async def export_document(
    document_id: UUID,
    request: ExportDocumentRequest,
    handler=Depends(get_export_document_handler),
):
    command = ExportDocument(
        document_id=document_id,
        export_format=request.format,
        exported_by="anonymous",
        include_feedback_history=request.include_feedback_history,
    )

    await handler.handle(command)

    return {"message": "Export completed", "format": request.format}


@router.put("/documents/{document_id}/policy-repository", response_model=DocumentResponse)
async def assign_policy_repository(
    document_id: UUID,
    policy_repository_id: UUID,
    assign_handler=Depends(get_assign_document_handler),
    query_handler=Depends(get_document_by_id_handler),
):
    from src.domain.commands import AssignDocumentToPolicy
    
    command = AssignDocumentToPolicy(
        document_id=document_id,
        repository_id=policy_repository_id,
        assigned_by="anonymous",
    )
    
    await assign_handler.handle(command)
    
    query = GetDocumentById(document_id=document_id)
    document = await query_handler.handle(query)

    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID {document_id} not found",
        )

    return DocumentResponse(
        id=document.id,
        title=document.title,
        description=document.description,
        status=document.status,
        version=document.version,
        original_format=document.original_format,
        compliance_status=document.compliance_status,
        created_at=document.created_at,
        updated_at=document.updated_at,
    )


@router.delete("/documents/{document_id}/policy-repository", status_code=status.HTTP_204_NO_CONTENT)
async def remove_policy_repository(
    document_id: UUID,
    handler=Depends(get_document_by_id_handler),
):
    query = GetDocumentById(document_id=document_id)
    document = await handler.handle(query)

    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID {document_id} not found",
        )

    return None
