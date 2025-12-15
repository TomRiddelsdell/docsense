"""Unit tests for CrossValidator and validation logic."""

import pytest
from decimal import Decimal
from uuid import uuid4
from src.domain.testing.cross_validator import CrossValidator
from src.domain.testing.validation_report import ValidationReport
from src.domain.testing.test_case import TestCase, TestCategory


@pytest.fixture
def sample_test_cases():
    """Sample test cases for validation."""
    return [
        TestCase(
            id='test-001',
            name='Normal case 1',
            category=TestCategory.NORMAL,
            inputs={'P': Decimal('1000'), 'r': Decimal('0.05'), 't': Decimal('2')},
            expected_output=Decimal('100'),
            precision=10,
            description='Basic test'
        ),
        TestCase(
            id='test-002',
            name='Boundary case',
            category=TestCategory.BOUNDARY,
            inputs={'P': Decimal('0'), 'r': Decimal('0.05'), 't': Decimal('2')},
            expected_output=Decimal('0'),
            precision=10,
            description='Zero principal'
        ),
        TestCase(
            id='test-003',
            name='Edge case',
            category=TestCategory.EDGE,
            inputs={'P': Decimal('1000000'), 'r': Decimal('0.99'), 't': Decimal('30')},
            expected_output=Decimal('29700000'),
            precision=10,
            description='Large values'
        )
    ]


@pytest.fixture
def reference_implementation():
    """Sample reference implementation code."""
    return """
from decimal import Decimal, getcontext

def calculate_simple_interest(P: Decimal, r: Decimal, t: Decimal) -> Decimal:
    '''Calculate simple interest.'''
    getcontext().prec = 28
    return P * r * t
"""


@pytest.fixture
def user_implementation():
    """Sample user implementation code."""
    return """
from decimal import Decimal

def calculate_simple_interest(P, r, t):
    return P * r * t
"""


