from typing import Type
from uuid import UUID

from src.domain.aggregates.feedback_session import FeedbackSession
from src.domain.value_objects import FeedbackItem
from src.infrastructure.repositories.base import Repository


class FeedbackSessionRepository(Repository[FeedbackSession]):
    def _aggregate_type(self) -> Type[FeedbackSession]:
        return FeedbackSession

    def _aggregate_type_name(self) -> str:
        return "FeedbackSession"

    def _serialize_aggregate(self, aggregate: FeedbackSession) -> dict:
        """
        Serialize FeedbackSession using immutable FeedbackItem value objects.

        Uses FeedbackItem.to_dict() for proper serialization.
        """
        return {
            "id": str(aggregate.id),
            "version": aggregate.version,
            "document_id": str(aggregate.document_id) if aggregate.document_id else None,
            "feedback_items": [
                {
                    "feedback_id": str(item.feedback_id),
                    "issue_description": item.issue_description,
                    "suggested_change": item.suggested_change,
                    "confidence_score": item.confidence_score,
                    "policy_reference": item.policy_reference,
                    "section_reference": item.section_reference,
                    "status": item.status.value,
                    "applied_change": item.applied_change,
                    "rejection_reason": item.rejection_reason,
                    "modified_change": item.modified_change,
                }
                for item in aggregate.feedback_items
            ],
        }

    def _deserialize_aggregate(self, state: dict) -> FeedbackSession:
        """
        Deserialize FeedbackSession using immutable FeedbackItem value objects.

        Uses FeedbackItem.from_dict() for proper deserialization.
        """
        session = FeedbackSession.__new__(FeedbackSession)
        session._id = UUID(state["id"])
        session._version = state["version"]
        session._pending_events = []
        session._document_id = UUID(state["document_id"]) if state.get("document_id") else None
        session._feedback_items = [
            FeedbackItem.from_dict(item)
            for item in state["feedback_items"]
        ]
        return session
