"""
Policy value object for DDD compliance.

Immutable value object representing a policy in a PolicyRepository.
Replaces mutable dict representation to enforce DDD principles.
"""
from dataclasses import dataclass
from uuid import UUID

from .requirement_type import RequirementType


@dataclass(frozen=True)
class Policy:
    """
    Immutable policy value object.

    Represents a single policy with its metadata and content.
    """
    policy_id: UUID
    policy_name: str
    policy_content: str
    requirement_type: RequirementType

    def __post_init__(self):
        """Validate policy invariants."""
        if not self.policy_name or not self.policy_name.strip():
            raise ValueError("Policy name cannot be empty")

        if not self.policy_content or not self.policy_content.strip():
            raise ValueError("Policy content cannot be empty")

    def is_must_requirement(self) -> bool:
        """Check if this is a MUST requirement."""
        return self.requirement_type == RequirementType.MUST

    def is_should_requirement(self) -> bool:
        """Check if this is a SHOULD requirement."""
        return self.requirement_type == RequirementType.SHOULD

    def to_dict(self) -> dict:
        """Convert to dict for serialization."""
        return {
            "policy_id": self.policy_id,
            "policy_name": self.policy_name,
            "policy_content": self.policy_content,
            "requirement_type": self.requirement_type.value,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Policy":
        """Create from dict (for deserialization)."""
        return cls(
            policy_id=data["policy_id"] if isinstance(data["policy_id"], UUID) else UUID(data["policy_id"]),
            policy_name=data["policy_name"],
            policy_content=data["policy_content"],
            requirement_type=RequirementType(data["requirement_type"]) if isinstance(data["requirement_type"], str) else data["requirement_type"],
        )