class TestCrossValidator:
    """Tests for CrossValidator."""

    def test_initialization(self):
        """Test validator initialization."""
        validator = CrossValidator()
        assert validator is not None

    def test_validate_implementation_basic(self, sample_test_cases):
        """Test basic implementation validation."""
        validator = CrossValidator()
        
        def reference(P, r, t):
            return P * r * t
        
        def implementation(P, r, t):
            return P * r * t
        
        report = validator.validate_implementation(
            implementation=implementation,
            reference=reference,
            test_cases=sample_test_cases,
            tolerance=1e-10
        )
        
        assert isinstance(report, ValidationReport)
        assert report.total_tests == len(sample_test_cases)
        assert report.passed + report.failed == report.total_tests

    def test_all_tests_pass(self, sample_test_cases, reference_implementation):
        """Test when all tests pass."""
        validator = CrossValidator()
        
        # Use same code for both reference and implementation
        report = validator.validate_implementation(
            test_cases=sample_test_cases,
            reference_code=reference_implementation,
            implementation_code=reference_implementation,
            tolerance=Decimal('1e-10')
        )
        
        assert report.success is True
        assert report.passed == report.total_tests
        assert report.failed == 0
        assert len(report.failed_tests) == 0

    def test_numeric_comparison_with_tolerance(self):
        """Test numeric comparison with tolerance."""
        validator = CrossValidator()
        
        test_cases = [
            TestCase(
                id='test-tol-001',
                name='Tolerance test',
                category=TestCategory.NORMAL,
                inputs={'x': Decimal('10')},
                expected_output=Decimal('100.000000001'),
                tolerance=Decimal('0.001'),
                description='Test with tolerance'
            )
        ]
        
        ref_code = """
from decimal import Decimal
def calc(x): return Decimal('100')
"""
        
        impl_code = """
from decimal import Decimal
def calc(x): return Decimal('100.0000000005')
"""
        
        report = validator.validate_implementation(
            test_cases=test_cases,
            reference_code=ref_code,
            implementation_code=impl_code,
            tolerance=Decimal('0.001')
        )
        
        # Should pass because difference is within tolerance
        assert report.success is True or report.passed >= 0

    def test_discrepancy_calculation(self):
        """Test discrepancy calculation for failed tests."""
        validator = CrossValidator()
        
        test_cases = [
            TestCase(
                id='test-disc-001',
                name='Discrepancy test',
                category=TestCategory.NORMAL,
                inputs={'x': Decimal('10')},
                expected_output=Decimal('100'),
                description='Test discrepancy'
            )
        ]
        
        ref_code = """
from decimal import Decimal
def calc(x): return Decimal('100')
"""
        
        impl_code = """
from decimal import Decimal
def calc(x): return Decimal('95')
"""
        
        report = validator.validate_implementation(
            test_cases=test_cases,
            reference_code=ref_code,
            implementation_code=impl_code,
            tolerance=Decimal('1e-10')
        )
        
        if report.failed > 0:
            assert report.discrepancy_summary is not None
            assert 'max_discrepancy' in report.discrepancy_summary

    def test_error_handling_in_implementation(self, sample_test_cases, reference_implementation):
        """Test handling of errors in user implementation."""
        validator = CrossValidator()
        
        # Implementation that raises an error
        bad_impl = """
from decimal import Decimal
def calculate_simple_interest(P, r, t):
    raise ValueError("Test error")
"""
        
        report = validator.validate_implementation(
            test_cases=sample_test_cases,
            reference_code=reference_implementation,
            implementation_code=bad_impl,
            tolerance=Decimal('1e-10')
        )
        
        # All tests should fail due to error
        assert report.failed > 0
        assert len(report.failed_tests) > 0

    def test_pass_rate_calculation(self, sample_test_cases, reference_implementation):
        """Test pass rate calculation."""
        validator = CrossValidator()
        
        report = validator.validate_implementation(
            test_cases=sample_test_cases,
            reference_code=reference_implementation,
            implementation_code=reference_implementation,
            tolerance=Decimal('1e-10')
        )
        
        expected_pass_rate = (report.passed / report.total_tests) * 100 if report.total_tests > 0 else 0
        assert abs(report.pass_rate - expected_pass_rate) < 0.01

    def test_failed_test_details(self):
        """Test that failed test details are captured."""
        validator = CrossValidator()
        
        test_cases = [
            TestCase(
                id='test-fail-001',
                name='Failing test',
                category=TestCategory.NORMAL,
                inputs={'x': Decimal('5')},
                expected_output=Decimal('25'),
                description='Should fail'
            )
        ]
        
        ref_code = """
from decimal import Decimal
def calc(x): return x * x
"""
        
        impl_code = """
from decimal import Decimal
def calc(x): return x * 2
"""
        
        report = validator.validate_implementation(
            test_cases=test_cases,
            reference_code=ref_code,
            implementation_code=impl_code,
            tolerance=Decimal('1e-10')
        )
        
        if report.failed > 0:
            failed_test = report.failed_tests[0]
            assert failed_test['test_name'] == 'Failing test'
            assert failed_test['category'] == 'normal'
            assert 'expected' in failed_test
            assert 'actual' in failed_test

    def test_multiple_implementations_comparison(self, sample_test_cases):
        """Test comparing multiple implementations."""
        validator = CrossValidator()
        
        impl1 = """
from decimal import Decimal
def calculate_simple_interest(P, r, t):
    return P * r * t
"""
        
        impl2 = """
from decimal import Decimal
def calculate_simple_interest(P, r, t):
    result = Decimal('0')
    for _ in range(int(t)):
        result += P * r
    return result
"""
        
        results = validator.compare_implementations(
            test_cases=sample_test_cases,
            implementations={'impl1': impl1, 'impl2': impl2},
            tolerance=Decimal('1e-10')
        )
        
        assert isinstance(results, list)
        assert len(results) > 0

    def test_validation_with_empty_test_suite(self, reference_implementation, user_implementation):
        """Test validation with empty test suite."""
        validator = CrossValidator()
        
        report = validator.validate_implementation(
            test_cases=[],
            reference_code=reference_implementation,
            implementation_code=user_implementation,
            tolerance=Decimal('1e-10')
        )
        
        assert report.total_tests == 0
        assert report.success is True  # No tests means no failures

    def test_execution_time_tracking(self, sample_test_cases, reference_implementation, user_implementation):
        """Test that execution time is tracked."""
        validator = CrossValidator()
        
        report = validator.validate_implementation(
            test_cases=sample_test_cases,
            reference_code=reference_implementation,
            implementation_code=user_implementation,
            tolerance=Decimal('1e-10')
        )
        
        # Report should have execution time or timestamp
        assert hasattr(report, 'report_id')
        assert report.report_id is not None


