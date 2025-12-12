"""Term lineage tracking for semantic IR."""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum


class DependencyType(Enum):
    """Type of dependency between terms."""
    DIRECT_REFERENCE = "direct_reference"  # Term explicitly references another term
    PARAMETER = "parameter"  # Term uses a parameter/variable
    FORMULA_INPUT = "formula_input"  # Term is used as input to a formula
    COMPUTED_FROM = "computed_from"  # Term is computed from other terms
    CONDITIONAL_ON = "conditional_on"  # Term's value depends on a condition


@dataclass(frozen=True)
class TermDependency:
    """Represents a dependency on another term or parameter."""

    # The referenced term/parameter name
    name: str

    # Type of dependency
    dependency_type: DependencyType

    # Optional: The specific part of the definition where this dependency appears
    context: str = ""

    # Optional: Additional metadata about the dependency
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "name": self.name,
            "dependency_type": self.dependency_type.value,
            "context": self.context,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TermDependency":
        """Create from dictionary."""
        return cls(
            name=data["name"],
            dependency_type=DependencyType(data["dependency_type"]),
            context=data.get("context", ""),
            metadata=data.get("metadata", {}),
        )


@dataclass(frozen=True)
class Parameter:
    """Represents a parameter used in a term definition."""

    # Parameter name
    name: str

    # Parameter type (e.g., "numeric", "date", "percentage", "text")
    param_type: str = "unknown"

    # Optional: Units if applicable (e.g., "USD", "days", "percent")
    units: Optional[str] = None

    # Optional: Description of what this parameter represents
    description: str = ""

    # Optional: Where in the definition this parameter appears
    context: str = ""

    # Optional: Default value if any
    default_value: Optional[Any] = None

    # Optional: Range or constraints (e.g., "0-100" for percentage)
    constraints: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "name": self.name,
            "param_type": self.param_type,
            "units": self.units,
            "description": self.description,
            "context": self.context,
            "default_value": self.default_value,
            "constraints": self.constraints,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Parameter":
        """Create from dictionary."""
        return cls(
            name=data["name"],
            param_type=data.get("param_type", "unknown"),
            units=data.get("units"),
            description=data.get("description", ""),
            context=data.get("context", ""),
            default_value=data.get("default_value"),
            constraints=data.get("constraints"),
        )


@dataclass(frozen=True)
class TermLineage:
    """
    Complete lineage information for a term.

    This captures all dependencies, parameters, and computational relationships
    to enable full lineage tracking and impact analysis.
    """

    # Terms that this term directly depends on
    input_terms: List[TermDependency] = field(default_factory=list)

    # Parameters used in this term's definition
    parameters: List[Parameter] = field(default_factory=list)

    # Whether this term is computed/derived (vs. just defined)
    is_computed: bool = False

    # If computed, describe the computation (e.g., "sum of X and Y")
    computation_description: str = ""

    # Optional: Formula or expression if applicable
    formula: Optional[str] = None

    # Optional: Conditions that affect this term's value
    conditions: List[str] = field(default_factory=list)

    # Optional: Additional metadata for lineage tracking
    metadata: Dict[str, Any] = field(default_factory=dict)

    def get_all_dependencies(self) -> List[str]:
        """Get all term names that this term depends on."""
        return [dep.name for dep in self.input_terms]

    def get_all_parameters(self) -> List[str]:
        """Get all parameter names used by this term."""
        return [param.name for param in self.parameters]

    def has_dependencies(self) -> bool:
        """Check if this term has any dependencies."""
        return len(self.input_terms) > 0 or len(self.parameters) > 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "input_terms": [dep.to_dict() for dep in self.input_terms],
            "parameters": [param.to_dict() for param in self.parameters],
            "is_computed": self.is_computed,
            "computation_description": self.computation_description,
            "formula": self.formula,
            "conditions": list(self.conditions),
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TermLineage":
        """Create from dictionary."""
        return cls(
            input_terms=[TermDependency.from_dict(d) for d in data.get("input_terms", [])],
            parameters=[Parameter.from_dict(p) for p in data.get("parameters", [])],
            is_computed=data.get("is_computed", False),
            computation_description=data.get("computation_description", ""),
            formula=data.get("formula"),
            conditions=data.get("conditions", []),
            metadata=data.get("metadata", {}),
        )

    @classmethod
    def empty(cls) -> "TermLineage":
        """Create an empty lineage (no dependencies)."""
        return cls()
