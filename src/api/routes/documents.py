from typing import Optional
from uuid import UUID
from io import BytesIO
import logging

from fastapi import APIRouter, Depends, UploadFile, File, Form, Query, HTTPException, status
from fastapi.responses import StreamingResponse, Response

from src.api.schemas.documents import (
    DocumentResponse,
    DocumentDetailResponse,
    DocumentListResponse,
    DocumentContentResponse,
    DocumentUpdateRequest,
    ExportDocumentRequest,
    AssignPolicyRepositoryRequest,
    ShareDocumentRequest,
    ShareDocumentResponse,
    MakePrivateResponse,
)
from src.api.dependencies import (
    get_upload_document_handler,
    get_export_document_handler,
    get_delete_document_handler,
    get_assign_document_handler,
    get_document_by_id_handler,
    get_list_documents_handler,
    get_count_documents_handler,
    get_container,
    get_authorization_service,
    get_document_repository,
    get_current_user,
)
from src.domain.aggregates.user import User
from src.api.config import get_settings
from src.api.utils.validation import validate_upload_file
from src.domain.commands import UploadDocument, ExportDocument, DeleteDocument
from src.application.queries.document_queries import GetDocumentById, ListDocuments
from src.application.queries.base import PaginationParams

router = APIRouter()
logger = logging.getLogger(__name__)


def mime_type_to_document_format(mime_type: str) -> "DocumentFormat":
    """Convert MIME type to DocumentFormat enum."""
    from src.infrastructure.converters.base import DocumentFormat

    mime_map = {
        "application/pdf": DocumentFormat.PDF,
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": DocumentFormat.WORD,
        "application/msword": DocumentFormat.WORD,
        "text/markdown": DocumentFormat.MARKDOWN,
        "text/x-rst": DocumentFormat.RST,
    }

    return mime_map.get(mime_type, DocumentFormat.UNKNOWN)


@router.post("/documents", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    title: str = Form(...),
    description: Optional[str] = Form(None),
    policy_repository_id: Optional[UUID] = Form(None),
    current_user: User = Depends(get_current_user),
    upload_handler=Depends(get_upload_document_handler),
    query_handler=Depends(get_document_by_id_handler),
):
    """
    Upload a document for analysis.

    Validates:
    - File size (must be <= MAX_UPLOAD_SIZE from config)
    - Filename (sanitized to prevent path traversal)
    - Content type (must be in allowed list)
    - Title length (max 255 characters)
    - Description length (max 2000 characters)

    Args:
        file: The document file to upload
        title: Document title (required, max 255 characters)
        description: Optional description (max 2000 characters)
        policy_repository_id: Optional policy repository to use for analysis

    Returns:
        DocumentResponse with the created document details

    Raises:
        HTTPException 400: Invalid input (bad filename, title, or description)
        HTTPException 413: File too large
        HTTPException 415: Unsupported file type
    """
    # Get configuration settings
    settings = get_settings()

    # Read file content (we need size for validation)
    content = await file.read()
    file_size = len(content)

    # Log upload attempt for security auditing
    logger.info(
        f"Document upload attempt: filename='{file.filename}', "
        f"content_type='{file.content_type}', size={file_size:,} bytes, "
        f"title='{title}'"
    )

    # Comprehensive input validation
    try:
        sanitized_filename = validate_upload_file(
            filename=file.filename,
            content_type=file.content_type,
            file_size=file_size,
            max_size=settings.MAX_UPLOAD_SIZE,
            title=title,
            description=description,
        )
    except HTTPException as e:
        # Log validation failure for security monitoring
        logger.warning(
            f"Document upload validation failed: {e.detail} "
            f"(filename='{file.filename}', size={file_size:,} bytes)"
        )
        raise

    logger.info(
        f"Document upload validation passed: original_filename='{file.filename}', "
        f"sanitized_filename='{sanitized_filename}', size={file_size:,} bytes"
    )

    # Create upload command with validated and sanitized inputs
    command = UploadDocument(
        filename=sanitized_filename,
        content=content,
        content_type=file.content_type or "application/octet-stream",
        uploaded_by=current_user.kerberos_id,
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
    current_user: User = Depends(get_current_user),
    handler=Depends(get_document_by_id_handler),
    auth_service=Depends(get_authorization_service),
    doc_repo=Depends(get_document_repository),
):
    query = GetDocumentById(document_id=document_id)
    document = await handler.handle(query)

    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID {document_id} not found",
        )
    
    # Load document aggregate for authorization check
    doc_aggregate = await doc_repo.get_by_id(document_id)
    if doc_aggregate is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID {document_id} not found",
        )
    
    # Check authorization
    if not auth_service.can_view_document(current_user, doc_aggregate):
        logger.warning(
            f"User {current_user.kerberos_id} denied access to document {document_id}"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to view this document",
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
    current_user: User = Depends(get_current_user),
    handler=Depends(get_document_by_id_handler),
    auth_service=Depends(get_authorization_service),
    doc_repo=Depends(get_document_repository),
):
    query = GetDocumentById(document_id=document_id)
    document = await handler.handle(query)

    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID {document_id} not found",
        )
    
    # Load document aggregate for authorization check
    doc_aggregate = await doc_repo.get_by_id(document_id)
    if doc_aggregate is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID {document_id} not found",
        )
    
    # Check authorization
    if not auth_service.can_edit_document(current_user, doc_aggregate):
        logger.warning(
            f"User {current_user.kerberos_id} denied edit access to document {document_id}"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to edit this document",
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
    current_user: User = Depends(get_current_user),
    handler=Depends(get_delete_document_handler),
    auth_service=Depends(get_authorization_service),
    doc_repo=Depends(get_document_repository),
):
    # Load document aggregate for authorization check
    doc_aggregate = await doc_repo.get_by_id(document_id)
    if doc_aggregate is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID {document_id} not found",
        )
    
    # Check authorization
    if not auth_service.can_delete_document(current_user, doc_aggregate):
        logger.warning(
            f"User {current_user.kerberos_id} denied delete access to document {document_id}"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to delete this document",
        )
    
    command = DeleteDocument(document_id=document_id, deleted_by=current_user.kerberos_id)
    await handler.handle(command)
    return None


