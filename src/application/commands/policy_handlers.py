from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from .base import CommandHandler
from src.domain.commands import (
    CreatePolicyRepository,
    AddPolicy,
    AssignDocumentToPolicy,
)
from src.domain.aggregates.policy_repository import PolicyRepository
from src.domain.exceptions.policy_exceptions import PolicyRepositoryNotFound

if TYPE_CHECKING:
    from src.application.services.event_publisher import EventPublisher


class CreatePolicyRepositoryHandler(CommandHandler[CreatePolicyRepository, UUID]):
    def __init__(
        self,
        policy_repository,
        event_publisher: "EventPublisher",
    ):
        self._policy_repo = policy_repository
        self._publisher = event_publisher

    async def handle(self, command: CreatePolicyRepository) -> UUID:
        repository_id = uuid4()
        
        policy_repo = PolicyRepository.create(
            repository_id=repository_id,
            name=command.name,
            description=command.description,
            created_by=command.created_by,
        )
        
        events = list(policy_repo.pending_events)
        await self._policy_repo.save(policy_repo)
        
        for event in events:
            await self._publisher.publish(event)
        
        return repository_id


class AddPolicyHandler(CommandHandler[AddPolicy, UUID]):
    def __init__(
        self,
        policy_repository,
        event_publisher: "EventPublisher",
    ):
        self._policy_repo = policy_repository
        self._publisher = event_publisher

    async def handle(self, command: AddPolicy) -> UUID:
        repo = await self._policy_repo.get(command.repository_id)
        if repo is None:
            raise PolicyRepositoryNotFound(repository_id=command.repository_id)
        
        policy_id = uuid4()
        
        repo.add_policy(
            policy_id=policy_id,
            policy_name=command.policy_name,
            policy_content=command.policy_content,
            requirement_type=command.requirement_type,
            added_by=command.added_by,
        )
        
        events = list(repo.pending_events)
        await self._policy_repo.save(repo)
        
        for event in events:
            await self._publisher.publish(event)
        
        return policy_id


class AssignDocumentToPolicyHandler(CommandHandler[AssignDocumentToPolicy, bool]):
    def __init__(
        self,
        policy_repository,
        document_repository,
        event_publisher: "EventPublisher",
    ):
        self._policy_repo = policy_repository
        self._document_repo = document_repository
        self._publisher = event_publisher

    async def handle(self, command: AssignDocumentToPolicy) -> bool:
        from src.domain.exceptions.document_exceptions import DocumentNotFound
        
        repo = await self._policy_repo.get(command.repository_id)
        if repo is None:
            raise PolicyRepositoryNotFound(repository_id=command.repository_id)
        
        document = await self._document_repo.get(command.document_id)
        if document is None:
            raise DocumentNotFound(document_id=command.document_id)
        
        repo.assign_document(
            document_id=command.document_id,
            assigned_by=command.assigned_by,
        )
        
        events = list(repo.pending_events)
        await self._policy_repo.save(repo)
        
        for event in events:
            await self._publisher.publish(event)
        
        return True
