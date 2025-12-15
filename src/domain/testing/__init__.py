"""
Testing domain package for specification verification.

This package provides:
- Test case generation from specifications
- Reference implementation generation
- Cross-validation between implementations
"""

from .test_case import TestCase, TestCategory, TestResult
from .test_generator import TestCaseGenerator
from .reference_impl import ReferenceImplementation
from .cross_validator import CrossValidator
from .validation_report import ValidationReport, ComparisonReport, ComparisonResult

__all__ = [
    "TestCase",
    "TestCategory",
    "TestResult",
    "TestCaseGenerator",
    "ReferenceImplementation",
    "CrossValidator",
    "ValidationReport",
    "ComparisonReport",
    "ComparisonResult",
]