@router.post("/documents/{document_id}/share", response_model=ShareDocumentResponse)
async def share_document(
    document_id: UUID,
    request: ShareDocumentRequest,
    current_user: User = Depends(get_current_user),
    auth_service=Depends(get_authorization_service),
    doc_repo=Depends(get_document_repository),
):
    """
    Share document with specified groups.
    
    Only document owner or admins can share documents.
    Users can only share with groups they belong to (unless admin).
    
    Args:
        document_id: UUID of document to share
        request: ShareDocumentRequest with list of groups
        current_user: Authenticated user
        
    Returns:
        ShareDocumentResponse with updated sharing status
        
    Raises:
        HTTPException 404: Document not found
        HTTPException 403: User cannot share document or not in specified groups
        HTTPException 400: Invalid group names
    """
    # Load document aggregate
    doc_aggregate = await doc_repo.get_by_id(document_id)
    if doc_aggregate is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID {document_id} not found",
        )
    
    # Check if user can share this document
    if not auth_service.can_share_document(current_user, doc_aggregate):
        logger.warning(
            f"User {current_user.kerberos_id} denied share access to document {document_id}"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to share this document",
        )
    
    # Validate that user is in all specified groups (unless admin)
    from src.domain.value_objects.user_role import UserRole
    if not current_user.has_role(UserRole.ADMIN):
        user_groups_set = set(current_user.groups)
        requested_groups_set = set(request.groups)
        invalid_groups = requested_groups_set - user_groups_set
        
        if invalid_groups:
            logger.warning(
                f"User {current_user.kerberos_id} attempted to share document {document_id} "
                f"with groups they don't belong to: {invalid_groups}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"You can only share with groups you belong to. Invalid groups: {', '.join(invalid_groups)}",
            )
    
    # Share with each group
    for group in request.groups:
        doc_aggregate.share_with_group(group, current_user.kerberos_id)
    
    # Save the aggregate (which publishes events)
    await doc_repo.save(doc_aggregate)
    
    logger.info(
        f"User {current_user.kerberos_id} shared document {document_id} "
        f"with groups: {', '.join(request.groups)}"
    )
    
    return ShareDocumentResponse(
        document_id=document_id,
        shared_with_groups=list(doc_aggregate.shared_with_groups),
        visibility=doc_aggregate.visibility,
        message=f"Document shared with {len(request.groups)} group(s)",
    )


@router.post("/documents/{document_id}/make-private", response_model=MakePrivateResponse)
async def make_document_private(
    document_id: UUID,
    current_user: User = Depends(get_current_user),
    auth_service=Depends(get_authorization_service),
    doc_repo=Depends(get_document_repository),
):
    """
    Make document private (remove all group sharing).
    
    Only document owner or admins can make documents private.
    
    Args:
        document_id: UUID of document to make private
        current_user: Authenticated user
        
    Returns:
        MakePrivateResponse with updated status
        
    Raises:
        HTTPException 404: Document not found
        HTTPException 403: User cannot modify sharing for this document
    """
    # Load document aggregate
    doc_aggregate = await doc_repo.get_by_id(document_id)
    if doc_aggregate is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID {document_id} not found",
        )
    
    # Check if user can share/modify sharing for this document
    if not auth_service.can_share_document(current_user, doc_aggregate):
        logger.warning(
            f"User {current_user.kerberos_id} denied permission to make document {document_id} private"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to modify sharing for this document",
        )
    
    # Make document private
    doc_aggregate.make_private(current_user.kerberos_id)
    
    # Save the aggregate (which publishes events)
    await doc_repo.save(doc_aggregate)
    
    logger.info(
        f"User {current_user.kerberos_id} made document {document_id} private"
    )
    
    return MakePrivateResponse(
        document_id=document_id,
        visibility=doc_aggregate.visibility,
        message="Document is now private",
    )


