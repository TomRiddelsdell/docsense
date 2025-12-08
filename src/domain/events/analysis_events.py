from dataclasses import dataclass, field
from typing import List, Dict, Any
from uuid import UUID

from .base import DomainEvent


@dataclass(frozen=True)
class AnalysisStarted(DomainEvent):
    policy_repository_id: UUID = field(default=None)
    ai_model: str = ""
    initiated_by: str = ""
    aggregate_type: str = field(default="Document")


@dataclass(frozen=True)
class AnalysisCompleted(DomainEvent):
    findings_count: int = 0
    compliance_score: float = 0.0
    findings: List[Dict[str, Any]] = field(default_factory=list)
    processing_time_ms: int = 0
    aggregate_type: str = field(default="Document")


@dataclass(frozen=True)
class AnalysisFailed(DomainEvent):
    error_message: str = ""
    error_code: str = ""
    retryable: bool = False
    aggregate_type: str = field(default="Document")


@dataclass(frozen=True)
class AnalysisReset(DomainEvent):
    reset_by: str = ""
    previous_status: str = ""
    aggregate_type: str = field(default="Document")
