"""
Cross-validator for comparing implementations against reference and each other.

Validates implementation correctness by running test cases and comparing
outputs against reference implementations or across multiple implementations.
"""

import time
from typing import Any, Callable, Dict, List, Optional, Tuple
from uuid import uuid4

from .test_case import TestCase, TestResult, TestCategory
from .validation_report import ValidationReport, ComparisonReport, ComparisonResult


class CrossValidator:
    """
    Validate implementations against reference and compare multiple implementations.
    
    Runs comprehensive test suites to ensure implementations match specifications
    and are consistent with each other.
    """
    
    def __init__(self, default_tolerance: float = 1e-10):
        """
        Initialize cross validator.
        
        Args:
            default_tolerance: Default tolerance for floating-point comparisons
        """
        self.default_tolerance = default_tolerance
    
    def validate_implementation(
        self,
        implementation: Callable,
        reference: Callable,
        test_cases: List[TestCase],
        implementation_name: str = "implementation",
        reference_name: str = "reference",
        tolerance: Optional[float] = None,
    ) -> ValidationReport:
        """
        Validate an implementation against a reference implementation.
        
        Args:
            implementation: Implementation function to validate
            reference: Reference implementation function
            test_cases: List of test cases to run
            implementation_name: Name for the implementation being tested
            reference_name: Name for the reference implementation
            tolerance: Override default tolerance for comparisons
            
        Returns:
            Validation report with detailed results
        """
        if tolerance is None:
            tolerance = self.default_tolerance
        
        start_time = time.time()
        results = []
        
        for test_case in test_cases:
            result = self._run_single_test(
                implementation=implementation,
                reference=reference,
                test_case=test_case,
                implementation_name=implementation_name,
                tolerance=tolerance,
            )
            results.append(result)
        
        end_time = time.time()
        execution_time_ms = (end_time - start_time) * 1000
        
        # Calculate statistics
        passed = sum(1 for r in results if r.passed)
        failed = sum(1 for r in results if r.failed)
        
        # Generate discrepancy summary
        discrepancy_summary = self._summarize_discrepancies(results)
        
        return ValidationReport(
            id=uuid4(),
            implementation_name=implementation_name,
            reference_name=reference_name,
            total_tests=len(test_cases),
            passed=passed,
            failed=failed,
            results=results,
            discrepancy_summary=discrepancy_summary,
            execution_time_ms=execution_time_ms,
        )
    
    def compare_implementations(
        self,
        implementations: Dict[str, Callable],
        test_cases: List[TestCase],
        tolerance: Optional[float] = None,
    ) -> ComparisonReport:
        """
        Compare multiple implementations against each other.
        
        Useful for ensuring consistency across different implementations
        of the same specification (e.g., backtesting vs production).
        
        Args:
            implementations: Dictionary mapping names to implementation functions
            test_cases: List of test cases to run
            tolerance: Override default tolerance for comparisons
            
        Returns:
            Comparison report showing consistency across implementations
        """
        if tolerance is None:
            tolerance = self.default_tolerance
        
        if len(implementations) < 2:
            raise ValueError("Need at least 2 implementations to compare")
        
        results = []
        
        for test_case in test_cases:
            result = self._compare_single_test(
                implementations=implementations,
                test_case=test_case,
                tolerance=tolerance,
            )
            results.append(result)
        
        # Calculate statistics
        consistent = sum(1 for r in results if r.consistent)
        inconsistent = sum(1 for r in results if not r.consistent)
        
        # Generate inconsistency summary
        inconsistency_summary = self._summarize_inconsistencies(results)
        
        return ComparisonReport(
            id=uuid4(),
            implementations=list(implementations.keys()),
            total_tests=len(test_cases),
            consistent_tests=consistent,
            inconsistent_tests=inconsistent,
            results=results,
            inconsistency_summary=inconsistency_summary,
        )
    
    def _run_single_test(
        self,
        implementation: Callable,
        reference: Callable,
        test_case: TestCase,
        implementation_name: str,
        tolerance: float,
    ) -> TestResult:
        """Run a single test case and compare results."""
        # Run reference implementation
        ref_output = None
        ref_exception = None
        try:
            ref_output = reference(**test_case.inputs)
        except Exception as e:
            ref_exception = e
        
        # Run implementation under test
        impl_output = None
        impl_exception = None
        impl_start = time.time()
        try:
            impl_output = implementation(**test_case.inputs)
        except Exception as e:
            impl_exception = e
        impl_end = time.time()
        execution_time_ms = (impl_end - impl_start) * 1000
        
        # Compare results
        match, discrepancy, error_msg = self._compare_outputs(
            expected=ref_output,
            actual=impl_output,
            expected_exception=ref_exception,
            actual_exception=impl_exception,
            test_case=test_case,
            tolerance=tolerance,
        )
        
        result = TestResult(
            test_case=test_case,
            implementation_name=implementation_name,
            actual_output=impl_output,
            actual_exception=impl_exception,
            match=match,
            discrepancy=discrepancy,
            error_message=error_msg,
            execution_time_ms=execution_time_ms,
        )
        
        # Calculate discrepancy if numeric
        result.calculate_discrepancy()
        
        return result
    
    def _compare_single_test(
        self,
        implementations: Dict[str, Callable],
        test_case: TestCase,
        tolerance: float,
    ) -> ComparisonResult:
        """Run a single test across all implementations and compare."""
        outputs = {}
        exceptions = {}
        
        # Run test on each implementation
        for name, impl in implementations.items():
            try:
                outputs[name] = impl(**test_case.inputs)
            except Exception as e:
                exceptions[name] = e
                outputs[name] = f"ERROR: {type(e).__name__}"
        
        # Check consistency
        consistent, max_discrepancy, error_msg = self._check_consistency(
            outputs=outputs,
            exceptions=exceptions,
            tolerance=tolerance,
        )
        
        return ComparisonResult(
            test_case_name=test_case.name,
            outputs=outputs,
            consistent=consistent,
            max_discrepancy=max_discrepancy,
            error_message=error_msg,
        )
    
    def _compare_outputs(
        self,
        expected: Any,
        actual: Any,
        expected_exception: Optional[Exception],
        actual_exception: Optional[Exception],
        test_case: TestCase,
        tolerance: float,
    ) -> Tuple[bool, Optional[float], str]:
        """
        Compare expected and actual outputs.
        
        Returns:
            Tuple of (match, discrepancy, error_message)
        """
        # Handle exception cases
        if expected_exception is not None:
            if actual_exception is None:
                return False, None, f"Expected exception {type(expected_exception).__name__} but got output {actual}"
            if type(expected_exception) != type(actual_exception):
                return False, None, f"Expected {type(expected_exception).__name__} but got {type(actual_exception).__name__}"
            return True, None, ""
        
        if actual_exception is not None:
            return False, None, f"Unexpected exception: {type(actual_exception).__name__}: {actual_exception}"
        
        # Handle numeric comparisons
        if isinstance(expected, (int, float)) and isinstance(actual, (int, float)):
            expected_float = float(expected)
            actual_float = float(actual)
            discrepancy = abs(expected_float - actual_float)
            
            # Use test case tolerance if specified, otherwise use default
            test_tolerance = test_case.tolerance if test_case.tolerance is not None else tolerance
            
            # Use precision if specified
            if test_case.precision is not None:
                expected_rounded = round(expected_float, test_case.precision)
                actual_rounded = round(actual_float, test_case.precision)
                match = expected_rounded == actual_rounded
            else:
                match = discrepancy <= test_tolerance
            
            if not match:
                error_msg = f"Expected {expected_float}, got {actual_float} (discrepancy: {discrepancy})"
            else:
                error_msg = ""
            
            return match, discrepancy, error_msg
        
        # Handle exact equality for non-numeric types
        match = expected == actual
        error_msg = "" if match else f"Expected {expected}, got {actual}"
        return match, None, error_msg
    
    def _check_consistency(
        self,
        outputs: Dict[str, Any],
        exceptions: Dict[str, Exception],
        tolerance: float,
    ) -> Tuple[bool, Optional[float], str]:
        """
        Check if all implementations produced consistent outputs.
        
        Returns:
            Tuple of (consistent, max_discrepancy, error_message)
        """
        if not outputs:
            return False, None, "No outputs to compare"
        
        # If any implementation raised an exception, check consistency of exceptions
        if exceptions:
            exception_types = {type(e).__name__ for e in exceptions.values()}
            if len(exception_types) > 1:
                return False, None, f"Inconsistent exceptions: {exception_types}"
            # All implementations that ran raised the same exception type
            if len(exceptions) != len(outputs):
                return False, None, "Some implementations raised exceptions, others did not"
            return True, None, ""
        
        # Get all output values
        values = list(outputs.values())
        
        # Check if all are numeric
        if all(isinstance(v, (int, float)) for v in values):
            floats = [float(v) for v in values]
            min_val = min(floats)
            max_val = max(floats)
            max_discrepancy = max_val - min_val
            
            consistent = max_discrepancy <= tolerance
            error_msg = "" if consistent else f"Max discrepancy {max_discrepancy} exceeds tolerance {tolerance}"
            
            return consistent, max_discrepancy, error_msg
        
        # For non-numeric, check exact equality
        first_value = values[0]
        consistent = all(v == first_value for v in values)
        error_msg = "" if consistent else f"Inconsistent outputs: {outputs}"
        
        return consistent, None, error_msg
    
    def _summarize_discrepancies(self, results: List[TestResult]) -> Dict[str, Any]:
        """Generate statistical summary of discrepancies."""
        numeric_results = [r for r in results if r.discrepancy is not None]
        
        if not numeric_results:
            return {
                "numeric_tests": 0,
                "max_discrepancy": None,
                "mean_discrepancy": None,
                "median_discrepancy": None,
            }
        
        discrepancies = [r.discrepancy for r in numeric_results]
        discrepancies_sorted = sorted(discrepancies)
        
        return {
            "numeric_tests": len(numeric_results),
            "max_discrepancy": max(discrepancies),
            "mean_discrepancy": sum(discrepancies) / len(discrepancies),
            "median_discrepancy": discrepancies_sorted[len(discrepancies_sorted) // 2],
            "tests_with_discrepancy": sum(1 for d in discrepancies if d > 0),
        }
    
    def _summarize_inconsistencies(self, results: List[ComparisonResult]) -> Dict[str, Any]:
        """Generate summary of inconsistencies across implementations."""
        inconsistent_tests = [r for r in results if not r.consistent]
        
        numeric_inconsistencies = [
            r for r in inconsistent_tests if r.max_discrepancy is not None
        ]
        
        summary = {
            "total_inconsistent": len(inconsistent_tests),
            "numeric_inconsistencies": len(numeric_inconsistencies),
            "non_numeric_inconsistencies": len(inconsistent_tests) - len(numeric_inconsistencies),
        }
        
        if numeric_inconsistencies:
            max_discreps = [r.max_discrepancy for r in numeric_inconsistencies]
            summary["max_discrepancy"] = max(max_discreps)
            summary["mean_discrepancy"] = sum(max_discreps) / len(max_discreps)
        
        return summary
