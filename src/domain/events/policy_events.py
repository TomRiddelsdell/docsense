from dataclasses import dataclass, field
from uuid import UUID

from .base import DomainEvent


@dataclass(frozen=True)
class PolicyRepositoryCreated(DomainEvent):
    name: str = ""
    description: str = ""
    created_by: str = ""
    aggregate_type: str = field(default="PolicyRepository")


@dataclass(frozen=True)
class PolicyAdded(DomainEvent):
    policy_id: UUID = field(default=None)
    policy_name: str = ""
    policy_content: str = ""
    requirement_type: str = ""
    added_by: str = ""
    aggregate_type: str = field(default="PolicyRepository")


@dataclass(frozen=True)
class DocumentAssignedToPolicy(DomainEvent):
    document_id: UUID = field(default=None)
    assigned_by: str = ""
    aggregate_type: str = field(default="PolicyRepository")