@router.get("/documents/{document_id}/content", response_model=DocumentContentResponse)
async def get_document_content(
    document_id: UUID,
    format: str = Query("markdown", pattern="^(markdown|original)$"),
    current_user: User = Depends(get_current_user),
    handler=Depends(get_document_by_id_handler),
    auth_service=Depends(get_authorization_service),
    doc_repo=Depends(get_document_repository),
):
    # Check authorization first
    doc_aggregate = await doc_repo.get_by_id(document_id)
    if doc_aggregate is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID {document_id} not found",
        )
    
    if not auth_service.can_view_document(current_user, doc_aggregate):
        logger.warning(
            f"User {current_user.kerberos_id} denied access to content of document {document_id}"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to view this document",
        )
    
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
    current_user: User = Depends(get_current_user),
    handler=Depends(get_export_document_handler),
    auth_service=Depends(get_authorization_service),
    doc_repo=Depends(get_document_repository),
):
    # Check authorization first
    doc_aggregate = await doc_repo.get_by_id(document_id)
    if doc_aggregate is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID {document_id} not found",
        )
    
    if not auth_service.can_view_document(current_user, doc_aggregate):
        logger.warning(
            f"User {current_user.kerberos_id} denied export access to document {document_id}"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to export this document",
        )
    
    command = ExportDocument(
        document_id=document_id,
        export_format=request.format,
        exported_by=current_user.kerberos_id,
    )

    await handler.handle(command)

    return {"message": "Export completed", "format": request.format}


@router.get("/documents/{document_id}/download")
async def download_original_document(
    document_id: UUID,
    current_user: User = Depends(get_current_user),
    handler=Depends(get_document_by_id_handler),
    auth_service=Depends(get_authorization_service),
    doc_repo=Depends(get_document_repository),
):
    """Download the original uploaded document file."""
    # Check authorization first
    doc_aggregate = await doc_repo.get_by_id(document_id)
    if doc_aggregate is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID {document_id} not found",
        )
    
    if not auth_service.can_view_document(current_user, doc_aggregate):
        logger.warning(
            f"User {current_user.kerberos_id} denied download access to document {document_id}"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to download this document",
        )
    
    query = GetDocumentById(document_id=document_id)
    document = await handler.handle(query)

    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID {document_id} not found",
        )

    # Get the original content from the database
    container = await get_container()
    conn = await container.db_pool.acquire()

    try:
        row = await conn.fetchrow("""
            SELECT original_content
            FROM document_contents
            WHERE document_id = $1
            ORDER BY version DESC
            LIMIT 1
        """, document_id)

        if not row or not row['original_content']:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Original file content not found",
            )

        original_content = bytes(row['original_content'])

        # Determine filename and content type
        filename = document.title or "document"
        content_type = document.original_format or "application/octet-stream"

        # Add appropriate extension if not present
        if not any(filename.endswith(ext) for ext in ['.pdf', '.docx', '.doc', '.md', '.rst', '.txt']):
            ext_map = {
                'application/pdf': '.pdf',
                'application/vnd.openxmlformats-officedocument.wordprocessingml.document': '.docx',
                'application/msword': '.doc',
                'text/markdown': '.md',
                'text/x-rst': '.rst',
            }
            filename += ext_map.get(content_type, '.bin')

        return Response(
            content=original_content,
            media_type=content_type,
            headers={
                'Content-Disposition': f'attachment; filename="{filename}"',
                'Content-Length': str(len(original_content)),
            }
        )
    finally:
        await container.db_pool.release(conn)


