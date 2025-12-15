"""Test data factories for Phase 14 testing framework."""

from decimal import Decimal
from uuid import uuid4
from typing import Dict, List, Any, Optional
from datetime import date, timedelta

from src.domain.testing.test_case import TestCase, TestCategory, TestResult
from src.domain.testing.validation_report import ValidationReport


class TestCaseFactory:
    """Factory for creating TestCase fixtures."""
    
    @staticmethod
    def create(
        id: Optional[str] = None,
        name: str = "test_case",
        category: TestCategory = TestCategory.NORMAL,
        inputs: Optional[Dict[str, Any]] = None,
        expected_output: Any = Decimal("20"),
        tolerance: Optional[Decimal] = None,
        precision: int = 10,
        description: str = "Test case",
        **kwargs
    ) -> TestCase:
        """Create a single test case."""
        return TestCase(
            id=id or str(uuid4()),
            name=name,
            category=category,
            inputs=inputs or {"x": Decimal("10")},
            expected_output=expected_output,
            tolerance=tolerance,
            precision=precision,
            description=description,
            **kwargs
        )
    
    @staticmethod
    def create_batch(count: int = 5, **kwargs) -> List[TestCase]:
        """Create a batch of test cases."""
        return [TestCaseFactory.create(**kwargs) for _ in range(count)]
    
    @staticmethod
    def create_simple_interest_tests() -> List[TestCase]:
        """Create test cases for simple interest formula: I = P * r * t"""
        return [
            TestCase(
                id=str(uuid4()),
                name="Normal case - moderate values",
                category=TestCategory.NORMAL,
                inputs={
                    'P': Decimal('1000'),
                    'r': Decimal('0.05'),
                    't': Decimal('2')
                },
                expected_output=Decimal('100'),
                tolerance=Decimal('1e-10'),
                precision=10,
                description='Calculate interest with moderate values'
            ),
            TestCase(
                id=str(uuid4()),
                name="Boundary case - zero principal",
                category=TestCategory.BOUNDARY,
                inputs={
                    'P': Decimal('0'),
                    'r': Decimal('0.05'),
                    't': Decimal('2')
                },
                expected_output=Decimal('0'),
                tolerance=Decimal('1e-10'),
                precision=10,
                description='Zero principal should return zero interest'
            ),
            TestCase(
                id=str(uuid4()),
                name="Edge case - large values",
                category=TestCategory.EDGE,
                inputs={
                    'P': Decimal('1000000'),
                    'r': Decimal('0.99'),
                    't': Decimal('30')
                },
                expected_output=Decimal('29700000'),
                tolerance=Decimal('1e-10'),
                precision=10,
                description='Large values test'
            ),
        ]


class TestResultFactory:
    """Factory for creating TestResult fixtures."""
    
    @staticmethod
    def create(
        test_case: Optional[TestCase] = None,
        implementation_name: str = "implementation",
        actual_output: Any = Decimal("20"),
        actual_exception: Optional[Exception] = None,
        match: bool = True,
        discrepancy: Optional[Decimal] = None,
        error_message: str = "",
        execution_time_ms: float = 1.0,
        **kwargs
    ) -> TestResult:
        """Create a single test result."""
        if test_case is None:
            test_case = TestCaseFactory.create()
        
        return TestResult(
            test_case=test_case,
            implementation_name=implementation_name,
            actual_output=actual_output,
            actual_exception=actual_exception,
            match=match,
            discrepancy=discrepancy,
            error_message=error_message,
            execution_time_ms=execution_time_ms,
            **kwargs
        )


class ValidationReportFactory:
    """Factory for creating ValidationReport fixtures."""
    
    @staticmethod
    def create(
        id: Optional[Any] = None,
        implementation_name: str = "implementation",
        reference_name: str = "reference",
        total_tests: int = 10,
        passed: int = 8,
        failed: Optional[int] = None,
        results: Optional[List[TestResult]] = None,
        discrepancy_summary: Optional[Dict[str, Any]] = None,
        execution_time_ms: float = 10.0,
        **kwargs
    ) -> ValidationReport:
        """Create a validation report."""
        if failed is None:
            failed = total_tests - passed
        
        if results is None:
            results = []
        
        if discrepancy_summary is None:
            discrepancy_summary = {}
        
        return ValidationReport(
            id=id or uuid4(),
            implementation_name=implementation_name,
            reference_name=reference_name,
            total_tests=total_tests,
            passed=passed,
            failed=failed,
            results=results,
            discrepancy_summary=discrepancy_summary,
            execution_time_ms=execution_time_ms,
            **kwargs
        )


class FunctionFactory:
    """Factory for creating test functions."""
    
    @staticmethod
    def simple_interest_reference():
        """Reference implementation of simple interest formula."""
        def calculate_simple_interest(P: Decimal, r: Decimal, t: Decimal) -> Decimal:
            """Calculate simple interest: I = P * r * t"""
            return P * r * t
        return calculate_simple_interest
    
    @staticmethod
    def simple_interest_implementation_correct():
        """Correct implementation of simple interest."""
        def calculate_simple_interest(P, r, t):
            """Calculate simple interest."""
            return P * r * t
        return calculate_simple_interest
    
    @staticmethod
    def simple_interest_implementation_wrong():
        """Incorrect implementation (uses division instead of multiplication)."""
        def calculate_simple_interest(P, r, t):
            """Calculate simple interest - WRONG FORMULA."""
            return P / r / t if r != 0 and t != 0 else Decimal('0')
        return calculate_simple_interest
    
    @staticmethod
    def simple_interest_implementation_error():
        """Implementation that raises errors."""
        def calculate_simple_interest(P, r, t):
            """Calculate simple interest - raises error."""
            raise ValueError("Test error")
        return calculate_simple_interest
    
    @staticmethod
    def multiply_by_two():
        """Simple function that multiplies by 2."""
        def calc(x):
            return x * 2
        return calc
    
    @staticmethod
    def square():
        """Simple function that squares input."""
        def calc(x):
            return x * x
        return calc
