"""Validation issue value objects for semantic IR."""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Dict, Any


class ValidationSeverity(Enum):
    """Severity level of a validation issue."""

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"

    def __str__(self) -> str:
        return self.value


class ValidationType(Enum):
    """Type of validation issue detected."""

    DUPLICATE_DEFINITION = "duplicate_definition"
    UNDEFINED_VARIABLE = "undefined_variable"
    CIRCULAR_DEPENDENCY = "circular_dependency"
    MISSING_REFERENCE = "missing_reference"
    AMBIGUOUS_TERM = "ambiguous_term"
    INCOMPLETE_FORMULA = "incomplete_formula"

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class ValidationIssue:
    """Pre-validation issue detected programmatically."""

    id: str
    issue_type: ValidationType
    severity: ValidationSeverity
    message: str
    location: str
    related_ids: List[str] = field(default_factory=list)
    suggestion: Optional[str] = None

    def __post_init__(self) -> None:
        """Validate issue data."""
        if not self.id:
            raise ValueError("Validation issue ID cannot be empty")
        if not self.message:
            raise ValueError("Validation message cannot be empty")
        if not self.location:
            raise ValueError("Validation location cannot be empty")

    def is_error(self) -> bool:
        """Check if this is an error-level issue."""
        return self.severity == ValidationSeverity.ERROR

    def is_warning(self) -> bool:
        """Check if this is a warning-level issue."""
        return self.severity == ValidationSeverity.WARNING

    def is_info(self) -> bool:
        """Check if this is an info-level issue."""
        return self.severity == ValidationSeverity.INFO

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ValidationIssue":
        """
        Deserialize from dictionary.

        Args:
            data: Dictionary representation

        Returns:
            ValidationIssue instance
        """
        # Handle enums
        issue_type = data.get("issue_type")
        if isinstance(issue_type, str):
            issue_type = ValidationType(issue_type)
        elif isinstance(issue_type, dict):
            issue_type = ValidationType(issue_type.get("value", issue_type.get("name")))

        severity = data.get("severity")
        if isinstance(severity, str):
            severity = ValidationSeverity(severity)
        elif isinstance(severity, dict):
            severity = ValidationSeverity(severity.get("value", severity.get("name")))

        return cls(
            id=data["id"],
            issue_type=issue_type,
            severity=severity,
            message=data["message"],
            location=data["location"],
            related_ids=data.get("related_ids", []),
            suggestion=data.get("suggestion"),
        )
