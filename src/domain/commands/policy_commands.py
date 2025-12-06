from dataclasses import dataclass, field
from uuid import UUID

from .base import Command


@dataclass(frozen=True)
class CreatePolicyRepository(Command):
    name: str = ""
    description: str = ""
    created_by: str = ""


@dataclass(frozen=True)
class AddPolicy(Command):
    repository_id: UUID = field(default=None)
    policy_name: str = ""
    policy_content: str = ""
    requirement_type: str = ""
    added_by: str = ""


@dataclass(frozen=True)
class AssignDocumentToPolicy(Command):
    repository_id: UUID = field(default=None)
    document_id: UUID = field(default=None)
    assigned_by: str = ""