@router.put("/documents/{document_id}/policy-repository", response_model=DocumentResponse)
async def assign_policy_repository(
    document_id: UUID,
    request: AssignPolicyRepositoryRequest,
    assign_handler=Depends(get_assign_document_handler),
    query_handler=Depends(get_document_by_id_handler),
):
    from src.domain.commands import AssignDocumentToPolicy
    
    command = AssignDocumentToPolicy(
        document_id=document_id,
        repository_id=request.policy_repository_id,
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


@router.get("/documents/{document_id}/semantic-ir")
async def get_document_semantic_ir(
    document_id: UUID,
    format: str = Query("json", pattern="^(json|llm-text)$"),
    handler=Depends(get_document_by_id_handler),
):
    """
    Retrieve the semantic intermediate representation (IR) for a document.

    Args:
        document_id: UUID of the document
        format: Output format - 'json' for structured data or 'llm-text' for LLM-optimized text

    Returns:
        Semantic IR in requested format
    """
    from src.infrastructure.semantic import IRBuilder
    from src.infrastructure.converters.converter_factory import ConverterFactory

    query = GetDocumentById(document_id=document_id)
    document = await handler.handle(query)

    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID {document_id} not found",
        )

    if not document.markdown_content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Document has not been converted yet",
        )

    # Rebuild IR from document data
    try:
        container = await get_container()

        # Get conversion result from document
        from src.infrastructure.converters.base import (
            ConversionResult,
            DocumentSection,
            DocumentMetadata,
            DocumentFormat,
        )

        sections = []
        if document.sections:
            for s in document.sections:
                if isinstance(s, dict):
                    sections.append(
                        DocumentSection(
                            id=s.get("id", ""),
                            title=s.get("title", ""),
                            content=s.get("content", ""),
                            level=s.get("level", 1),
                            start_line=s.get("start_line"),
                            end_line=s.get("end_line"),
                        )
                    )

        metadata_dict = document.metadata or {}
        metadata = DocumentMetadata(
            title=document.title,
            author=metadata_dict.get("author"),
            created_date=metadata_dict.get("created_date"),
            modified_date=metadata_dict.get("modified_date"),
            page_count=metadata_dict.get("page_count", 0),
            word_count=metadata_dict.get("word_count", 0),
            original_format=mime_type_to_document_format(document.original_format) if document.original_format else DocumentFormat.UNKNOWN,
        )

        conversion_result = ConversionResult(
            success=True,
            markdown_content=document.markdown_content,
            sections=sections,
            metadata=metadata,
        )

        # Build IR
        ir_builder = IRBuilder()
        ir = ir_builder.build(conversion_result, str(document_id))

        if format == "llm-text":
            return Response(
                content=ir.to_llm_format(),
                media_type="text/plain",
            )
        else:
            return ir.to_dict()

    except Exception as e:
        logger.exception(f"Error generating semantic IR: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate semantic IR: {str(e)}",
        )


@router.get("/documents/{document_id}/semantic-ir/download")
async def download_semantic_ir(
    document_id: UUID,
    format: str = Query("json", pattern="^(json|llm-text|markdown)$"),
    handler=Depends(get_document_by_id_handler),
):
    """
    Download the semantic intermediate representation as a file.

    Args:
        document_id: UUID of the document
        format: Output format - 'json', 'llm-text', or 'markdown'

    Returns:
        Downloadable file with semantic IR
    """
    from src.infrastructure.semantic import IRBuilder
    import json

    query = GetDocumentById(document_id=document_id)
    document = await handler.handle(query)

    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID {document_id} not found",
        )

    if not document.markdown_content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Document has not been converted yet",
        )

    # Rebuild IR from document data
    try:
        from src.infrastructure.converters.base import (
            ConversionResult,
            DocumentSection,
            DocumentMetadata,
            DocumentFormat,
        )

        sections = []
        if document.sections:
            for s in document.sections:
                if isinstance(s, dict):
                    sections.append(
                        DocumentSection(
                            id=s.get("id", ""),
                            title=s.get("title", ""),
                            content=s.get("content", ""),
                            level=s.get("level", 1),
                            start_line=s.get("start_line"),
                            end_line=s.get("end_line"),
                        )
                    )

        metadata_dict = document.metadata or {}
        metadata = DocumentMetadata(
            title=document.title,
            author=metadata_dict.get("author"),
            created_date=metadata_dict.get("created_date"),
            modified_date=metadata_dict.get("modified_date"),
            page_count=metadata_dict.get("page_count", 0),
            word_count=metadata_dict.get("word_count", 0),
            original_format=mime_type_to_document_format(document.original_format) if document.original_format else DocumentFormat.UNKNOWN,
        )

        conversion_result = ConversionResult(
            success=True,
            markdown_content=document.markdown_content,
            sections=sections,
            metadata=metadata,
        )

        # Build IR
        ir_builder = IRBuilder()
        ir = ir_builder.build(conversion_result, str(document_id))

        # Determine content and filename
        filename = f"{document.title or 'document'}_semantic_ir"

        if format == "json":
            content = json.dumps(ir.to_dict(), indent=2)
            media_type = "application/json"
            filename += ".json"
        elif format == "llm-text":
            content = ir.to_llm_format()
            media_type = "text/plain"
            filename += ".txt"
        else:  # markdown
            content = ir.raw_markdown
            media_type = "text/markdown"
            filename += ".md"

        return Response(
            content=content.encode('utf-8') if isinstance(content, str) else content,
            media_type=media_type,
            headers={
                'Content-Disposition': f'attachment; filename="{filename}"',
            }
        )

    except Exception as e:
        logger.exception(f"Error downloading semantic IR: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to download semantic IR: {str(e)}",
        )
