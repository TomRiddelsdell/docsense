from uuid import UUID

from .base import CommandHandler
from src.domain.commands import StartAnalysis, CancelAnalysis
from src.domain.aggregates.document import Document
from src.domain.exceptions.document_exceptions import DocumentNotFound
from src.domain.exceptions.policy_exceptions import PolicyRepositoryNotFound
from src.infrastructure.repositories.document_repository import DocumentRepository
from src.infrastructure.repositories.policy_repository import PolicyRepositoryRepository
from src.application.services.event_publisher import EventPublisher


class StartAnalysisHandler(CommandHandler[StartAnalysis, UUID]):
    def __init__(
        self,
        document_repository: DocumentRepository,
        policy_repository: PolicyRepositoryRepository,
        event_publisher: EventPublisher
    ):
        self._documents = document_repository
        self._policies = policy_repository
        self._publisher = event_publisher

    async def handle(self, command: StartAnalysis) -> UUID:
        document = await self._documents.get(command.document_id)
        if document is None:
            raise DocumentNotFound(document_id=command.document_id)

        policy_repo = await self._policies.get(command.policy_repository_id)
        if policy_repo is None:
            raise PolicyRepositoryNotFound(repository_id=command.policy_repository_id)

        document.start_analysis(
            policy_repository_id=command.policy_repository_id,
            ai_model=command.ai_model,
            initiated_by=command.initiated_by
        )

        await self._documents.save(document)

        events = document.pending_events
        if events:
            await self._publisher.publish_all(events)

        return command.document_id


class CancelAnalysisHandler(CommandHandler[CancelAnalysis, bool]):
    def __init__(
        self,
        document_repository: DocumentRepository,
        event_publisher: EventPublisher
    ):
        self._documents = document_repository
        self._publisher = event_publisher

    async def handle(self, command: CancelAnalysis) -> bool:
        document = await self._documents.get(command.document_id)
        if document is None:
            raise DocumentNotFound(document_id=command.document_id)

        return True
