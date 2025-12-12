"""Cross-reference value object for semantic IR."""

from dataclasses import dataclass
from typing import Dict, Any


@dataclass(frozen=True)
class CrossReference:
    """Internal document reference."""

    id: str
    source_id: str
    source_type: str  # "section", "formula", "table", "definition"
    target_id: str
    target_type: str
    reference_text: str
    resolved: bool = False

    def __post_init__(self) -> None:
        """Validate cross-reference data."""
        if not self.id:
            raise ValueError("Cross-reference ID cannot be empty")
        if not self.source_id:
            raise ValueError("Source ID cannot be empty")
        if not self.source_type:
            raise ValueError("Source type cannot be empty")
        if not self.target_id:
            raise ValueError("Target ID cannot be empty")
        if not self.target_type:
            raise ValueError("Target type cannot be empty")

        # Validate types
        valid_types = {"section", "formula", "table", "definition"}
        if self.source_type not in valid_types:
            raise ValueError(
                f"Invalid source type: {self.source_type}. Must be one of {valid_types}"
            )
        if self.target_type not in valid_types:
            raise ValueError(
                f"Invalid target type: {self.target_type}. Must be one of {valid_types}"
            )

    def is_circular(self) -> bool:
        """Check if this is a circular reference (source == target)."""
        return self.source_id == self.target_id

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CrossReference":
        """
        Deserialize from dictionary.

        Args:
            data: Dictionary representation

        Returns:
            CrossReference instance
        """
        return cls(
            id=data["id"],
            source_id=data["source_id"],
            source_type=data["source_type"],
            target_id=data["target_id"],
            target_type=data["target_type"],
            reference_text=data["reference_text"],
            resolved=data.get("resolved", False),
        )
