from uuid import UUID
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

from src.infrastructure.ai.analysis.analysis_log import AnalysisLogStore

router = APIRouter()


class LogEntryResponse(BaseModel):
    id: str
    timestamp: str
    level: str
    stage: str
    message: str
    details: Optional[dict] = None


class AnalysisLogResponse(BaseModel):
    document_id: str
    started_at: str
    completed_at: Optional[str] = None
    status: str
    entries: List[LogEntryResponse]


@router.get("/documents/{document_id}/analysis-logs", response_model=AnalysisLogResponse)
async def get_analysis_logs(document_id: UUID):
    store = AnalysisLogStore.get_instance()
    log = store.get_log(document_id)
    
    if log is None:
        return AnalysisLogResponse(
            document_id=str(document_id),
            started_at=datetime.utcnow().isoformat(),
            completed_at=None,
            status="not_started",
            entries=[],
        )
    
    return AnalysisLogResponse(
        document_id=str(log.document_id),
        started_at=log.started_at.isoformat(),
        completed_at=log.completed_at.isoformat() if log.completed_at else None,
        status=log.status,
        entries=[
            LogEntryResponse(
                id=str(e.id),
                timestamp=e.timestamp.isoformat(),
                level=e.level.value,
                stage=e.stage,
                message=e.message,
                details=e.details,
            )
            for e in log.entries
        ],
    )
