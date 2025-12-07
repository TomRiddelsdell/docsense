from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List
from uuid import UUID, uuid4


class LogLevel(Enum):
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


@dataclass
class LogEntry:
    id: UUID
    timestamp: datetime
    level: LogLevel
    stage: str
    message: str
    details: Dict | None = None

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "timestamp": self.timestamp.isoformat(),
            "level": self.level.value,
            "stage": self.stage,
            "message": self.message,
            "details": self.details,
        }


@dataclass
class AnalysisLog:
    document_id: UUID
    started_at: datetime
    entries: List[LogEntry] = field(default_factory=list)
    completed_at: datetime | None = None
    status: str = "in_progress"

    def add_entry(
        self,
        level: LogLevel,
        stage: str,
        message: str,
        details: Dict | None = None,
    ) -> None:
        entry = LogEntry(
            id=uuid4(),
            timestamp=datetime.utcnow(),
            level=level,
            stage=stage,
            message=message,
            details=details,
        )
        self.entries.append(entry)

    def info(self, stage: str, message: str, details: Dict | None = None) -> None:
        self.add_entry(LogLevel.INFO, stage, message, details)

    def debug(self, stage: str, message: str, details: Dict | None = None) -> None:
        self.add_entry(LogLevel.DEBUG, stage, message, details)

    def warning(self, stage: str, message: str, details: Dict | None = None) -> None:
        self.add_entry(LogLevel.WARNING, stage, message, details)

    def error(self, stage: str, message: str, details: Dict | None = None) -> None:
        self.add_entry(LogLevel.ERROR, stage, message, details)

    def complete(self, status: str = "completed") -> None:
        self.completed_at = datetime.utcnow()
        self.status = status

    def to_dict(self) -> dict:
        return {
            "document_id": str(self.document_id),
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "status": self.status,
            "entries": [e.to_dict() for e in self.entries],
        }


class AnalysisLogStore:
    _instance: "AnalysisLogStore | None" = None
    
    def __init__(self):
        self._logs: Dict[UUID, AnalysisLog] = {}

    @classmethod
    def get_instance(cls) -> "AnalysisLogStore":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def create_log(self, document_id: UUID) -> AnalysisLog:
        log = AnalysisLog(
            document_id=document_id,
            started_at=datetime.utcnow(),
        )
        self._logs[document_id] = log
        return log

    def get_log(self, document_id: UUID) -> AnalysisLog | None:
        return self._logs.get(document_id)

    def get_or_create_log(self, document_id: UUID) -> AnalysisLog:
        if document_id not in self._logs:
            return self.create_log(document_id)
        return self._logs[document_id]

    def clear_log(self, document_id: UUID) -> None:
        if document_id in self._logs:
            del self._logs[document_id]

    def get_all_logs(self) -> List[AnalysisLog]:
        return list(self._logs.values())
