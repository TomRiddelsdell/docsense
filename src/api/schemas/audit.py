from datetime import datetime
from typing import Optional, List, Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class AuditEntry(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    event_type: str
    document_id: Optional[UUID] = None
    user_id: Optional[str] = None
    details: Optional[dict] = None
    timestamp: datetime


class AuditTrailResponse(BaseModel):
    entries: List[AuditEntry]
    total: int
    page: Optional[int] = None
    per_page: Optional[int] = None
