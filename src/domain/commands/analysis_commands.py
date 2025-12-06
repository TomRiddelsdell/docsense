from dataclasses import dataclass, field
from uuid import UUID

from .base import Command


@dataclass(frozen=True)
class StartAnalysis(Command):
    document_id: UUID = field(default=None)
    policy_repository_id: UUID = field(default=None)
    initiated_by: str = ""
    ai_model: str = "gemini-pro"


@dataclass(frozen=True)
class CancelAnalysis(Command):
    document_id: UUID = field(default=None)
    cancelled_by: str = ""
    reason: str = ""
