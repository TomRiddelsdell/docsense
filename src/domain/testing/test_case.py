"""
Test case domain models for specification verification.

Provides value objects for representing test cases, categories, and results
that are used throughout the testing and verification framework.
"""

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, Optional, Union
from uuid import UUID, uuid4


class TestCategory(Enum):
    """Categories of test cases based on their purpose."""
    
    NORMAL = "normal"      # Typical values within expected ranges
    BOUNDARY = "boundary"  # Min/max parameter values at edges
    EDGE = "edge"          # Edge cases from specification (precision, calendar)
    ERROR = "error"        # Exception cases that should raise errors


@dataclass(frozen=True)
class TestCase:
    """
    An executable test case with inputs and expected outputs.
    
    Immutable value object representing a single test scenario generated
    from a specification. Used to validate implementation correctness.
    
    Attributes:
        id: Unique identifier for the test case
        name: Human-readable test name (e.g., "calculate_nav_normal_case")
        category: Type of test (normal, boundary, edge, error)
        inputs: Dictionary of parameter names to input values
        expected_output: Expected result value (None if to be computed)
        expected_exception: Expected exception type if test should raise
        precision: Number of decimal places for comparison
        tolerance: Absolute tolerance for floating-point comparison
        description: Human-readable description of what is being tested
        metadata: Additional context (formula_id, document_id, etc.)
    """
    
    id: UUID
    name: str
    category: TestCategory
    inputs: Dict[str, Any]
    expected_output: Optional[Any] = None
    expected_exception: Optional[type] = None
    precision: Optional[int] = None
    tolerance: Optional[float] = None
    description: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate test case invariants."""
        if not self.name:
            raise ValueError("Test case name cannot be empty")
        
        if not self.inputs:
            raise ValueError("Test case must have at least one input")
        
        if self.expected_output is not None and self.expected_exception is not None:
            raise ValueError("Test case cannot have both expected_output and expected_exception")
        
        if self.precision is not None and self.precision < 0:
            raise ValueError("Precision must be non-negative")
        
        if self.tolerance is not None and self.tolerance < 0:
            raise ValueError("Tolerance must be non-negative")
    
    @classmethod
    def create(
        cls,
        name: str,
        category: TestCategory,
        inputs: Dict[str, Any],
        expected_output: Optional[Any] = None,
        expected_exception: Optional[type] = None,
        precision: Optional[int] = None,
        tolerance: Optional[float] = None,
        description: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> "TestCase":
        """Create a new test case with generated ID."""
        return cls(
            id=uuid4(),
            name=name,
            category=category,
            inputs=inputs,
            expected_output=expected_output,
            expected_exception=expected_exception,
            precision=precision,
            tolerance=tolerance,
            description=description,
            metadata=metadata or {},
        )
    
    def with_expected_output(self, output: Any) -> "TestCase":
        """Create a new test case with the expected output set."""
        return TestCase(
            id=self.id,
            name=self.name,
            category=self.category,
            inputs=self.inputs,
            expected_output=output,
            expected_exception=self.expected_exception,
            precision=self.precision,
            tolerance=self.tolerance,
            description=self.description,
            metadata=self.metadata,
        )
    
    def matches_output(self, actual_output: Any) -> bool:
        """
        Check if actual output matches expected output within tolerance.
        
        Args:
            actual_output: The actual output from running the test
            
        Returns:
            True if outputs match within specified precision/tolerance
        """
        if self.expected_output is None:
            return True  # No expected output to compare
        
        # Handle numeric comparisons with precision/tolerance
        if isinstance(self.expected_output, (int, float, Decimal)):
            if not isinstance(actual_output, (int, float, Decimal)):
                return False
            
            expected = float(self.expected_output)
            actual = float(actual_output)
            
            # Use precision if specified (round and compare)
            if self.precision is not None:
                expected_rounded = round(expected, self.precision)
                actual_rounded = round(actual, self.precision)
                return expected_rounded == actual_rounded
            
            # Use tolerance if specified (absolute difference)
            if self.tolerance is not None:
                return abs(expected - actual) <= self.tolerance
            
            # Default: exact equality
            return expected == actual
        
        # Handle date comparisons
        if isinstance(self.expected_output, date) and isinstance(actual_output, date):
            return self.expected_output == actual_output
        
        # Handle string comparisons
        if isinstance(self.expected_output, str) and isinstance(actual_output, str):
            return self.expected_output == actual_output
        
        # Handle collection comparisons
        if isinstance(self.expected_output, (list, tuple)) and isinstance(actual_output, (list, tuple)):
            if len(self.expected_output) != len(actual_output):
                return False
            return all(
                TestCase(
                    id=self.id,
                    name=self.name,
                    category=self.category,
                    inputs={},
                    expected_output=exp,
                    precision=self.precision,
                    tolerance=self.tolerance,
                ).matches_output(act)
                for exp, act in zip(self.expected_output, actual_output)
            )
        
        # Default: exact equality
        return self.expected_output == actual_output


@dataclass
class TestResult:
    """
    Result of running a single test case against an implementation.
    
    Captures the outcome of executing a test case, including actual output,
    whether it matches expectations, and any discrepancies or errors.
    
    Attributes:
        test_case: The test case that was executed
        implementation_name: Name/identifier of the implementation tested
        actual_output: Actual result from running the implementation
        actual_exception: Exception raised (if any)
        match: Whether actual output matches expected output
        discrepancy: Numeric difference (for numeric outputs)
        error_message: Error description if test failed
        execution_time_ms: Time taken to execute (milliseconds)
    """
    
    test_case: TestCase
    implementation_name: str
    actual_output: Optional[Any] = None
    actual_exception: Optional[Exception] = None
    match: bool = False
    discrepancy: Optional[float] = None
    error_message: str = ""
    execution_time_ms: Optional[float] = None
    
    @property
    def passed(self) -> bool:
        """Whether the test passed (matches expected behavior)."""
        # If expected exception, check if correct exception was raised
        if self.test_case.expected_exception is not None:
            if self.actual_exception is None:
                return False
            return isinstance(self.actual_exception, self.test_case.expected_exception)
        
        # If expected output, check if output matches
        if self.test_case.expected_output is not None:
            return self.match
        
        # If no expectations set, test passes if no exception raised
        return self.actual_exception is None
    
    @property
    def failed(self) -> bool:
        """Whether the test failed."""
        return not self.passed
    
    def calculate_discrepancy(self) -> None:
        """Calculate numeric discrepancy between expected and actual output."""
        if self.test_case.expected_output is None or self.actual_output is None:
            self.discrepancy = None
            return
        
        try:
            expected = float(self.test_case.expected_output)
            actual = float(self.actual_output)
            self.discrepancy = abs(expected - actual)
        except (TypeError, ValueError):
            self.discrepancy = None
    
    def __str__(self) -> str:
        """Human-readable test result summary."""
        status = "PASS" if self.passed else "FAIL"
        details = []
        
        if self.actual_exception:
            details.append(f"Exception: {type(self.actual_exception).__name__}")
        elif self.actual_output is not None:
            details.append(f"Output: {self.actual_output}")
        
        if self.discrepancy is not None:
            details.append(f"Discrepancy: {self.discrepancy}")
        
        if self.error_message:
            details.append(f"Error: {self.error_message}")
        
        details_str = ", ".join(details) if details else ""
        return f"[{status}] {self.test_case.name} ({self.implementation_name}){' - ' + details_str if details_str else ''}"
