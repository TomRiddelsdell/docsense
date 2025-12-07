from datetime import datetime
from typing import Optional, List, Any
from uuid import UUID

from pydantic import BaseModel, Field


class DocumentUploadRequest(BaseModel):
    title: str = Field(..., max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    tags: Optional[List[str]] = None
    policy_repository_id: Optional[UUID] = None


class DocumentUpdateRequest(BaseModel):
    title: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    tags: Optional[List[str]] = None


class ExportDocumentRequest(BaseModel):
    format: str = Field(..., pattern="^(pdf|docx|md)$")
    include_feedback_history: bool = False


class PolicyRepositorySummary(BaseModel):
    id: UUID
    name: str


class DocumentResponse(BaseModel):
    id: UUID
    title: str
    description: Optional[str] = None
    status: str
    version: int
    original_format: Optional[str] = None
    policy_repository: Optional[PolicyRepositorySummary] = None
    compliance_status: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SectionResponse(BaseModel):
    title: str
    content: str
    level: int = 1


class DocumentDetailResponse(DocumentResponse):
    markdown_content: Optional[str] = None
    sections: Optional[List[SectionResponse]] = None
    metadata: Optional[dict] = None


class DocumentContentResponse(BaseModel):
    document_id: UUID
    format: str
    content: str
    sections: Optional[List[SectionResponse]] = None


class DocumentListResponse(BaseModel):
    documents: List[DocumentResponse]
    total: int
    page: int = 1
    per_page: int = 20
