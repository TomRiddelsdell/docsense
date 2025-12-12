"""Document Intermediate Representation value object."""

from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional, Set

from .ir_section import IRSection
from .term_definition import TermDefinition
from .formula_reference import FormulaReference
from .table_data import TableData
from .cross_reference import CrossReference
from .validation_issue import ValidationIssue


@dataclass
class DocumentIR:
    """Semantic Intermediate Representation for document analysis."""

    document_id: str
    title: str
    original_format: str
    sections: List[IRSection]
    definitions: List[TermDefinition]
    formulae: List[FormulaReference]
    tables: List[TableData]
    cross_references: List[CrossReference]
    metadata: Dict[str, Any]
    raw_markdown: str
    validation_issues: List[ValidationIssue] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Validate document IR data."""
        if not self.document_id:
            raise ValueError("Document ID cannot be empty")
        if not self.title:
            raise ValueError("Document title cannot be empty")
        if not self.original_format:
            raise ValueError("Original format cannot be empty")

    def to_dict(self) -> Dict[str, Any]:
        """
        Serialize to JSON-compatible dictionary.

        Returns:
            Dictionary representation of the DocumentIR
        """
        return {
            "document_id": self.document_id,
            "title": self.title,
            "original_format": self.original_format,
            "sections": [asdict(s) for s in self.sections],
            "definitions": [d.to_dict() for d in self.definitions],
            "formulae": [asdict(f) for f in self.formulae],
            "tables": [asdict(t) for t in self.tables],
            "cross_references": [asdict(c) for c in self.cross_references],
            "metadata": self.metadata,
            "raw_markdown": self.raw_markdown,
            "validation_issues": [asdict(v) for v in self.validation_issues],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DocumentIR":
        """
        Deserialize from JSON-compatible dictionary.

        Args:
            data: Dictionary representation

        Returns:
            DocumentIR instance
        """
        return cls(
            document_id=data["document_id"],
            title=data["title"],
            original_format=data["original_format"],
            sections=[IRSection.from_dict(s) for s in data.get("sections", [])],
            definitions=[TermDefinition.from_dict(d) for d in data.get("definitions", [])],
            formulae=[FormulaReference.from_dict(f) for f in data.get("formulae", [])],
            tables=[TableData.from_dict(t) for t in data.get("tables", [])],
            cross_references=[CrossReference.from_dict(c) for c in data.get("cross_references", [])],
            metadata=data.get("metadata", {}),
            raw_markdown=data.get("raw_markdown", ""),
            validation_issues=[ValidationIssue.from_dict(v) for v in data.get("validation_issues", [])],
        )

    def get_all_defined_terms(self) -> List[str]:
        """
        Get all terms defined in the document.

        Returns:
            List of all term names and aliases
        """
        terms = []
        for definition in self.definitions:
            terms.extend(definition.get_all_terms())
        return terms

    def get_all_defined_terms_set(self) -> Set[str]:
        """
        Get all defined terms as a set for fast lookup.

        Returns:
            Set of all term names and aliases (lowercase)
        """
        return {term.lower() for term in self.get_all_defined_terms()}

    def find_definition(self, term: str) -> Optional[TermDefinition]:
        """
        Find definition by term or alias.

        Args:
            term: Term to search for (case-insensitive)

        Returns:
            TermDefinition if found, None otherwise
        """
        for definition in self.definitions:
            if definition.matches(term):
                return definition
        return None

    def find_formula(self, formula_id: str) -> Optional[FormulaReference]:
        """
        Find formula by ID.

        Args:
            formula_id: Formula ID to search for

        Returns:
            FormulaReference if found, None otherwise
        """
        for formula in self.formulae:
            if formula.id == formula_id:
                return formula
        return None

    def find_formula_by_name(self, name: str) -> Optional[FormulaReference]:
        """
        Find formula by name.

        Args:
            name: Formula name to search for (case-insensitive)

        Returns:
            FormulaReference if found, None otherwise
        """
        name_lower = name.lower()
        for formula in self.formulae:
            if formula.name and formula.name.lower() == name_lower:
                return formula
        return None

    def find_table(self, table_id: str) -> Optional[TableData]:
        """
        Find table by ID.

        Args:
            table_id: Table ID to search for

        Returns:
            TableData if found, None otherwise
        """
        for table in self.tables:
            if table.id == table_id:
                return table
        return None

    def find_section(self, section_id: str) -> Optional[IRSection]:
        """
        Find section by ID.

        Args:
            section_id: Section ID to search for

        Returns:
            IRSection if found, None otherwise
        """
        for section in self.sections:
            if section.id == section_id:
                return section
        return None

    def get_error_issues(self) -> List[ValidationIssue]:
        """Get all error-level validation issues."""
        return [issue for issue in self.validation_issues if issue.is_error()]

    def get_warning_issues(self) -> List[ValidationIssue]:
        """Get all warning-level validation issues."""
        return [issue for issue in self.validation_issues if issue.is_warning()]

    def has_errors(self) -> bool:
        """Check if there are any error-level validation issues."""
        return len(self.get_error_issues()) > 0

    def to_llm_format(self) -> str:
        """
        Generate LLM-optimized flattened text with semantic markers.

        Returns:
            Formatted text optimized for LLM consumption
        """
        lines = []

        # Document metadata
        lines.append("=== DOCUMENT METADATA ===")
        lines.append(f"Title: {self.title}")
        lines.append(f"Format: {self.original_format}")
        lines.append(f"Sections: {len(self.sections)}")
        lines.append(f"Definitions: {len(self.definitions)}")
        lines.append(f"Formulae: {len(self.formulae)}")
        lines.append(f"Tables: {len(self.tables)}")
        lines.append("")

        # Definitions
        if self.definitions:
            lines.append(f"=== DEFINITIONS ({len(self.definitions)} terms) ===")
            for defn in self.definitions:
                lines.append(f"TERM: {defn.term}")
                lines.append(f"Definition: {defn.definition}")
                lines.append(f"Location: {defn.section_id}")
                if defn.aliases:
                    lines.append(f"Aliases: {', '.join(defn.aliases)}")
                lines.append("")

        # Formulae
        if self.formulae:
            lines.append(f"=== FORMULAE ({len(self.formulae)} formulas) ===")
            for formula in self.formulae:
                formula_header = f"FORMULA: {formula.id}"
                if formula.name:
                    formula_header += f" ({formula.name})"
                lines.append(formula_header)
                lines.append(f"LaTeX: {formula.latex}")
                if formula.variables:
                    lines.append(f"Variables: {', '.join(formula.variables)}")
                if formula.dependencies:
                    lines.append(f"Dependencies: {', '.join(formula.dependencies)}")
                lines.append(f"Location: {formula.section_id}")
                lines.append("")

        # Tables
        if self.tables:
            lines.append(f"=== TABLES ({len(self.tables)} tables) ===")
            for table in self.tables:
                table_header = f"TABLE: {table.id}"
                if table.title:
                    table_header += f" - {table.title}"
                lines.append(table_header)
                lines.append(f"Columns: {', '.join(table.headers)}")
                lines.append(f"Rows: {table.row_count}")
                lines.append(f"Location: {table.section_id}")
                lines.append("")

        # Validation issues
        if self.validation_issues:
            lines.append(f"=== VALIDATION ISSUES ({len(self.validation_issues)}) ===")
            for issue in self.validation_issues:
                severity_symbol = "❌" if issue.is_error() else "⚠️" if issue.is_warning() else "ℹ️"
                lines.append(f"{severity_symbol} {issue.issue_type.value.upper()}: {issue.message}")
                lines.append(f"   Location: {issue.location}")
                if issue.suggestion:
                    lines.append(f"   Suggestion: {issue.suggestion}")
                lines.append("")

        # Document content
        lines.append("=== DOCUMENT CONTENT ===")
        lines.append(self.raw_markdown)

        return "\n".join(lines)

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about the document IR.

        Returns:
            Dictionary with various statistics
        """
        return {
            "section_count": len(self.sections),
            "definition_count": len(self.definitions),
            "formula_count": len(self.formulae),
            "table_count": len(self.tables),
            "cross_reference_count": len(self.cross_references),
            "validation_error_count": len(self.get_error_issues()),
            "validation_warning_count": len(self.get_warning_issues()),
            "total_terms": len(self.get_all_defined_terms()),
            "markdown_length": len(self.raw_markdown),
        }
