from typing import Type
from uuid import UUID

from src.domain.aggregates.policy_repository import PolicyRepository as PolicyRepositoryAggregate
from src.domain.value_objects import Policy
from src.infrastructure.repositories.base import Repository


class PolicyRepositoryRepository(Repository[PolicyRepositoryAggregate]):
    def _aggregate_type(self) -> Type[PolicyRepositoryAggregate]:
        return PolicyRepositoryAggregate

    def _aggregate_type_name(self) -> str:
        return "PolicyRepository"

    def _serialize_aggregate(self, aggregate: PolicyRepositoryAggregate) -> dict:
        """
        Serialize PolicyRepository using immutable Policy value objects.

        Uses Policy.to_dict() for proper serialization.
        """
        return {
            "id": str(aggregate.id),
            "version": aggregate.version,
            "name": aggregate.name,
            "description": aggregate.description,
            "policies": [
                {
                    "policy_id": str(p.policy_id),
                    "policy_name": p.policy_name,
                    "policy_content": p.policy_content,
                    "requirement_type": p.requirement_type.value,
                }
                for p in aggregate.policies
            ],
            "assigned_documents": [str(doc_id) for doc_id in aggregate.assigned_documents],
        }

    def _deserialize_aggregate(self, state: dict) -> PolicyRepositoryAggregate:
        """
        Deserialize PolicyRepository using immutable Policy value objects.

        Uses Policy.from_dict() for proper deserialization.
        """
        repo = PolicyRepositoryAggregate.__new__(PolicyRepositoryAggregate)
        repo._id = UUID(state["id"])
        repo._version = state["version"]
        repo._pending_events = []
        repo._name = state["name"]
        repo._description = state["description"]
        repo._policies = [
            Policy.from_dict(p)
            for p in state["policies"]
        ]
        repo._assigned_documents = set(UUID(doc_id) for doc_id in state["assigned_documents"])
        return repo
