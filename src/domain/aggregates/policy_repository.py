from typing import List, Dict, Any, Set
from uuid import UUID

from .base import Aggregate
from src.domain.events.base import DomainEvent
from src.domain.events.policy_events import (
    PolicyRepositoryCreated,
    PolicyAdded,
    DocumentAssignedToPolicy,
)


class PolicyRepository(Aggregate):
    def __init__(self, repository_id: UUID):
        super().__init__(repository_id)
        self._name: str = ""
        self._description: str = ""
        self._policies: List[Dict[str, Any]] = []
        self._assigned_documents: Set[UUID] = set()

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    @property
    def policies(self) -> List[Dict[str, Any]]:
        return self._policies.copy()

    @property
    def assigned_documents(self) -> Set[UUID]:
        return self._assigned_documents.copy()

    @classmethod
    def create(
        cls,
        repository_id: UUID,
        name: str,
        description: str,
        created_by: str,
    ) -> "PolicyRepository":
        repo = cls(repository_id)
        repo._apply_event(
            PolicyRepositoryCreated(
                aggregate_id=repository_id,
                name=name,
                description=description,
                created_by=created_by,
            )
        )
        return repo

    def add_policy(
        self,
        policy_id: UUID,
        policy_name: str,
        policy_content: str,
        requirement_type: str,
        added_by: str,
    ) -> None:
        self._apply_event(
            PolicyAdded(
                aggregate_id=self._id,
                policy_id=policy_id,
                policy_name=policy_name,
                policy_content=policy_content,
                requirement_type=requirement_type,
                added_by=added_by,
            )
        )

    def assign_document(
        self,
        document_id: UUID,
        assigned_by: str,
    ) -> None:
        self._apply_event(
            DocumentAssignedToPolicy(
                aggregate_id=self._id,
                document_id=document_id,
                assigned_by=assigned_by,
            )
        )

    def _when(self, event: DomainEvent) -> None:
        if isinstance(event, PolicyRepositoryCreated):
            self._name = event.name
            self._description = event.description
        elif isinstance(event, PolicyAdded):
            self._policies.append({
                "policy_id": event.policy_id,
                "policy_name": event.policy_name,
                "policy_content": event.policy_content,
                "requirement_type": event.requirement_type,
            })
        elif isinstance(event, DocumentAssignedToPolicy):
            self._assigned_documents.add(event.document_id)
