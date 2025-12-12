"""Tests for IR validator."""

import pytest
from src.infrastructure.semantic.ir_validator import IRValidator
from src.domain.value_objects.semantic_ir import (
    DocumentIR,
    IRSection,
    TermDefinition,
    FormulaReference,
    TableData,
    CrossReference,
    SectionType,
    ValidationSeverity,
    ValidationType,
)


class TestIRValidator:
    """Test suite for IRValidator."""

    @pytest.fixture
    def validator(self):
        """Create an IRValidator instance."""
        return IRValidator()

    @pytest.fixture
    def sample_ir(self):
        """Create a sample DocumentIR for testing."""
        return DocumentIR(
            document_id="doc-1",
            title="Test Document",
            original_format="pdf",
            sections=[
                IRSection(
                    id="section-1",
                    title="Introduction",
                    content="Content",
                    level=1,
                    section_type=SectionType.NARRATIVE,
                )
            ],
            definitions=[],
            formulae=[],
            tables=[],
            cross_references=[],
            metadata={},
            raw_markdown="# Test",
        )

    def test_detect_duplicate_definitions(self, validator, sample_ir):
        """Test detection of duplicate term definitions."""
        sample_ir.definitions = [
            TermDefinition(
                id="def-1",
                term="Volatility",
                definition="First definition",
                section_id="section-1",
            ),
            TermDefinition(
                id="def-2",
                term="Volatility",  # Duplicate
                definition="Second definition",
                section_id="section-2",
            ),
        ]

        issues = validator.validate(sample_ir)

        duplicate_issues = [i for i in issues if i.issue_type == ValidationType.DUPLICATE_DEFINITION]
        assert len(duplicate_issues) == 1
        assert duplicate_issues[0].severity == ValidationSeverity.WARNING
        assert "Volatility" in duplicate_issues[0].message

    def test_case_insensitive_duplicate_detection(self, validator, sample_ir):
        """Test that duplicate detection is case-insensitive."""
        sample_ir.definitions = [
            TermDefinition(
                id="def-1",
                term="Risk Factor",
                definition="First",
                section_id="section-1",
            ),
            TermDefinition(
                id="def-2",
                term="RISK FACTOR",  # Same term, different case
                definition="Second",
                section_id="section-2",
            ),
        ]

        issues = validator.validate(sample_ir)

        duplicate_issues = [i for i in issues if i.issue_type == ValidationType.DUPLICATE_DEFINITION]
        assert len(duplicate_issues) == 1

    def test_detect_undefined_variables(self, validator, sample_ir):
        """Test detection of undefined variables in formulas."""
        sample_ir.formulae = [
            FormulaReference(
                id="formula-1",
                name="Result",
                latex="Result = UndefinedVar * 2",
                section_id="section-1",
                variables=["UndefinedVar"],
            )
        ]
        # No definitions provided, so UndefinedVar is undefined

        issues = validator.validate(sample_ir)

        undefined_issues = [i for i in issues if i.issue_type == ValidationType.UNDEFINED_VARIABLE]
        assert len(undefined_issues) == 1
        assert "UndefinedVar" in undefined_issues[0].message

    def test_defined_variables_not_flagged(self, validator, sample_ir):
        """Test that defined variables are not flagged as undefined."""
        sample_ir.definitions = [
            TermDefinition(
                id="def-1",
                term="DefinedVar",
                definition="A defined variable",
                section_id="section-1",
            )
        ]
        sample_ir.formulae = [
            FormulaReference(
                id="formula-1",
                name="Result",
                latex="Result = DefinedVar * 2",
                section_id="section-1",
                variables=["DefinedVar"],
            )
        ]

        issues = validator.validate(sample_ir)

        undefined_issues = [i for i in issues if i.issue_type == ValidationType.UNDEFINED_VARIABLE]
        assert len(undefined_issues) == 0

    def test_detect_circular_dependencies(self, validator, sample_ir):
        """Test detection of circular dependencies in formulas."""
        sample_ir.formulae = [
            FormulaReference(
                id="formula-1",
                name="A",
                latex="A = B * 2",
                section_id="section-1",
                variables=["B"],
                dependencies=["formula-2"],
            ),
            FormulaReference(
                id="formula-2",
                name="B",
                latex="B = A * 3",
                section_id="section-1",
                variables=["A"],
                dependencies=["formula-1"],  # Circular!
            ),
        ]

        issues = validator.validate(sample_ir)

        circular_issues = [i for i in issues if i.issue_type == ValidationType.CIRCULAR_DEPENDENCY]
        assert len(circular_issues) > 0
        assert circular_issues[0].severity == ValidationSeverity.ERROR

    def test_no_circular_dependency_in_chain(self, validator, sample_ir):
        """Test that linear dependency chains are not flagged."""
        sample_ir.formulae = [
            FormulaReference(
                id="formula-1",
                name="A",
                latex="A = 5",
                section_id="section-1",
                variables=[],
                dependencies=[],
            ),
            FormulaReference(
                id="formula-2",
                name="B",
                latex="B = A * 2",
                section_id="section-1",
                variables=["A"],
                dependencies=["formula-1"],
            ),
            FormulaReference(
                id="formula-3",
                name="C",
                latex="C = B * 3",
                section_id="section-1",
                variables=["B"],
                dependencies=["formula-2"],
            ),
        ]

        issues = validator.validate(sample_ir)

        circular_issues = [i for i in issues if i.issue_type == ValidationType.CIRCULAR_DEPENDENCY]
        assert len(circular_issues) == 0

    def test_detect_unresolved_references(self, validator, sample_ir):
        """Test detection of unresolved cross-references."""
        sample_ir.cross_references = [
            CrossReference(
                id="ref-1",
                source_id="section-1",
                source_type="section",
                target_id="section-999",
                target_type="section",
                reference_text="See Section 999",
                resolved=False,  # Unresolved
            )
        ]

        issues = validator.validate(sample_ir)

        missing_issues = [i for i in issues if i.issue_type == ValidationType.MISSING_REFERENCE]
        assert len(missing_issues) == 1
        assert "Section 999" in missing_issues[0].message

    def test_resolved_references_not_flagged(self, validator, sample_ir):
        """Test that resolved references are not flagged."""
        sample_ir.cross_references = [
            CrossReference(
                id="ref-1",
                source_id="section-1",
                source_type="section",
                target_id="section-2",
                target_type="section",
                reference_text="See Section 2",
                resolved=True,  # Resolved
            )
        ]

        issues = validator.validate(sample_ir)

        missing_issues = [i for i in issues if i.issue_type == ValidationType.MISSING_REFERENCE]
        assert len(missing_issues) == 0

    def test_multiple_validation_issues(self, validator, sample_ir):
        """Test that multiple issues are detected."""
        sample_ir.definitions = [
            TermDefinition(id="def-1", term="Term", definition="First", section_id="section-1"),
            TermDefinition(id="def-2", term="Term", definition="Second", section_id="section-1"),
        ]
        sample_ir.formulae = [
            FormulaReference(
                id="formula-1",
                latex="x = UndefinedVar",
                section_id="section-1",
                variables=["UndefinedVar"],
            )
        ]
        sample_ir.cross_references = [
            CrossReference(
                id="ref-1",
                source_id="section-1",
                source_type="section",
                target_id="missing",
                target_type="section",
                reference_text="Missing",
                resolved=False,
            )
        ]

        issues = validator.validate(sample_ir)

        # Should have at least one of each type
        assert len(issues) >= 3
        issue_types = {i.issue_type for i in issues}
        assert ValidationType.DUPLICATE_DEFINITION in issue_types
        assert ValidationType.UNDEFINED_VARIABLE in issue_types
        assert ValidationType.MISSING_REFERENCE in issue_types

    def test_validation_issue_has_suggestion(self, validator, sample_ir):
        """Test that validation issues include suggestions."""
        sample_ir.definitions = [
            TermDefinition(id="def-1", term="Dup", definition="First", section_id="section-1"),
            TermDefinition(id="def-2", term="Dup", definition="Second", section_id="section-1"),
        ]

        issues = validator.validate(sample_ir)

        assert len(issues) > 0
        assert issues[0].suggestion is not None
        assert len(issues[0].suggestion) > 0

    def test_no_issues_for_valid_ir(self, validator, sample_ir):
        """Test that a valid IR produces no validation issues."""
        sample_ir.definitions = [
            TermDefinition(id="def-1", term="Var1", definition="First var", section_id="section-1")
        ]
        sample_ir.formulae = [
            FormulaReference(
                id="formula-1",
                latex="Result = Var1 * 2",
                section_id="section-1",
                variables=["Var1"],
                dependencies=["def-1"],
            )
        ]

        issues = validator.validate(sample_ir)

        # No duplicate definitions, no undefined vars, no circular deps, no unresolved refs
        assert len(issues) == 0
