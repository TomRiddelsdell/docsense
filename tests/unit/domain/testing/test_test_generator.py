"""Unit tests for TestCaseGenerator."""

import pytest
from decimal import Decimal
from src.domain.testing.test_generator import TestCaseGenerator
from src.domain.testing.test_case import TestCategory
from src.domain.value_objects.semantic_ir import (
    DocumentIR,
    FormulaReference,
    IRSection,
    TermDefinition,
    SectionType
)


@pytest.fixture
def simple_formula():
    """Simple interest formula for testing."""
    return FormulaReference(
        id='formula-001',
        name='simple_interest',
        latex=r'I = P \times r \times t',
        section_id='section-1',
        variables=['P', 'r', 't'],
        plain_text='I = P * r * t'
    )


@pytest.fixture
def document_ir_with_formula(simple_formula):
    """DocumentIR containing simple formula and parameter definitions."""
    return DocumentIR(
        document_id='doc-001',
        title='Test Document',
        original_format='pdf',
        sections=[
            IRSection(
                id='section-1',
                title='Formulas',
                content='Test content',
                level=1,
                section_type=SectionType.NARRATIVE
            )
        ],
        definitions=[
            TermDefinition(
                id='def-P',
                term='P',
                definition='Principal amount: numeric value between 0 and 1000000',
                section_id='section-1'
            ),
            TermDefinition(
                id='def-r',
                term='r',
                definition='Interest rate: numeric value between 0 and 1',
                section_id='section-1'
            ),
            TermDefinition(
                id='def-t',
                term='t',
                definition='Time period: numeric value between 0 and 30 years',
                section_id='section-1'
            )
        ],
        formulae=[simple_formula],
        tables=[],
        cross_references=[],
        metadata={},
        raw_markdown='# Test'
    )


@pytest.fixture
def formula_with_calendar():
    """Formula with calendar dependency for testing edge cases."""
    return FormulaReference(
        id='formula-002',
        name='accrued_interest',
        latex=r'AI = P \times r \times \frac{days}{360}',
        section_id='section-1',
        variables=['P', 'r', 'start_date', 'end_date'],
        dependencies=['calendar'],
        plain_text='AI = P * r * days/360'
    )


