from typing import Type
from uuid import UUID

from src.domain.aggregates.policy_repository import PolicyRepository as PolicyRepositoryAggregate
from src.infrastructure.repositories.base import Repository


class PolicyRepositoryRepository(Repository[PolicyRepositoryAggregate]):
    def _aggregate_type(self) -> Type[PolicyRepositoryAggregate]:
        return PolicyRepositoryAggregate

    def _aggregate_type_name(self) -> str:
        return "PolicyRepository"

    def _serialize_aggregate(self, aggregate: PolicyRepositoryAggregate) -> dict:
        return {
            "id": str(aggregate.id),
            "version": aggregate.version,
            "name": aggregate.name,
            "description": aggregate.description,
            "policies": [
                {
                    "policy_id": str(p["policy_id"]),
                    "name": p["name"],
                    "description": p["description"],
                    "requirement_type": p["requirement_type"],
                }
                for p in aggregate.policies
            ],
            "assigned_documents": [str(doc_id) for doc_id in aggregate.assigned_documents],
        }

    def _deserialize_aggregate(self, state: dict) -> PolicyRepositoryAggregate:
        repo = PolicyRepositoryAggregate.__new__(PolicyRepositoryAggregate)
        repo._id = UUID(state["id"])
        repo._version = state["version"]
        repo._pending_events = []
        repo._name = state["name"]
        repo._description = state["description"]
        repo._policies = [
            {
                "policy_id": UUID(p["policy_id"]),
                "name": p["name"],
                "description": p["description"],
                "requirement_type": p["requirement_type"],
            }
            for p in state["policies"]
        ]
        repo._assigned_documents = [UUID(doc_id) for doc_id in state["assigned_documents"]]
        return repo
