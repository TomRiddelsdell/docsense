"""Enhanced section with semantic classification."""

from dataclasses import dataclass
from typing import Optional, Dict, Any

from .section_type import SectionType


@dataclass(frozen=True)
class IRSection:
    """Enhanced document section with semantic classification."""

    id: str
    title: str
    content: str
    level: int
    section_type: SectionType
    parent_id: Optional[str] = None
    start_line: Optional[int] = None
    end_line: Optional[int] = None

    def __post_init__(self) -> None:
        """Validate section data."""
        if not self.id:
            raise ValueError("Section ID cannot be empty")
        if not self.title:
            raise ValueError("Section title cannot be empty")
        if self.level < 1:
            raise ValueError(f"Section level must be >= 1, got {self.level}")
        if self.start_line is not None and self.start_line < 1:
            raise ValueError(f"Start line must be >= 1, got {self.start_line}")
        if self.end_line is not None and self.start_line is not None:
            if self.end_line < self.start_line:
                raise ValueError(
                    f"End line ({self.end_line}) must be >= start line ({self.start_line})"
                )

    def contains_line(self, line_number: int) -> bool:
        """Check if this section contains the given line number."""
        if self.start_line is None or self.end_line is None:
            return False
        return self.start_line <= line_number <= self.end_line

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "IRSection":
        """
        Deserialize from dictionary.

        Args:
            data: Dictionary representation

        Returns:
            IRSection instance
        """
        # Handle section_type enum
        section_type = data.get("section_type")
        if isinstance(section_type, str):
            section_type = SectionType(section_type)
        elif isinstance(section_type, dict):
            section_type = SectionType(section_type.get("value", section_type.get("name", "unknown")))

        return cls(
            id=data["id"],
            title=data["title"],
            content=data["content"],
            level=data["level"],
            section_type=section_type,
            parent_id=data.get("parent_id"),
            start_line=data.get("start_line"),
            end_line=data.get("end_line"),
        )
