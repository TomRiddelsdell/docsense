"""Formula reference value object for semantic IR."""

from dataclasses import dataclass, field
from typing import List, Optional, Set, Dict, Any


@dataclass(frozen=True)
class FormulaReference:
    """A mathematical formula with dependency tracking."""

    id: str
    latex: str
    section_id: str
    name: Optional[str] = None  # e.g., "AssetLongTermVol"
    mathml: Optional[str] = None
    plain_text: str = ""
    variables: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)  # IDs of other formulas or terms
    line_number: Optional[int] = None

    def __post_init__(self) -> None:
        """Validate formula reference data."""
        if not self.id:
            raise ValueError("Formula reference ID cannot be empty")
        if not self.latex:
            raise ValueError("LaTeX content cannot be empty")
        if not self.section_id:
            raise ValueError("Section ID cannot be empty")
        if self.line_number is not None and self.line_number < 1:
            raise ValueError(f"Line number must be >= 1, got {self.line_number}")

    def get_undefined_variables(self, defined_terms: Set[str]) -> List[str]:
        """
        Return variables not in the defined terms set.

        Args:
            defined_terms: Set of defined term names (case-insensitive)

        Returns:
            List of undefined variable names
        """
        defined_lower = {t.lower() for t in defined_terms}
        return [v for v in self.variables if v.lower() not in defined_lower]

    def has_dependency(self, dependency_id: str) -> bool:
        """Check if this formula depends on another entity."""
        return dependency_id in self.dependencies

    def get_variable_count(self) -> int:
        """Get the number of unique variables in this formula."""
        return len(set(self.variables))

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FormulaReference":
        """
        Deserialize from dictionary.

        Args:
            data: Dictionary representation

        Returns:
            FormulaReference instance
        """
        return cls(
            id=data["id"],
            latex=data["latex"],
            section_id=data["section_id"],
            name=data.get("name"),
            mathml=data.get("mathml"),
            plain_text=data.get("plain_text", ""),
            variables=data.get("variables", []),
            dependencies=data.get("dependencies", []),
            line_number=data.get("line_number"),
        )
