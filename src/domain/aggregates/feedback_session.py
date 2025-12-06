from typing import List, Dict, Any, Optional
from uuid import UUID

from .base import Aggregate
from src.domain.events.base import DomainEvent
from src.domain.events.feedback_events import (
    FeedbackGenerated,
    ChangeAccepted,
    ChangeRejected,
    ChangeModified,
)


class FeedbackSession(Aggregate):
    def __init__(self, session_id: UUID):
        super().__init__(session_id)
        self._document_id: Optional[UUID] = None
        self._feedback_items: List[Dict[str, Any]] = []

    @property
    def document_id(self) -> Optional[UUID]:
        return self._document_id

    @property
    def feedback_items(self) -> List[Dict[str, Any]]:
        return self._feedback_items

    @classmethod
    def create_for_document(
        cls,
        session_id: UUID,
        document_id: UUID,
    ) -> "FeedbackSession":
        session = cls(session_id)
        session._document_id = document_id
        return session

    def add_feedback(
        self,
        feedback_id: UUID,
        issue_description: str,
        suggested_change: str,
        confidence_score: float,
        policy_reference: str,
        section_reference: str,
    ) -> None:
        self._apply_event(
            FeedbackGenerated(
                aggregate_id=self._id,
                feedback_id=feedback_id,
                issue_description=issue_description,
                suggested_change=suggested_change,
                confidence_score=confidence_score,
                policy_reference=policy_reference,
                section_reference=section_reference,
            )
        )

    def accept_change(
        self,
        feedback_id: UUID,
        accepted_by: str,
        applied_change: str,
    ) -> None:
        self._apply_event(
            ChangeAccepted(
                aggregate_id=self._id,
                feedback_id=feedback_id,
                accepted_by=accepted_by,
                applied_change=applied_change,
            )
        )

    def reject_change(
        self,
        feedback_id: UUID,
        rejected_by: str,
        rejection_reason: str,
    ) -> None:
        self._apply_event(
            ChangeRejected(
                aggregate_id=self._id,
                feedback_id=feedback_id,
                rejected_by=rejected_by,
                rejection_reason=rejection_reason,
            )
        )

    def _find_feedback_index(self, feedback_id: UUID) -> int:
        for i, item in enumerate(self._feedback_items):
            if item["feedback_id"] == feedback_id:
                return i
        return -1

    def _when(self, event: DomainEvent) -> None:
        if isinstance(event, FeedbackGenerated):
            self._feedback_items.append({
                "feedback_id": event.feedback_id,
                "issue_description": event.issue_description,
                "suggested_change": event.suggested_change,
                "confidence_score": event.confidence_score,
                "policy_reference": event.policy_reference,
                "section_reference": event.section_reference,
                "status": "PENDING",
            })
        elif isinstance(event, ChangeAccepted):
            idx = self._find_feedback_index(event.feedback_id)
            if idx >= 0:
                self._feedback_items[idx]["status"] = "ACCEPTED"
                self._feedback_items[idx]["applied_change"] = event.applied_change
        elif isinstance(event, ChangeRejected):
            idx = self._find_feedback_index(event.feedback_id)
            if idx >= 0:
                self._feedback_items[idx]["status"] = "REJECTED"
                self._feedback_items[idx]["rejection_reason"] = event.rejection_reason
        elif isinstance(event, ChangeModified):
            idx = self._find_feedback_index(event.feedback_id)
            if idx >= 0:
                self._feedback_items[idx]["status"] = "MODIFIED"
                self._feedback_items[idx]["modified_change"] = event.modified_change
