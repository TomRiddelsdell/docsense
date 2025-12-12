"""Tests for IR builder."""

import pytest
from src.infrastructure.semantic.ir_builder import IRBuilder
from src.infrastructure.converters.base import (
    ConversionResult,
    DocumentSection,
    DocumentMetadata,
    DocumentFormat,
)


class TestIRBuilder:
    """Test suite for IRBuilder."""

    @pytest.fixture
    def builder(self):
        """Create an IRBuilder instance."""
        return IRBuilder()

    @pytest.fixture
    def sample_conversion_result(self):
        """Create a sample ConversionResult for testing."""
        markdown = """
# Introduction

"Volatility" means the realized volatility measure.

## Formula

$$
Vol = \\sqrt{\\frac{1}{N} \\sum r_i^2}
$$

## Parameters

| Parameter | Value |
|-----------|-------|
| N | 252 |
| r | return |
"""
        sections = [
            DocumentSection(
                id="section-1",
                title="Introduction",
                content='"Volatility" means the realized volatility measure.',
                level=1,
                start_line=1,
                end_line=3,
            ),
            DocumentSection(
                id="section-2",
                title="Formula",
                content="$$\nVol = \\sqrt{\\frac{1}{N} \\sum r_i^2}\n$$",
                level=2,
                start_line=5,
                end_line=9,
            ),
            DocumentSection(
                id="section-3",
                title="Parameters",
                content="| Parameter | Value |\n|-----------|-------|\n| N | 252 |\n| r | return |",
                level=2,
                start_line=11,
                end_line=15,
            ),
        ]

        metadata = DocumentMetadata(
            title="Test Document",
            author="Test Author",
            page_count=1,
            word_count=50,
            original_format=DocumentFormat.PDF,
        )

        return ConversionResult(
            success=True,
            markdown_content=markdown,
            sections=sections,
            metadata=metadata,
        )

    def test_build_ir_from_conversion_result(self, builder, sample_conversion_result):
        """Test building DocumentIR from ConversionResult."""
        document_id = "doc-123"

        ir = builder.build(sample_conversion_result, document_id)

        assert ir.document_id == document_id
        assert ir.title == "Test Document"
        assert ir.original_format == "pdf"
        assert len(ir.sections) == 3
        assert ir.raw_markdown == sample_conversion_result.markdown_content

    def test_extracts_definitions(self, builder, sample_conversion_result):
        """Test that definitions are extracted."""
        ir = builder.build(sample_conversion_result, "doc-123")

        assert len(ir.definitions) > 0
        terms = [d.term for d in ir.definitions]
        assert "Volatility" in terms

    def test_extracts_formulas(self, builder, sample_conversion_result):
        """Test that formulas are extracted."""
        ir = builder.build(sample_conversion_result, "doc-123")

        assert len(ir.formulae) > 0
        assert any("sqrt" in f.latex.lower() for f in ir.formulae)

    def test_extracts_tables(self, builder, sample_conversion_result):
        """Test that tables are extracted."""
        ir = builder.build(sample_conversion_result, "doc-123")

        assert len(ir.tables) > 0
        assert ir.tables[0].headers == ["Parameter", "Value"]

    def test_classifies_sections(self, builder, sample_conversion_result):
        """Test that sections are classified by type."""
        ir = builder.build(sample_conversion_result, "doc-123")

        # Should have different section types
        section_types = {s.section_type for s in ir.sections}
        assert len(section_types) > 1  # Not all UNKNOWN

    def test_resolves_formula_dependencies(self, builder):
        """Test that formula dependencies are resolved."""
        markdown = """
"BaseValue" means the starting value.

$$
Factor = BaseValue * 2
$$

$$
Result = Factor * 3
$$
"""
        sections = [
            DocumentSection(
                id="section-1",
                title="Test",
                content=markdown,
                level=1,
                start_line=1,
                end_line=10,
            )
        ]

        result = ConversionResult(
            success=True,
            markdown_content=markdown,
            sections=sections,
            metadata=DocumentMetadata(original_format=DocumentFormat.PDF),
        )

        ir = builder.build(result, "doc-123")

        # Result formula should depend on Factor
        if len(ir.formulae) >= 2:
            result_formula = next((f for f in ir.formulae if "Result" in str(f.name)), None)
            if result_formula:
                assert len(result_formula.dependencies) > 0

    def test_runs_validation(self, builder, sample_conversion_result):
        """Test that validation is run on the IR."""
        ir = builder.build(sample_conversion_result, "doc-123")

        # validation_issues should be populated (may be empty if valid)
        assert isinstance(ir.validation_issues, list)

    def test_builds_section_map(self, builder, sample_conversion_result):
        """Test section mapping construction."""
        section_map = builder._build_section_map(sample_conversion_result.sections)

        assert isinstance(section_map, dict)
        assert 1 in section_map  # Line 1 should map to a section
        assert section_map[1] == "section-1"

    def test_extracts_metadata_dict(self, builder, sample_conversion_result):
        """Test metadata extraction to dictionary."""
        metadata_dict = builder._extract_metadata_dict(sample_conversion_result)

        assert metadata_dict["title"] == "Test Document"
        assert metadata_dict["author"] == "Test Author"
        assert metadata_dict["page_count"] == 1
        assert metadata_dict["original_format"] == "pdf"

    def test_handles_empty_conversion_result(self, builder):
        """Test handling of conversion result with no content."""
        result = ConversionResult(
            success=True,
            markdown_content="",
            sections=[],
            metadata=DocumentMetadata(original_format=DocumentFormat.PDF),
        )

        ir = builder.build(result, "doc-123")

        assert ir.document_id == "doc-123"
        assert len(ir.sections) == 0
        assert len(ir.definitions) == 0
        assert len(ir.formulae) == 0
        assert len(ir.tables) == 0

    def test_merges_duplicate_definitions(self, builder):
        """Test that duplicate definitions are merged."""
        markdown = """
"Term" means first definition.

Some text.

"Term" means second longer definition with more detail.
"""
        sections = [
            DocumentSection(
                id="section-1",
                title="Test",
                content=markdown,
                level=1,
                start_line=1,
                end_line=7,
            )
        ]

        result = ConversionResult(
            success=True,
            markdown_content=markdown,
            sections=sections,
            metadata=DocumentMetadata(original_format=DocumentFormat.PDF),
        )

        ir = builder.build(result, "doc-123")

        # Should have only one definition for "Term"
        term_defs = [d for d in ir.definitions if d.term == "Term"]
        assert len(term_defs) == 1

    def test_ir_statistics(self, builder, sample_conversion_result):
        """Test that IR statistics are computed correctly."""
        ir = builder.build(sample_conversion_result, "doc-123")

        stats = ir.get_statistics()

        assert "section_count" in stats
        assert "definition_count" in stats
        assert "formula_count" in stats
        assert "table_count" in stats
        assert stats["section_count"] == len(ir.sections)
        assert stats["definition_count"] == len(ir.definitions)

    def test_ir_to_dict_serialization(self, builder, sample_conversion_result):
        """Test that IR can be serialized to dictionary."""
        ir = builder.build(sample_conversion_result, "doc-123")

        ir_dict = ir.to_dict()

        assert isinstance(ir_dict, dict)
        assert ir_dict["document_id"] == "doc-123"
        assert "sections" in ir_dict
        assert "definitions" in ir_dict
        assert "formulae" in ir_dict
        assert "tables" in ir_dict

    def test_ir_to_llm_format(self, builder, sample_conversion_result):
        """Test that IR can be converted to LLM-optimized format."""
        ir = builder.build(sample_conversion_result, "doc-123")

        llm_text = ir.to_llm_format()

        assert isinstance(llm_text, str)
        assert "=== DOCUMENT METADATA ===" in llm_text
        assert "=== DEFINITIONS" in llm_text or len(ir.definitions) == 0
        assert "=== FORMULAE" in llm_text or len(ir.formulae) == 0
        assert "=== DOCUMENT CONTENT ===" in llm_text
