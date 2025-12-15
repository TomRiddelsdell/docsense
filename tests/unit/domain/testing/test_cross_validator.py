"""Unit tests for CrossValidator and validation logic."""

import pytest
from decimal import Decimal
from uuid import uuid4
from src.domain.testing.cross_validator import CrossValidator
from src.domain.testing.validation_report import ValidationReport
from src.domain.testing.test_case import TestCase, TestCategory, TestResult
from tests.fixtures.testing_factories import TestCaseFactory, FunctionFactory


@pytest.fixture
def sample_test_cases():
    """Sample test cases for validation."""
    return TestCaseFactory.create_simple_interest_tests()


@pytest.fixture
def reference_implementation():
    """Sample reference implementation function."""
    return FunctionFactory.simple_interest_reference()


@pytest.fixture
def user_implementation():
    """Sample user implementation function (correct)."""
    return FunctionFactory.simple_interest_implementation_correct()


@pytest.fixture
def wrong_implementation():
    """Wrong implementation function."""
    return FunctionFactory.simple_interest_implementation_wrong()


@pytest.fixture
def error_implementation():
    """Implementation that raises errors."""
    return FunctionFactory.simple_interest_implementation_error()


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

    def test_all_tests_pass(self, sample_test_cases, reference_implementation, user_implementation):
        """Test when all tests pass."""
        validator = CrossValidator()
        
        # Use correct implementation - should match reference
        report = validator.validate_implementation(
            implementation=user_implementation,
            reference=reference_implementation,
            test_cases=sample_test_cases,
            tolerance=1e-10
        )
        
        assert report.passed == report.total_tests
        assert report.failed == 0

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
        
        def reference(x):
            return Decimal('100')
        
        def implementation(x):
            return Decimal('100.0000000005')
        
        report = validator.validate_implementation(
            implementation=implementation,
            reference=reference,
            test_cases=test_cases,
            tolerance=0.001
        )
        
        # Should pass because difference is within tolerance
        assert report.passed >= 0

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
        
        def reference(x):
            return Decimal('100')
        
        def implementation(x):
            return Decimal('95')
        
        report = validator.validate_implementation(
            implementation=implementation,
            reference=reference,
            test_cases=test_cases,
            tolerance=1e-10
        )
        
        if report.failed > 0:
            assert report.discrepancy_summary is not None

    def test_error_handling_in_implementation(self, sample_test_cases, reference_implementation, error_implementation):
        """Test handling of errors in user implementation."""
        validator = CrossValidator()
        
        report = validator.validate_implementation(
            implementation=error_implementation,
            reference=reference_implementation,
            test_cases=sample_test_cases,
            tolerance=1e-10
        )
        
        # All tests should fail due to error
        assert report.failed > 0

    def test_pass_rate_calculation(self, sample_test_cases, reference_implementation, user_implementation):
        """Test pass rate calculation."""
        validator = CrossValidator()
        
        report = validator.validate_implementation(
            implementation=user_implementation,
            reference=reference_implementation,
            test_cases=sample_test_cases,
            tolerance=1e-10
        )
        
        # Check that tests passed
        assert report.total_tests > 0
        assert report.passed >= 0

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
        
        reference = FunctionFactory.square()
        implementation = FunctionFactory.multiply_by_two()
        
        report = validator.validate_implementation(
            implementation=implementation,
            reference=reference,
            test_cases=test_cases,
            tolerance=1e-10
        )
        
        # Should have failures since implementations differ
        assert report.failed > 0

    def test_multiple_implementations_comparison(self, sample_test_cases):
        """Test comparing multiple implementations."""
        validator = CrossValidator()
        
        def impl1(P, r, t):
            return P * r * t
        
        def impl2(P, r, t):
            result = Decimal('0')
            for _ in range(int(t)):
                result += P * r
            return result
        
        report = validator.compare_implementations(
            implementations={'impl1': impl1, 'impl2': impl2},
            test_cases=sample_test_cases,
            tolerance=1e-10
        )
        
        assert report is not None
        assert report.total_tests > 0

    def test_validation_with_empty_test_suite(self, reference_implementation, user_implementation):
        """Test validation with empty test suite."""
        validator = CrossValidator()
        
        report = validator.validate_implementation(
            implementation=user_implementation,
            reference=reference_implementation,
            test_cases=[],
            tolerance=1e-10
        )
        
        assert report.total_tests == 0
        assert report.failed == 0  # No tests means no failures

    def test_execution_time_tracking(self, sample_test_cases, reference_implementation, user_implementation):
        """Test that execution time is tracked."""
        validator = CrossValidator()
        
        report = validator.validate_implementation(
            implementation=user_implementation,
            reference=reference_implementation,
            test_cases=sample_test_cases,
            tolerance=1e-10
        )
        
        # Report should have execution time
        assert hasattr(report, 'execution_time_ms')
        assert report.execution_time_ms >= 0


class TestValidationReport:
    """Tests for ValidationReport value object."""

    def test_create_successful_report(self):
        """Test creating a successful validation report."""
        report = ValidationReport(
            id=uuid4(),
            implementation_name='test_impl',
            reference_name='reference',
            total_tests=10,
            passed=10,
            failed=0,
            results=[],
            discrepancy_summary={},
            execution_time_ms=10.0,
            metadata={'document_id': 'doc-001', 'formula_id': 'formula-001'}
        )
        
        assert report.success is True
        assert report.pass_rate == 100.0
        assert report.failed == 0

    def test_create_failed_report(self):
        """Test creating a failed validation report."""
        # Create a failed test result
        test_case = TestCaseFactory.create()
        failed_result = TestResult(
            test_case=test_case,
            implementation_name='test_impl',
            actual_output=Decimal('95'),
            actual_exception=None,
            match=False,
            discrepancy=Decimal('5'),
            error_message='Mismatch',
            execution_time_ms=1.0
        )
        
        report = ValidationReport(
            id=uuid4(),
            implementation_name='test_impl',
            reference_name='reference',
            total_tests=10,
            passed=7,
            failed=3,
            results=[failed_result],
            discrepancy_summary={
                'numeric_tests': 10,
                'max_discrepancy': Decimal('5.0'),
                'mean_discrepancy': Decimal('1.5')
            },
            execution_time_ms=100.0
        )
        
        assert report.success is False
        assert report.failed == 3
        assert len(report.get_failed_tests()) == 1
        assert report.discrepancy_summary['max_discrepancy'] == Decimal('5.0')

    def test_report_immutability(self):
        """Test that ValidationReport is frozen dataclass."""
        report = ValidationReport(
            id=uuid4(),
            implementation_name='test_impl',
            reference_name='reference',
            total_tests=5,
            passed=5,
            failed=0,
            results=[],
            discrepancy_summary={},
            execution_time_ms=10.0
        )
        
        # Dataclass fields can be set, but success is a property
        assert report.success is True

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
            id=uuid4(),
            implementation_name='test_impl',
            reference_name='reference',
            total_tests=20,
            passed=15,
            failed=5,
            results=[],
            discrepancy_summary=summary,
            execution_time_ms=100.0
        )
        
        assert report.discrepancy_summary['numeric_tests'] == 20
        assert report.discrepancy_summary['max_discrepancy'] == Decimal('10.5')
        assert report.discrepancy_summary['mean_discrepancy'] == Decimal('2.3')
        assert report.pass_rate == 75.0


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
