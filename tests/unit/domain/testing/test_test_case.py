"""Unit tests for TestCase, TestCategory, and TestResult."""

import pytest
from decimal import Decimal
from src.domain.testing.test_case import TestCase, TestCategory, TestResult


class TestTestCategory:
    """Tests for TestCategory enum."""

    def test_all_categories_defined(self):
        """Test that all expected categories are defined."""
        categories = {c.value for c in TestCategory}
        assert categories == {'normal', 'boundary', 'edge', 'error'}

    def test_category_values(self):
        """Test category enum values."""
        assert TestCategory.NORMAL.value == 'normal'
        assert TestCategory.BOUNDARY.value == 'boundary'
        assert TestCategory.EDGE.value == 'edge'
        assert TestCategory.ERROR.value == 'error'


class TestTestCase:
    """Tests for TestCase value object."""

    def test_create_basic_test_case(self):
        """Test creating a basic test case."""
        test_case = TestCase(
            id='test-001',
            name='Test basic calculation',
            category=TestCategory.NORMAL,
            inputs={'x': 10, 'y': 20},
            expected_output=Decimal('30'),
            description='Basic addition test'
        )
        
        assert test_case.id == 'test-001'
        assert test_case.name == 'Test basic calculation'
        assert test_case.category == TestCategory.NORMAL
        assert test_case.inputs == {'x': 10, 'y': 20}
        assert test_case.expected_output == Decimal('30')
        assert test_case.description == 'Basic addition test'
        assert test_case.precision is None
        assert test_case.tolerance is None

    def test_create_test_case_with_precision(self):
        """Test creating test case with precision."""
        test_case = TestCase(
            id='test-002',
            name='Test with precision',
            category=TestCategory.NORMAL,
            inputs={'rate': Decimal('0.05')},
            expected_output=Decimal('1.05127'),
            precision=5,
            description='Precision test'
        )
        
        assert test_case.precision == 5

    def test_create_test_case_with_tolerance(self):
        """Test creating test case with tolerance."""
        test_case = TestCase(
            id='test-003',
            name='Test with tolerance',
            category=TestCategory.BOUNDARY,
            inputs={'value': Decimal('999.999')},
            expected_output=Decimal('1000'),
            tolerance=Decimal('0.001'),
            description='Tolerance test'
        )
        
        assert test_case.tolerance == Decimal('0.001')

    def test_test_case_immutability(self):
        """Test that TestCase is immutable (frozen dataclass)."""
        test_case = TestCase(
            id='test-004',
            name='Immutable test',
            category=TestCategory.NORMAL,
            inputs={'x': 1},
            expected_output=1,
            description='Test immutability'
        )
        
        with pytest.raises(AttributeError):
            test_case.name = 'Modified name'

    def test_boundary_test_case(self):
        """Test boundary category test case."""
        test_case = TestCase(
            id='boundary-001',
            name='Boundary test',
            category=TestCategory.BOUNDARY,
            inputs={'value': 0},
            expected_output=0,
            description='Test zero boundary'
        )
        
        assert test_case.category == TestCategory.BOUNDARY

    def test_edge_test_case(self):
        """Test edge category test case."""
        test_case = TestCase(
            id='edge-001',
            name='Edge test',
            category=TestCategory.EDGE,
            inputs={'value': float('inf')},
            expected_output='ERROR',
            description='Test infinity edge case'
        )
        
        assert test_case.category == TestCategory.EDGE

    def test_error_test_case(self):
        """Test error category test case."""
        test_case = TestCase(
            id='error-001',
            name='Error test',
            category=TestCategory.ERROR,
            inputs={'value': -1},
            expected_output='ValueError',
            description='Test negative value error'
        )
        
        assert test_case.category == TestCategory.ERROR


class TestTestResult:
    """Tests for TestResult value object."""

    def test_passed_test_result(self):
        """Test creating a passed test result."""
        result = TestResult(
            test_case_id='test-001',
            passed=True,
            actual_output=Decimal('30'),
            expected_output=Decimal('30'),
            execution_time_ms=15.5,
            discrepancy=None,
            error_message=None
        )
        
        assert result.test_case_id == 'test-001'
        assert result.passed is True
        assert result.actual_output == Decimal('30')
        assert result.expected_output == Decimal('30')
        assert result.execution_time_ms == 15.5
        assert result.discrepancy is None
        assert result.error_message is None

    def test_failed_test_result_with_discrepancy(self):
        """Test creating a failed test result with discrepancy."""
        result = TestResult(
            test_case_id='test-002',
            passed=False,
            actual_output=Decimal('30.001'),
            expected_output=Decimal('30'),
            execution_time_ms=12.3,
            discrepancy=Decimal('0.001'),
            error_message=None
        )
        
        assert result.passed is False
        assert result.discrepancy == Decimal('0.001')

    def test_failed_test_result_with_error(self):
        """Test creating a failed test result with error."""
        result = TestResult(
            test_case_id='test-003',
            passed=False,
            actual_output=None,
            expected_output=Decimal('30'),
            execution_time_ms=5.0,
            discrepancy=None,
            error_message='ValueError: Invalid input'
        )
        
        assert result.passed is False
        assert result.actual_output is None
        assert result.error_message == 'ValueError: Invalid input'

    def test_test_result_immutability(self):
        """Test that TestResult is immutable."""
        result = TestResult(
            test_case_id='test-004',
            passed=True,
            actual_output=100,
            expected_output=100,
            execution_time_ms=10.0
        )
        
        with pytest.raises(AttributeError):
            result.passed = False

    def test_test_result_with_zero_execution_time(self):
        """Test result with zero execution time."""
        result = TestResult(
            test_case_id='test-005',
            passed=True,
            actual_output=1,
            expected_output=1,
            execution_time_ms=0.0
        )
        
        assert result.execution_time_ms == 0.0

    def test_test_result_with_large_discrepancy(self):
        """Test result with large discrepancy."""
        result = TestResult(
            test_case_id='test-006',
            passed=False,
            actual_output=Decimal('1000'),
            expected_output=Decimal('100'),
            execution_time_ms=8.5,
            discrepancy=Decimal('900')
        )
        
        assert result.discrepancy == Decimal('900')
        assert result.passed is False
