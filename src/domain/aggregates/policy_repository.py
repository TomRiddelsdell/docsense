from typing import List, Set, Optional
from uuid import UUID

from .base import Aggregate
from src.domain.events.base import DomainEvent
from src.domain.events.policy_events import (
    PolicyRepositoryCreated,
    PolicyAdded,
    DocumentAssignedToPolicy,
)
from src.domain.exceptions.policy_exceptions import PolicyAlreadyExists, PolicyIdAlreadyExists
from src.domain.exceptions.document_exceptions import DocumentAlreadyAssigned
from src.domain.value_objects import Policy, RequirementType


class PolicyRepository(Aggregate):
    def __init__(self, repository_id: UUID):
        super().__init__(repository_id)
        self._name: str = ""
        self._description: str = ""
        self._policies: List[Policy] = []
        self._assigned_documents: Set[UUID] = set()

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    @property
    def policies(self) -> List[Policy]:
        """Return copy of policies list (policies themselves are immutable)."""
        return self._policies.copy()

    @property
    def assigned_documents(self) -> Set[UUID]:
        """Return copy of assigned documents set."""
        return self._assigned_documents.copy()

    def _init_state(self) -> None:
        self._name = ""
        self._description = ""
        self._policies = []
        self._assigned_documents = set()

    def _find_policy_by_id(self, policy_id: UUID) -> Optional[Policy]:
        """Find policy by ID."""
        for policy in self._policies:
            if policy.policy_id == policy_id:
                return policy
        return None

    def _find_policy_by_name(self, policy_name: str) -> Optional[Policy]:
        """Find policy by name."""
        for policy in self._policies:
            if policy.policy_name == policy_name:
                return policy
        return None

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
        if self._find_policy_by_id(policy_id) is not None:
            raise PolicyIdAlreadyExists(policy_id=policy_id)
        if self._find_policy_by_name(policy_name) is not None:
            raise PolicyAlreadyExists(policy_name=policy_name)
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
        if document_id in self._assigned_documents:
            raise DocumentAlreadyAssigned(
                document_id=document_id,
                repository_id=self._id
            )
        self._apply_event(
            DocumentAssignedToPolicy(
                aggregate_id=self._id,
                document_id=document_id,
                assigned_by=assigned_by,
            )
        )

    def _when(self, event: DomainEvent) -> None:
        """
        Apply event to aggregate state using immutable value objects.

        Creates immutable Policy value objects instead of mutable dicts.
        """
        if isinstance(event, PolicyRepositoryCreated):
            self._name = event.name
            self._description = event.description

        elif isinstance(event, PolicyAdded):
            # Create immutable Policy value object
            new_policy = Policy(
                policy_id=event.policy_id,
                policy_name=event.policy_name,
                policy_content=event.policy_content,
                requirement_type=RequirementType(event.requirement_type) if isinstance(event.requirement_type, str) else event.requirement_type,
            )
            self._policies.append(new_policy)

        elif isinstance(event, DocumentAssignedToPolicy):
            # UUID is immutable, so adding to set is safe
            self._assigned_documents.add(event.document_id)
