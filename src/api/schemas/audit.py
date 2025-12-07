from datetime import datetime
from typing import Optional, List, Any
from uuid import UUID

from pydantic import BaseModel


class AuditEntry(BaseModel):
    id: UUID
    event_type: str
    document_id: Optional[UUID] = None
    user_id: Optional[str] = None
    details: Optional[dict] = None
    timestamp: datetime

    class Config:
        from_attributes = True


class AuditTrailResponse(BaseModel):
    entries: List[AuditEntry]
    total: int
    page: Optional[int] = None
    per_page: Optional[int] = None
