"""
FeedbackItem value object for DDD compliance.

Immutable value object representing a single feedback item in a FeedbackSession.
Replaces mutable dict representation to enforce DDD principles.
"""
from dataclasses import dataclass
from typing import Optional
from uuid import UUID

from .feedback_status import FeedbackStatus


@dataclass(frozen=True)
class FeedbackItem:
    """
    Immutable feedback item value object.

    Represents a single piece of feedback with its complete state including
    the original suggestion and any modifications or actions taken.
    """
    feedback_id: UUID
    issue_description: str
    suggested_change: str
    confidence_score: float
    policy_reference: str
    section_reference: str
    status: FeedbackStatus
    applied_change: Optional[str] = None
    rejection_reason: Optional[str] = None
    modified_change: Optional[str] = None

    def __post_init__(self):
        """Validate feedback item invariants."""
        if not 0.0 <= self.confidence_score <= 1.0:
            raise ValueError(
                f"Confidence score must be between 0.0 and 1.0, got {self.confidence_score}"
            )

        if self.status == FeedbackStatus.ACCEPTED and self.applied_change is None:
            raise ValueError("Accepted feedback must have applied_change")

        if self.status == FeedbackStatus.REJECTED and self.rejection_reason is None:
            raise ValueError("Rejected feedback must have rejection_reason")

        if self.status == FeedbackStatus.MODIFIED and self.modified_change is None:
            raise ValueError("Modified feedback must have modified_change")

    def is_pending(self) -> bool:
        """Check if feedback is still pending."""
        return self.status == FeedbackStatus.PENDING

    def is_resolved(self) -> bool:
        """Check if feedback has been resolved (accepted, rejected, or modified)."""
        return self.status.is_resolved()

    def accept(self, applied_change: str) -> "FeedbackItem":
        """
        Create a new FeedbackItem with status changed to ACCEPTED.

        Returns a new instance - this is immutable.
        """
        return FeedbackItem(
            feedback_id=self.feedback_id,
            issue_description=self.issue_description,
            suggested_change=self.suggested_change,
            confidence_score=self.confidence_score,
            policy_reference=self.policy_reference,
            section_reference=self.section_reference,
            status=FeedbackStatus.ACCEPTED,
            applied_change=applied_change,
            rejection_reason=self.rejection_reason,
            modified_change=self.modified_change,
        )

    def reject(self, rejection_reason: str) -> "FeedbackItem":
        """
        Create a new FeedbackItem with status changed to REJECTED.

        Returns a new instance - this is immutable.
        """
        return FeedbackItem(
            feedback_id=self.feedback_id,
            issue_description=self.issue_description,
            suggested_change=self.suggested_change,
            confidence_score=self.confidence_score,
            policy_reference=self.policy_reference,
            section_reference=self.section_reference,
            status=FeedbackStatus.REJECTED,
            applied_change=self.applied_change,
            rejection_reason=rejection_reason,
            modified_change=self.modified_change,
        )

    def modify(self, modified_change: str) -> "FeedbackItem":
        """
        Create a new FeedbackItem with status changed to MODIFIED.

        Returns a new instance - this is immutable.
        """
        return FeedbackItem(
            feedback_id=self.feedback_id,
            issue_description=self.issue_description,
            suggested_change=self.suggested_change,
            confidence_score=self.confidence_score,
            policy_reference=self.policy_reference,
            section_reference=self.section_reference,
            status=FeedbackStatus.MODIFIED,
            applied_change=self.applied_change,
            rejection_reason=self.rejection_reason,
            modified_change=modified_change,
        )

    @classmethod
    def create_pending(
        cls,
        feedback_id: UUID,
        issue_description: str,
        suggested_change: str,
        confidence_score: float,
        policy_reference: str,
        section_reference: str,
    ) -> "FeedbackItem":
        """Create a new pending feedback item."""
        return cls(
            feedback_id=feedback_id,
            issue_description=issue_description,
            suggested_change=suggested_change,
            confidence_score=confidence_score,
            policy_reference=policy_reference,
            section_reference=section_reference,
            status=FeedbackStatus.PENDING,
            applied_change=None,
            rejection_reason=None,
            modified_change=None,
        )

    def to_dict(self) -> dict:
        """Convert to dict for serialization."""
        return {
            "feedback_id": self.feedback_id,
            "issue_description": self.issue_description,
            "suggested_change": self.suggested_change,
            "confidence_score": self.confidence_score,
            "policy_reference": self.policy_reference,
            "section_reference": self.section_reference,
            "status": self.status.value,
            "applied_change": self.applied_change,
            "rejection_reason": self.rejection_reason,
            "modified_change": self.modified_change,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "FeedbackItem":
        """Create from dict (for deserialization)."""
        return cls(
            feedback_id=data["feedback_id"] if isinstance(data["feedback_id"], UUID) else UUID(data["feedback_id"]),
            issue_description=data["issue_description"],
            suggested_change=data["suggested_change"],
            confidence_score=data["confidence_score"],
            policy_reference=data["policy_reference"],
            section_reference=data["section_reference"],
            status=FeedbackStatus(data["status"]) if isinstance(data["status"], str) else data["status"],
            applied_change=data.get("applied_change"),
            rejection_reason=data.get("rejection_reason"),
            modified_change=data.get("modified_change"),
        )
