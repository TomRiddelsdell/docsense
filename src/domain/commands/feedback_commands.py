from dataclasses import dataclass, field
from uuid import UUID

from .base import Command


@dataclass(frozen=True)
class AcceptChange(Command):
    document_id: UUID = field(default=None)
    feedback_id: UUID = field(default=None)
    accepted_by: str = ""


@dataclass(frozen=True)
class RejectChange(Command):
    document_id: UUID = field(default=None)
    feedback_id: UUID = field(default=None)
    rejected_by: str = ""
    reason: str = ""


@dataclass(frozen=True)
class ModifyChange(Command):
    document_id: UUID = field(default=None)
    feedback_id: UUID = field(default=None)
    modified_by: str = ""
    modified_content: str = ""
