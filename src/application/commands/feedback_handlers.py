from uuid import UUID

from .base import CommandHandler
from src.domain.commands import AcceptChange, RejectChange, ModifyChange
from src.domain.aggregates.feedback_session import FeedbackSession
from src.domain.exceptions.feedback_exceptions import FeedbackSessionNotFound
from src.infrastructure.repositories.feedback_repository import FeedbackSessionRepository
from src.application.services.event_publisher import EventPublisher


class AcceptChangeHandler(CommandHandler[AcceptChange, bool]):
    def __init__(
        self,
        feedback_repository: FeedbackSessionRepository,
        event_publisher: EventPublisher
    ):
        self._feedback = feedback_repository
        self._publisher = event_publisher

    async def handle(self, command: AcceptChange) -> bool:
        sessions = await self._find_session_for_document(command.document_id)
        if sessions is None:
            raise FeedbackSessionNotFound(session_id=command.document_id)

        sessions.accept_change(
            feedback_id=command.feedback_id,
            accepted_by=command.accepted_by,
            applied_change=""
        )

        await self._feedback.save(sessions)

        events = sessions.pending_events
        if events:
            await self._publisher.publish_all(events)

        return True

    async def _find_session_for_document(self, document_id: UUID) -> FeedbackSession:
        return await self._feedback.get(document_id)


class RejectChangeHandler(CommandHandler[RejectChange, bool]):
    def __init__(
        self,
        feedback_repository: FeedbackSessionRepository,
        event_publisher: EventPublisher
    ):
        self._feedback = feedback_repository
        self._publisher = event_publisher

    async def handle(self, command: RejectChange) -> bool:
        session = await self._feedback.get(command.document_id)
        if session is None:
            raise FeedbackSessionNotFound(session_id=command.document_id)

        session.reject_change(
            feedback_id=command.feedback_id,
            rejected_by=command.rejected_by,
            rejection_reason=command.reason
        )

        await self._feedback.save(session)

        events = session.pending_events
        if events:
            await self._publisher.publish_all(events)

        return True


class ModifyChangeHandler(CommandHandler[ModifyChange, bool]):
    def __init__(
        self,
        feedback_repository: FeedbackSessionRepository,
        event_publisher: EventPublisher
    ):
        self._feedback = feedback_repository
        self._publisher = event_publisher

    async def handle(self, command: ModifyChange) -> bool:
        session = await self._feedback.get(command.document_id)
        if session is None:
            raise FeedbackSessionNotFound(session_id=command.document_id)

        session.modify_change(
            feedback_id=command.feedback_id,
            modified_by=command.modified_by,
            modified_change=command.modified_content,
            original_change=""
        )

        await self._feedback.save(session)

        events = session.pending_events
        if events:
            await self._publisher.publish_all(events)

        return True
