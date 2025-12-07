from datetime import datetime
from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel, Field


class StartAnalysisRequest(BaseModel):
    model_provider: Optional[str] = Field(
        None, pattern="^(gemini|openai|anthropic)$"
    )
    focus_areas: Optional[List[str]] = None


class AnalysisProgress(BaseModel):
    current_step: str
    total_steps: int
    completed_steps: int
    percentage: float


class AnalysisIssue(BaseModel):
    id: UUID
    section: Optional[str] = None
    category: str
    severity: str
    description: str
    suggestion: Optional[str] = None


class AnalysisSessionResponse(BaseModel):
    document_id: UUID
    status: str
    model_provider: Optional[str] = None
    progress: Optional[AnalysisProgress] = None
    issues_found: int = 0
    issues: Optional[List[AnalysisIssue]] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
