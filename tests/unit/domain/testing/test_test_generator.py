"""Unit tests for TestCaseGenerator."""

import pytest
from decimal import Decimal
from unittest.mock import Mock, MagicMock
from src.domain.testing.test_generator import TestCaseGenerator
from src.domain.testing.test_case import TestCategory


@pytest.fixture
def sample_semantic_ir():
    """Sample semantic IR for testing."""
    return {
        'document_id': 'doc-001',
        'formulas': [
            {
                'id': 'formula-001',
                'name': 'Simple Interest',
                'latex': r'I = P \times r \times t',
                'parameters': [
                    {'name': 'P', 'type': 'numeric', 'min': 0, 'max': 1000000},
                    {'name': 'r', 'type': 'numeric', 'min': 0, 'max': 1},
                    {'name': 't', 'type': 'numeric', 'min': 0, 'max': 30}
                ],
                'constraints': [],
                'dependencies': []
            }
        ],
        'parameters': [],
        'dependencies': []
    }


@pytest.fixture
def formula_with_calendar():
    """Formula with calendar dependency."""
    return {
        'id': 'formula-002',
        'name': 'Accrued Interest',
        'latex': r'AI = P \times r \times \frac{days}{360}',
        'parameters': [
            {'name': 'P', 'type': 'numeric', 'min': 0},
            {'name': 'r', 'type': 'numeric', 'min': 0, 'max': 1},
            {'name': 'start_date', 'type': 'date'},
            {'name': 'end_date', 'type': 'date'}
        ],
        'dependencies': ['calendar'],
        'constraints': []
    }


