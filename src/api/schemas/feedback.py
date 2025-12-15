from datetime import datetime
from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class RejectFeedbackRequest(BaseModel):
    reason: Optional[str] = None


class FeedbackItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    document_id: UUID
    section_id: Optional[str] = None
    status: str
    category: Optional[str] = None
    severity: Optional[str] = None
    original_text: Optional[str] = None
    suggestion: str
    explanation: Optional[str] = None
    confidence_score: Optional[float] = None
    policy_reference: Optional[str] = None
    rejection_reason: Optional[str] = None
    processed_at: Optional[datetime] = None
    created_at: datetime


class FeedbackListResponse(BaseModel):
    items: List[FeedbackItemResponse]
    total: int
    pending_count: int
    accepted_count: int
    rejected_count: int
