from typing import Type
from uuid import UUID

from src.domain.aggregates.feedback_session import FeedbackSession
from src.domain.value_objects import FeedbackStatus
from src.infrastructure.repositories.base import Repository


class FeedbackSessionRepository(Repository[FeedbackSession]):
    def _aggregate_type(self) -> Type[FeedbackSession]:
        return FeedbackSession

    def _aggregate_type_name(self) -> str:
        return "FeedbackSession"

    def _serialize_aggregate(self, aggregate: FeedbackSession) -> dict:
        return {
            "id": str(aggregate.id),
            "version": aggregate.version,
            "document_id": str(aggregate.document_id),
            "feedback_items": [
                {
                    "feedback_id": str(item["feedback_id"]),
                    "section": item["section"],
                    "issue": item["issue"],
                    "suggestion": item["suggestion"],
                    "original_text": item.get("original_text", ""),
                    "suggested_text": item.get("suggested_text", ""),
                    "confidence": item["confidence"],
                    "policy_reference": item.get("policy_reference", ""),
                    "status": item["status"].value if isinstance(item["status"], FeedbackStatus) else item["status"],
                }
                for item in aggregate.feedback_items
            ],
        }

    def _deserialize_aggregate(self, state: dict) -> FeedbackSession:
        session = FeedbackSession.__new__(FeedbackSession)
        session._id = UUID(state["id"])
        session._version = state["version"]
        session._pending_events = []
        session._document_id = UUID(state["document_id"])
        session._feedback_items = [
            {
                "feedback_id": UUID(item["feedback_id"]),
                "section": item["section"],
                "issue": item["issue"],
                "suggestion": item["suggestion"],
                "original_text": item.get("original_text", ""),
                "suggested_text": item.get("suggested_text", ""),
                "confidence": item["confidence"],
                "policy_reference": item.get("policy_reference", ""),
                "status": FeedbackStatus(item["status"]),
            }
            for item in state["feedback_items"]
        ]
        return session