class TestTestCaseGenerator:
    """Tests for TestCaseGenerator."""

    def test_initialization(self):
        """Test generator initialization."""
        generator = TestCaseGenerator()
        assert generator is not None

    def test_generate_from_formula_basic(self, simple_formula, document_ir_with_formula):
        """Test generating test cases from a basic formula."""
        generator = TestCaseGenerator()
        
        test_cases = generator.generate_from_formula(
            formula=simple_formula,
            document_ir=document_ir_with_formula,
            count_per_category={TestCategory.NORMAL: 5, TestCategory.BOUNDARY: 2, TestCategory.EDGE: 1, TestCategory.ERROR: 1}
        )
        
        # Should generate tests for all categories
        assert len(test_cases) > 0
        categories = {tc.category for tc in test_cases}
        assert TestCategory.NORMAL in categories

    def test_generate_normal_test_cases(self, simple_formula, document_ir_with_formula):
        """Test generating normal test cases."""
        generator = TestCaseGenerator()
        
        test_cases = generator.generate_from_formula(
            formula=simple_formula,
            document_ir=document_ir_with_formula,
            count_per_category={TestCategory.NORMAL: 10, TestCategory.BOUNDARY: 0, TestCategory.EDGE: 0, TestCategory.ERROR: 0}
        )
        
        normal_tests = [tc for tc in test_cases if tc.category == TestCategory.NORMAL]
        assert len(normal_tests) >= 5
        
        # Check that test cases have inputs
        for tc in normal_tests:
            assert tc.inputs is not None
            assert len(tc.inputs) > 0

    def test_generate_boundary_test_cases(self, simple_formula, document_ir_with_formula):
        """Test generating boundary test cases."""
        generator = TestCaseGenerator()
        
        test_cases = generator.generate_from_formula(
            formula=simple_formula,
            document_ir=document_ir_with_formula,
            count_per_category={TestCategory.NORMAL: 0, TestCategory.BOUNDARY: 5, TestCategory.EDGE: 0, TestCategory.ERROR: 0}
        )
        
        boundary_tests = [tc for tc in test_cases if tc.category == TestCategory.BOUNDARY]
        assert len(boundary_tests) >= 1
        
        # Boundary tests should have test cases
        assert len(boundary_tests) > 0

    def test_generate_edge_test_cases(self, simple_formula, document_ir_with_formula):
        """Test generating edge test cases."""
        generator = TestCaseGenerator()
        
        test_cases = generator.generate_from_formula(
            formula=simple_formula,
            document_ir=document_ir_with_formula,
            count_per_category={TestCategory.NORMAL: 0, TestCategory.BOUNDARY: 0, TestCategory.EDGE: 5, TestCategory.ERROR: 0}
        )
        
        edge_tests = [tc for tc in test_cases if tc.category == TestCategory.EDGE]
        assert len(edge_tests) >= 1

    def test_generate_error_test_cases(self, simple_formula, document_ir_with_formula):
        """Test generating error test cases."""
        generator = TestCaseGenerator()
        
        test_cases = generator.generate_from_formula(
            formula=simple_formula,
            document_ir=document_ir_with_formula,
            count_per_category={TestCategory.NORMAL: 0, TestCategory.BOUNDARY: 0, TestCategory.EDGE: 0, TestCategory.ERROR: 5}
        )
        
        error_tests = [tc for tc in test_cases if tc.category == TestCategory.ERROR]
        assert len(error_tests) >= 1
        
        # Error tests should exist and have description
        for tc in error_tests:
            assert tc.description is not None

    def test_generate_from_document(self, document_ir_with_formula):
        """Test generating test cases from entire document."""
        generator = TestCaseGenerator()
        
        test_suites = generator.generate_from_document(
            document_ir=document_ir_with_formula
        )
        
        assert isinstance(test_suites, dict)
        assert len(test_suites) > 0
        # Should have generated tests for the formula
        assert 'formula-001' in test_suites

    def test_calendar_edge_cases(self, formula_with_calendar):
        """Test generating calendar-specific edge cases."""
        generator = TestCaseGenerator()
        
        # Create minimal DocumentIR for calendar formula
        doc_ir = DocumentIR(
            document_id='doc-002',
            title='Calendar Test',
            original_format='pdf',
            sections=[IRSection(id='s1', title='Test', content='', level=1, section_type=SectionType.NARRATIVE)],
            definitions=[],
            formulae=[formula_with_calendar],
            tables=[],
            cross_references=[],
            metadata={},
            raw_markdown=''
        )
        
        test_cases = generator.generate_from_formula(
            formula=formula_with_calendar,
            document_ir=doc_ir,
            count_per_category={TestCategory.NORMAL: 2, TestCategory.BOUNDARY: 0, TestCategory.EDGE: 5, TestCategory.ERROR: 0}
        )
        
        edge_tests = [tc for tc in test_cases if tc.category == TestCategory.EDGE]
        # Should generate edge test cases
        assert len(edge_tests) > 0

    def test_test_case_ids_unique(self, simple_formula, document_ir_with_formula):
        """Test that generated test case IDs are unique."""
        generator = TestCaseGenerator()
        
        test_cases = generator.generate_from_formula(
            formula=simple_formula,
            document_ir=document_ir_with_formula,
            count_per_category={TestCategory.NORMAL: 10, TestCategory.BOUNDARY: 5, TestCategory.EDGE: 3, TestCategory.ERROR: 2}
        )
        
        ids = [tc.id for tc in test_cases]
        assert len(ids) == len(set(ids))  # All IDs should be unique

    def test_test_case_names_descriptive(self, simple_formula, document_ir_with_formula):
        """Test that test case names are descriptive."""
        generator = TestCaseGenerator()
        
        test_cases = generator.generate_from_formula(
            formula=simple_formula,
            document_ir=document_ir_with_formula,
            count_per_category={TestCategory.NORMAL: 5, TestCategory.BOUNDARY: 2, TestCategory.EDGE: 1, TestCategory.ERROR: 1}
        )
        
        for tc in test_cases:
            # Names should exist and be non-empty
            assert tc.name is not None
            assert len(tc.name) > 0

    def test_precision_handling_in_tests(self, simple_formula, document_ir_with_formula):
        """Test that test cases are generated with proper structure."""
        generator = TestCaseGenerator()
        
        test_cases = generator.generate_from_formula(
            formula=simple_formula,
            document_ir=document_ir_with_formula,
            count_per_category={TestCategory.NORMAL: 10, TestCategory.BOUNDARY: 0, TestCategory.EDGE: 0, TestCategory.ERROR: 0}
        )
        
        # Test cases should have valid structure
        for tc in test_cases:
            assert tc.id is not None
            assert tc.name is not None
            assert tc.category == TestCategory.NORMAL
            assert isinstance(tc.inputs, dict)
            assert len(tc.inputs) > 0

    def test_empty_count_per_category(self, simple_formula, document_ir_with_formula):
        """Test with empty count per category."""
        generator = TestCaseGenerator()
        
        test_cases = generator.generate_from_formula(
            formula=simple_formula,
            document_ir=document_ir_with_formula,
            count_per_category={TestCategory.NORMAL: 0, TestCategory.BOUNDARY: 0, TestCategory.EDGE: 0, TestCategory.ERROR: 0}
        )
        
        assert len(test_cases) == 0

    def test_large_count_generation(self, simple_formula, document_ir_with_formula):
        """Test generating a large number of test cases."""
        generator = TestCaseGenerator()
        
        test_cases = generator.generate_from_formula(
            formula=simple_formula,
            document_ir=document_ir_with_formula,
            count_per_category={TestCategory.NORMAL: 50, TestCategory.BOUNDARY: 10, TestCategory.EDGE: 5, TestCategory.ERROR: 5}
        )
        
        assert len(test_cases) >= 50  # Should generate at least the normal count
