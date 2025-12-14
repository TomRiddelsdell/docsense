from typing import List, Optional
from uuid import UUID

from .base import Aggregate
from src.domain.events.base import DomainEvent
from src.domain.events.feedback_events import (
    FeedbackSessionCreated,
    FeedbackGenerated,
    ChangeAccepted,
    ChangeRejected,
    ChangeModified,
)
from src.domain.exceptions.feedback_exceptions import (
    FeedbackNotFound,
    ChangeAlreadyProcessed,
)
from src.domain.value_objects import FeedbackItem, FeedbackStatus


class FeedbackSession(Aggregate):
    def __init__(self, session_id: UUID):
        super().__init__(session_id)
        self._document_id: Optional[UUID] = None
        self._feedback_items: List[FeedbackItem] = []

    @property
    def document_id(self) -> Optional[UUID]:
        return self._document_id

    @property
    def feedback_items(self) -> List[FeedbackItem]:
        """Return copy of feedback items list (items themselves are immutable)."""
        return self._feedback_items.copy()

    def _init_state(self) -> None:
        self._document_id = None
        self._feedback_items = []

    @classmethod
    def create_for_document(
        cls,
        session_id: UUID,
        document_id: UUID,
    ) -> "FeedbackSession":
        session = cls(session_id)
        session._apply_event(
            FeedbackSessionCreated(
                aggregate_id=session_id,
                document_id=document_id,
            )
        )
        return session

    def _find_feedback(self, feedback_id: UUID) -> Optional[FeedbackItem]:
        """Find feedback item by ID."""
        for item in self._feedback_items:
            if item.feedback_id == feedback_id:
                return item
        return None

    def _find_feedback_index(self, feedback_id: UUID) -> int:
        """Find index of feedback item by ID. Returns -1 if not found."""
        for i, item in enumerate(self._feedback_items):
            if item.feedback_id == feedback_id:
                return i
        return -1

    def _validate_feedback_pending(self, feedback_id: UUID) -> None:
        """Validate that feedback exists and is in PENDING status."""
        feedback = self._find_feedback(feedback_id)
        if feedback is None:
            raise FeedbackNotFound(feedback_id=feedback_id)
        if feedback.status != FeedbackStatus.PENDING:
            raise ChangeAlreadyProcessed(
                feedback_id=feedback_id,
                current_status=feedback.status.value
            )

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
        self._validate_feedback_pending(feedback_id)
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
        self._validate_feedback_pending(feedback_id)
        self._apply_event(
            ChangeRejected(
                aggregate_id=self._id,
                feedback_id=feedback_id,
                rejected_by=rejected_by,
                rejection_reason=rejection_reason,
            )
        )

    def modify_change(
        self,
        feedback_id: UUID,
        modified_by: str,
        modified_change: str,
        original_change: str = "",
    ) -> None:
        self._validate_feedback_pending(feedback_id)
        self._apply_event(
            ChangeModified(
                aggregate_id=self._id,
                feedback_id=feedback_id,
                modified_by=modified_by,
                original_change=original_change,
                modified_change=modified_change,
            )
        )

    def _when(self, event: DomainEvent) -> None:
        """
        Apply event to aggregate state using immutable value objects.

        Creates new lists instead of mutating existing ones to maintain DDD principles.
        """
        if isinstance(event, FeedbackSessionCreated):
            self._document_id = event.document_id

        elif isinstance(event, FeedbackGenerated):
            # Create new FeedbackItem and append to list
            new_item = FeedbackItem.create_pending(
                feedback_id=event.feedback_id,
                issue_description=event.issue_description,
                suggested_change=event.suggested_change,
                confidence_score=event.confidence_score,
                policy_reference=event.policy_reference,
                section_reference=event.section_reference,
            )
            self._feedback_items.append(new_item)

        elif isinstance(event, ChangeAccepted):
            # Find item and replace with accepted version (immutable update)
            idx = self._find_feedback_index(event.feedback_id)
            if idx >= 0:
                old_item = self._feedback_items[idx]
                accepted_item = old_item.accept(event.applied_change)
                # Create new list with updated item
                self._feedback_items = [
                    accepted_item if i == idx else item
                    for i, item in enumerate(self._feedback_items)
                ]

        elif isinstance(event, ChangeRejected):
            # Find item and replace with rejected version (immutable update)
            idx = self._find_feedback_index(event.feedback_id)
            if idx >= 0:
                old_item = self._feedback_items[idx]
                rejected_item = old_item.reject(event.rejection_reason)
                # Create new list with updated item
                self._feedback_items = [
                    rejected_item if i == idx else item
                    for i, item in enumerate(self._feedback_items)
                ]

        elif isinstance(event, ChangeModified):
            # Find item and replace with modified version (immutable update)
            idx = self._find_feedback_index(event.feedback_id)
            if idx >= 0:
                old_item = self._feedback_items[idx]
                modified_item = old_item.modify(event.modified_change)
                # Create new list with updated item
                self._feedback_items = [
                    modified_item if i == idx else item
                    for i, item in enumerate(self._feedback_items)
                ]