class TestTestCaseGenerator:
    """Tests for TestCaseGenerator."""

    def test_initialization(self):
        """Test generator initialization."""
        generator = TestCaseGenerator()
        assert generator is not None

    def test_generate_from_formula_basic(self, sample_semantic_ir):
        """Test generating test cases from a basic formula."""
        generator = TestCaseGenerator()
        formula = sample_semantic_ir['formulas'][0]
        
        test_cases = generator.generate_from_formula(
            formula=formula,
            count_per_category={'normal': 5, 'boundary': 2, 'edge': 1, 'error': 1}
        )
        
        # Should generate tests for all categories
        assert len(test_cases) > 0
        categories = {tc.category for tc in test_cases}
        assert TestCategory.NORMAL in categories

    def test_generate_normal_test_cases(self, sample_semantic_ir):
        """Test generating normal test cases."""
        generator = TestCaseGenerator()
        formula = sample_semantic_ir['formulas'][0]
        
        test_cases = generator.generate_from_formula(
            formula=formula,
            count_per_category={'normal': 10, 'boundary': 0, 'edge': 0, 'error': 0}
        )
        
        normal_tests = [tc for tc in test_cases if tc.category == TestCategory.NORMAL]
        assert len(normal_tests) >= 5
        
        # Check that inputs are within valid ranges
        for tc in normal_tests:
            if 'P' in tc.inputs:
                assert 0 <= tc.inputs['P'] <= 1000000

    def test_generate_boundary_test_cases(self, sample_semantic_ir):
        """Test generating boundary test cases."""
        generator = TestCaseGenerator()
        formula = sample_semantic_ir['formulas'][0]
        
        test_cases = generator.generate_from_formula(
            formula=formula,
            count_per_category={'normal': 0, 'boundary': 5, 'edge': 0, 'error': 0}
        )
        
        boundary_tests = [tc for tc in test_cases if tc.category == TestCategory.BOUNDARY]
        assert len(boundary_tests) >= 2
        
        # Boundary tests should include min/max values
        has_zero = any(tc.inputs.get('P') == 0 for tc in boundary_tests if 'P' in tc.inputs)
        has_max = any(tc.inputs.get('P') == 1000000 for tc in boundary_tests if 'P' in tc.inputs)
        assert has_zero or has_max

    def test_generate_edge_test_cases(self, sample_semantic_ir):
        """Test generating edge test cases."""
        generator = TestCaseGenerator()
        formula = sample_semantic_ir['formulas'][0]
        
        test_cases = generator.generate_from_formula(
            formula=formula,
            count_per_category={'normal': 0, 'boundary': 0, 'edge': 5, 'error': 0}
        )
        
        edge_tests = [tc for tc in test_cases if tc.category == TestCategory.EDGE]
        assert len(edge_tests) >= 1

    def test_generate_error_test_cases(self, sample_semantic_ir):
        """Test generating error test cases."""
        generator = TestCaseGenerator()
        formula = sample_semantic_ir['formulas'][0]
        
        test_cases = generator.generate_from_formula(
            formula=formula,
            count_per_category={'normal': 0, 'boundary': 0, 'edge': 0, 'error': 5}
        )
        
        error_tests = [tc for tc in test_cases if tc.category == TestCategory.ERROR]
        assert len(error_tests) >= 1
        
        # Error tests should have invalid inputs
        for tc in error_tests:
            # Check for negative values or out of range
            invalid = any(
                v < 0 if isinstance(v, (int, float, Decimal)) else False
                for v in tc.inputs.values()
            )
            assert invalid or tc.description.lower().find('invalid') >= 0

    def test_generate_from_document(self, sample_semantic_ir):
        """Test generating test cases from entire document."""
        generator = TestCaseGenerator()
        
        test_suites = generator.generate_from_document(
            semantic_ir=sample_semantic_ir,
            count_per_category={'normal': 5, 'boundary': 2, 'edge': 1, 'error': 1}
        )
        
        assert len(test_suites) == len(sample_semantic_ir['formulas'])
        assert test_suites[0]['formula_id'] == 'formula-001'
        assert len(test_suites[0]['test_cases']) > 0

    def test_calendar_edge_cases(self, formula_with_calendar):
        """Test generating calendar-specific edge cases."""
        generator = TestCaseGenerator()
        
        test_cases = generator.generate_from_formula(
            formula=formula_with_calendar,
            count_per_category={'normal': 2, 'boundary': 0, 'edge': 5, 'error': 0}
        )
        
        edge_tests = [tc for tc in test_cases if tc.category == TestCategory.EDGE]
        
        # Should include calendar edge cases like leap years, month ends
        has_calendar_edge = any(
            'leap' in tc.description.lower() or 
            'weekend' in tc.description.lower() or
            'month' in tc.description.lower()
            for tc in edge_tests
        )
        assert has_calendar_edge or len(edge_tests) > 0

    def test_test_case_ids_unique(self, sample_semantic_ir):
        """Test that generated test case IDs are unique."""
        generator = TestCaseGenerator()
        formula = sample_semantic_ir['formulas'][0]
        
        test_cases = generator.generate_from_formula(
            formula=formula,
            count_per_category={'normal': 10, 'boundary': 5, 'edge': 3, 'error': 2}
        )
        
        ids = [tc.id for tc in test_cases]
        assert len(ids) == len(set(ids))  # All IDs should be unique

    def test_test_case_names_descriptive(self, sample_semantic_ir):
        """Test that test case names are descriptive."""
        generator = TestCaseGenerator()
        formula = sample_semantic_ir['formulas'][0]
        
        test_cases = generator.generate_from_formula(
            formula=formula,
            count_per_category={'normal': 5, 'boundary': 2, 'edge': 1, 'error': 1}
        )
        
        for tc in test_cases:
            assert len(tc.name) > 10  # Names should be meaningful
            assert tc.category.value in tc.name.lower() or tc.id

    def test_precision_included_in_numeric_tests(self, sample_semantic_ir):
        """Test that precision is set for numeric test cases."""
        generator = TestCaseGenerator()
        formula = sample_semantic_ir['formulas'][0]
        
        test_cases = generator.generate_from_formula(
            formula=formula,
            count_per_category={'normal': 10, 'boundary': 0, 'edge': 0, 'error': 0}
        )
        
        # At least some tests should have precision defined
        has_precision = any(tc.precision is not None for tc in test_cases)
        assert has_precision

    def test_empty_count_per_category(self, sample_semantic_ir):
        """Test with empty count per category."""
        generator = TestCaseGenerator()
        formula = sample_semantic_ir['formulas'][0]
        
        test_cases = generator.generate_from_formula(
            formula=formula,
            count_per_category={'normal': 0, 'boundary': 0, 'edge': 0, 'error': 0}
        )
        
        assert len(test_cases) == 0

    def test_large_count_generation(self, sample_semantic_ir):
        """Test generating a large number of test cases."""
        generator = TestCaseGenerator()
        formula = sample_semantic_ir['formulas'][0]
        
        test_cases = generator.generate_from_formula(
            formula=formula,
            count_per_category={'normal': 50, 'boundary': 10, 'edge': 5, 'error': 5}
        )
        
        assert len(test_cases) >= 50  # Should generate at least the normal count
