from dataclasses import dataclass, field
from uuid import UUID

from .base import DomainEvent


@dataclass(frozen=True)
class FeedbackGenerated(DomainEvent):
    feedback_id: UUID = field(default=None)
    issue_description: str = ""
    suggested_change: str = ""
    confidence_score: float = 0.0
    policy_reference: str = ""
    section_reference: str = ""
    aggregate_type: str = field(default="FeedbackSession")


@dataclass(frozen=True)
class ChangeAccepted(DomainEvent):
    feedback_id: UUID = field(default=None)
    accepted_by: str = ""
    applied_change: str = ""
    aggregate_type: str = field(default="FeedbackSession")


@dataclass(frozen=True)
class ChangeRejected(DomainEvent):
    feedback_id: UUID = field(default=None)
    rejected_by: str = ""
    rejection_reason: str = ""
    aggregate_type: str = field(default="FeedbackSession")


@dataclass(frozen=True)
class ChangeModified(DomainEvent):
    feedback_id: UUID = field(default=None)
    modified_by: str = ""
    original_change: str = ""
    modified_change: str = ""
    aggregate_type: str = field(default="FeedbackSession")
