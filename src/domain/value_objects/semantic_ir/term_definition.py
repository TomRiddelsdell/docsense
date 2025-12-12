"""Term definition value object for semantic IR."""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

from .term_lineage import TermLineage


@dataclass(frozen=True)
class TermDefinition:
    """A defined term within the document."""

    id: str
    term: str
    definition: str
    section_id: str
    aliases: List[str] = field(default_factory=list)
    first_occurrence_line: int = 0
    lineage: Optional[TermLineage] = None

    def __post_init__(self) -> None:
        """Validate term definition data."""
        if not self.id:
            raise ValueError("Term definition ID cannot be empty")
        if not self.term:
            raise ValueError("Term cannot be empty")
        if not self.definition:
            raise ValueError("Definition cannot be empty")
        if not self.section_id:
            raise ValueError("Section ID cannot be empty")
        if self.first_occurrence_line < 0:
            raise ValueError(
                f"First occurrence line must be >= 0, got {self.first_occurrence_line}"
            )

    def matches(self, text: str) -> bool:
        """Check if text matches this term or any alias."""
        normalized = text.lower().strip()
        if self.term.lower() == normalized:
            return True
        return any(alias.lower() == normalized for alias in self.aliases)

    def get_all_terms(self) -> List[str]:
        """Get the main term and all aliases."""
        return [self.term] + list(self.aliases)

    def to_dict(self) -> Dict[str, Any]:
        """
        Serialize to JSON-compatible dictionary.

        Returns:
            Dictionary representation of the TermDefinition
        """
        return {
            "id": self.id,
            "term": self.term,
            "definition": self.definition,
            "section_id": self.section_id,
            "aliases": list(self.aliases),
            "first_occurrence_line": self.first_occurrence_line,
            "lineage": self.lineage.to_dict() if self.lineage else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TermDefinition":
        """
        Deserialize from dictionary.

        Args:
            data: Dictionary representation

        Returns:
            TermDefinition instance
        """
        lineage_data = data.get("lineage")
        lineage = TermLineage.from_dict(lineage_data) if lineage_data else None

        return cls(
            id=data["id"],
            term=data["term"],
            definition=data["definition"],
            section_id=data["section_id"],
            aliases=data.get("aliases", []),
            first_occurrence_line=data.get("first_occurrence_line", 0),
            lineage=lineage,
        )
