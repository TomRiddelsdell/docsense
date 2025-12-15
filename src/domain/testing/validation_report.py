"""
Validation report data structures for cross-implementation comparison results.

Provides value objects for capturing and summarizing validation outcomes
when comparing implementations against reference or each other.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from .test_case import TestResult


@dataclass
class ValidationReport:
    """
    Results of validating an implementation against reference or another implementation.
    
    Captures comprehensive validation outcomes including test results,
    discrepancy analysis, and performance metrics.
    
    Attributes:
        id: Unique identifier for this validation run
        implementation_name: Name/identifier of implementation tested
        reference_name: Name of reference implementation
        total_tests: Total number of test cases executed
        passed: Number of tests that passed
        failed: Number of tests that failed
        results: Detailed results for each test case
        discrepancy_summary: Statistical summary of discrepancies
        execution_time_ms: Total execution time in milliseconds
        timestamp: When the validation was performed
        metadata: Additional context (document_id, formula_id, etc.)
    """
    
    id: UUID
    implementation_name: str
    reference_name: str
    total_tests: int
    passed: int
    failed: int
    results: List[TestResult]
    discrepancy_summary: Dict[str, Any]
    execution_time_ms: Optional[float] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def pass_rate(self) -> float:
        """Calculate pass rate as percentage."""
        if self.total_tests == 0:
            return 0.0
        return (self.passed / self.total_tests) * 100.0
    
    @property
    def success(self) -> bool:
        """Whether validation was successful (all tests passed)."""
        return self.passed == self.total_tests
    
    def get_failed_tests(self) -> List[TestResult]:
        """Get list of failed test results."""
        return [r for r in self.results if r.failed]
    
    def get_passed_tests(self) -> List[TestResult]:
        """Get list of passed test results."""
        return [r for r in self.results if r.passed]
    
    def get_largest_discrepancies(self, limit: int = 10) -> List[TestResult]:
        """
        Get test results with largest numeric discrepancies.
        
        Args:
            limit: Maximum number of results to return
            
        Returns:
            List of test results sorted by discrepancy (largest first)
        """
        results_with_discrepancy = [
            r for r in self.results if r.discrepancy is not None
        ]
        results_with_discrepancy.sort(key=lambda r: r.discrepancy, reverse=True)
        return results_with_discrepancy[:limit]
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Serialize to dictionary.
        
        Returns:
            Dictionary representation
        """
        return {
            "id": str(self.id),
            "implementation_name": self.implementation_name,
            "reference_name": self.reference_name,
            "total_tests": self.total_tests,
            "passed": self.passed,
            "failed": self.failed,
            "pass_rate": self.pass_rate,
            "success": self.success,
            "discrepancy_summary": self.discrepancy_summary,
            "execution_time_ms": self.execution_time_ms,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
            "failed_tests": [
                {
                    "test_name": r.test_case.name,
                    "expected": r.test_case.expected_output,
                    "actual": r.actual_output,
                    "discrepancy": r.discrepancy,
                    "error": r.error_message,
                }
                for r in self.get_failed_tests()
            ],
        }
    
    def __str__(self) -> str:
        """Human-readable summary."""
        lines = []
        lines.append(f"Validation Report: {self.implementation_name} vs {self.reference_name}")
        lines.append(f"Status: {'SUCCESS' if self.success else 'FAILED'}")
        lines.append(f"Pass Rate: {self.pass_rate:.1f}% ({self.passed}/{self.total_tests})")
        
        if self.execution_time_ms:
            lines.append(f"Execution Time: {self.execution_time_ms:.2f}ms")
        
        if self.discrepancy_summary:
            lines.append("\nDiscrepancy Summary:")
            for key, value in self.discrepancy_summary.items():
                lines.append(f"  {key}: {value}")
        
        if self.failed > 0:
            lines.append(f"\nFailed Tests: {self.failed}")
            for result in self.get_failed_tests()[:5]:  # Show first 5
                lines.append(f"  - {result.test_case.name}: {result.error_message}")
        
        return "\n".join(lines)


@dataclass
class ComparisonReport:
    """
    Results of comparing multiple implementations against each other.
    
    Used when validating consistency across multiple implementations
    of the same specification (e.g., backtesting vs production).
    
    Attributes:
        id: Unique identifier for this comparison
        implementations: Names of implementations compared
        total_tests: Total number of test cases executed
        consistent_tests: Number of tests where all implementations agreed
        inconsistent_tests: Number of tests with discrepancies
        results: Detailed results for each test case
        inconsistency_summary: Summary of where implementations differ
        timestamp: When the comparison was performed
        metadata: Additional context
    """
    
    id: UUID
    implementations: List[str]
    total_tests: int
    consistent_tests: int
    inconsistent_tests: int
    results: List["ComparisonResult"]
    inconsistency_summary: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def consistency_rate(self) -> float:
        """Calculate consistency rate as percentage."""
        if self.total_tests == 0:
            return 0.0
        return (self.consistent_tests / self.total_tests) * 100.0
    
    @property
    def all_consistent(self) -> bool:
        """Whether all implementations are consistent."""
        return self.consistent_tests == self.total_tests
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "id": str(self.id),
            "implementations": self.implementations,
            "total_tests": self.total_tests,
            "consistent_tests": self.consistent_tests,
            "inconsistent_tests": self.inconsistent_tests,
            "consistency_rate": self.consistency_rate,
            "all_consistent": self.all_consistent,
            "inconsistency_summary": self.inconsistency_summary,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }


@dataclass
class ComparisonResult:
    """
    Result of running a single test case across multiple implementations.
    
    Attributes:
        test_case_name: Name of the test case
        outputs: Dictionary mapping implementation names to outputs
        consistent: Whether all outputs are consistent
        max_discrepancy: Maximum numeric discrepancy between implementations
        error_message: Description if test failed
    """
    
    test_case_name: str
    outputs: Dict[str, Any]
    consistent: bool
    max_discrepancy: Optional[float] = None
    error_message: str = ""
    
    def get_output_summary(self) -> str:
        """Get summary of outputs from all implementations."""
        lines = []
        for impl_name, output in self.outputs.items():
            lines.append(f"  {impl_name}: {output}")
        return "\n".join(lines)