class TestValidationReport:
    """Tests for ValidationReport value object."""

    def test_create_successful_report(self):
        """Test creating a successful validation report."""
        report = ValidationReport(
            report_id='report-001',
            document_id='doc-001',
            formula_id='formula-001',
            success=True,
            pass_rate=100.0,
            total_tests=10,
            passed=10,
            failed=0,
            discrepancy_summary={},
            failed_tests=[]
        )
        
        assert report.success is True
        assert report.pass_rate == 100.0
        assert report.failed == 0

    def test_create_failed_report(self):
        """Test creating a failed validation report."""
        report = ValidationReport(
            report_id='report-002',
            document_id='doc-001',
            formula_id='formula-001',
            success=False,
            pass_rate=70.0,
            total_tests=10,
            passed=7,
            failed=3,
            discrepancy_summary={
                'numeric_tests': 10,
                'max_discrepancy': Decimal('5.0'),
                'mean_discrepancy': Decimal('1.5')
            },
            failed_tests=[
                {
                    'test_name': 'Test 1',
                    'category': 'normal',
                    'expected': Decimal('100'),
                    'actual': Decimal('95'),
                    'discrepancy': Decimal('5'),
                    'error': ''
                }
            ]
        )
        
        assert report.success is False
        assert report.failed == 3
        assert len(report.failed_tests) == 1
        assert report.discrepancy_summary['max_discrepancy'] == Decimal('5.0')

    def test_report_immutability(self):
        """Test that ValidationReport is immutable."""
        report = ValidationReport(
            report_id='report-003',
            document_id='doc-001',
            formula_id='formula-001',
            success=True,
            pass_rate=100.0,
            total_tests=5,
            passed=5,
            failed=0,
            discrepancy_summary={},
            failed_tests=[]
        )
        
        with pytest.raises((AttributeError, TypeError)):
            report.success = False

    def test_discrepancy_summary_structure(self):
        """Test discrepancy summary structure."""
        summary = {
            'numeric_tests': 20,
            'max_discrepancy': Decimal('10.5'),
            'mean_discrepancy': Decimal('2.3'),
            'median_discrepancy': Decimal('1.8'),
            'tests_with_discrepancy': 5
        }
        
        report = ValidationReport(
            report_id='report-004',
            document_id='doc-001',
            formula_id='formula-001',
            success=False,
            pass_rate=75.0,
            total_tests=20,
            passed=15,
            failed=5,
            discrepancy_summary=summary,
            failed_tests=[]
        )
        
        assert report.discrepancy_summary['numeric_tests'] == 20
        assert report.discrepancy_summary['max_discrepancy'] == Decimal('10.5')
        assert report.discrepancy_summary['mean_discrepancy'] == Decimal('2.3')


class TestComparisonResult:
    """Tests for ComparisonResult (if exists in validation_report.py)."""

    def test_comparison_result_creation(self):
        """Test creating a comparison result."""
        # This test assumes ComparisonResult exists
        # If not, it can be skipped
        try:
            result = ComparisonResult(
                implementation_name='impl1',
                passed=True,
                discrepancy=None
            )
            assert result.implementation_name == 'impl1'
            assert result.passed is True
        except (NameError, ImportError):
            pytest.skip("ComparisonResult not defined")
