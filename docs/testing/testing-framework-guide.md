# Testing Framework Guide

**Version**: 1.0  
**Phase**: 14 - Implementation Testing and Verification Framework  
**Related**: [ADR-019](../decisions/019-implementation-testing-verification.md)

## Overview

The Testing Framework provides automated generation of test cases, reference implementations, and cross-validation to ensure implementations match specifications precisely.

## Core Components

### 1. TestCaseGenerator

Generates comprehensive test suites from semantic IR specifications.

```python
from src.domain.testing import TestCaseGenerator, TestCategory

# Initialize generator
generator = TestCaseGenerator()

# Generate test cases for a formula
test_cases = generator.generate_from_formula(
    formula=formula,
    document_ir=document_ir,
    count_per_category={
        TestCategory.NORMAL: 10,     # 10 normal tests
        TestCategory.BOUNDARY: 4,     # 4 boundary tests
        TestCategory.EDGE: 3,         # 3 edge tests
        TestCategory.ERROR: 2,        # 2 error tests
    }
)

# Generate for entire document
test_suites = generator.generate_from_document(document_ir)
```

**Test Categories**:
- **NORMAL**: Typical values within expected ranges
- **BOUNDARY**: Min/max values at parameter edges
- **EDGE**: Special cases (zero values, year-end dates, leap years, large numbers)
- **ERROR**: Invalid inputs that should raise exceptions

### 2. ReferenceImplementation

Generates executable Python code from specifications.

```python
from src.domain.testing import ReferenceImplementation

# Initialize generator
ref_gen = ReferenceImplementation()

# Generate reference function
reference_func = ref_gen.generate_reference(
    formula=formula,
    document_ir=document_ir,
    precision=4,  # Round to 4 decimal places
    include_validation=True,  # Include parameter validation
)

# Get code as string
code = ref_gen.generate_function_code(
    formula=formula,
    document_ir=document_ir,
)

print(code)
```

**Generated Code Includes**:
- Type-annotated function signature
- Comprehensive docstring with formula LaTeX
- Parameter validation (range checks, positive values)
- Formula implementation (LaTeX → Python)
- Precision handling (Decimal arithmetic with rounding)

### 3. CrossValidator

Validates implementations against reference.

```python
from src.domain.testing import CrossValidator

# Initialize validator
validator = CrossValidator(default_tolerance=1e-10)

# Validate single implementation
report = validator.validate_implementation(
    implementation=user_function,
    reference=reference_function,
    test_cases=test_cases,
    implementation_name="my_implementation",
)

print(f"Pass Rate: {report.pass_rate:.1f}%")
print(f"Passed: {report.passed}/{report.total_tests}")

# Show failed tests
for result in report.get_failed_tests():
    print(f"FAILED: {result.test_case.name}")
    print(f"  Expected: {result.test_case.expected_output}")
    print(f"  Actual: {result.actual_output}")
    print(f"  Discrepancy: {result.discrepancy}")

# Compare multiple implementations
comparison = validator.compare_implementations(
    implementations={
        "backtesting": backtesting_impl,
        "production": production_impl,
        "reference": reference_impl,
    },
    test_cases=test_cases,
)

print(f"Consistency Rate: {comparison.consistency_rate:.1f}%")
```

## API Usage

### Generate Test Cases

```bash
POST /api/v1/testing/test-cases
Content-Type: application/json

{
  "document_id": "uuid-here",
  "formula_ids": ["formula-1", "formula-2"],  # Optional
  "count_per_category": {
    "normal": 10,
    "boundary": 5,
    "edge": 3,
    "error": 2
  }
}
```

**Response**:
```json
[
  {
    "document_id": "uuid-here",
    "formula_id": "formula-1",
    "total_tests": 20,
    "test_cases": [
      {
        "id": "test-uuid",
        "name": "calculate_nav_normal_0",
        "category": "normal",
        "inputs": {
          "total_assets": 1000000.0,
          "total_liabilities": 50000.0,
          "shares_outstanding": 10000
        },
        "expected_output": 95.0,
        "precision": 4,
        "tolerance": 0.0001,
        "description": "Normal case with typical values"
      }
    ]
  }
]
```

### Generate Reference Implementation

```bash
POST /api/v1/testing/reference
Content-Type: application/json

{
  "document_id": "uuid-here",
  "formula_id": "nav_calculation",
  "precision": 4,
  "include_validation": true
}
```

**Response**:
```json
{
  "document_id": "uuid-here",
  "formula_id": "nav_calculation",
  "function_name": "calculate_nav",
  "code": "from decimal import Decimal, ROUND_HALF_UP\n\ndef calculate_nav(total_assets: float, total_liabilities: float, shares_outstanding: int) -> float:\n    \"\"\"Calculate NAV...\"\"\"\n    ..."
}
```

### Validate Implementation

```bash
POST /api/v1/testing/validate
Content-Type: application/json

{
  "document_id": "uuid-here",
  "formula_id": "nav_calculation",
  "implementation_code": "def calculate_nav(total_assets, total_liabilities, shares_outstanding):\n    return (total_assets - total_liabilities) / shares_outstanding",
  "tolerance": 1e-10
}
```

**Response**:
```json
{
  "report_id": "report-uuid",
  "document_id": "uuid-here",
  "formula_id": "nav_calculation",
  "success": false,
  "pass_rate": 85.0,
  "total_tests": 20,
  "passed": 17,
  "failed": 3,
  "discrepancy_summary": {
    "numeric_tests": 17,
    "max_discrepancy": 0.0001,
    "mean_discrepancy": 0.00003,
    "median_discrepancy": 0.00002
  },
  "failed_tests": [
    {
      "test_name": "calculate_nav_boundary_total_assets_min",
      "category": "boundary",
      "expected": 0.0,
      "actual": -0.0001,
      "discrepancy": 0.0001,
      "error": "Expected 0.0, got -0.0001 (discrepancy: 0.0001)"
    }
  ]
}
```

## CI/CD Integration

The testing framework includes a GitHub Actions workflow that runs on every commit.

### Workflow: `.github/workflows/specification-validation.yml`

1. **Generate test cases** from all document specifications
2. **Generate reference implementations** for all formulas
3. **Run validation** comparing implementations against references
4. **Upload artifacts** (test cases, references, validation report)
5. **Comment on PR** with validation results
6. **Block merge** if validation fails

### Running Locally

```bash
# Generate test cases
python scripts/run_validation.py generate-tests \
  --output tests/generated/ \
  --documents doc-uuid-1 doc-uuid-2 \
  --verbose

# Generate reference implementations
python scripts/run_validation.py generate-references \
  --output tests/reference/ \
  --documents doc-uuid-1 doc-uuid-2 \
  --verbose

# Run validation
python scripts/run_validation.py validate \
  --test-dir tests/generated/ \
  --reference-dir tests/reference/ \
  --report validation-report.json \
  --threshold 100 \
  --verbose

# Check results
python scripts/check_validation.py \
  --report validation-report.json \
  --threshold 100 \
  --fail-on-error
```

## Best Practices

### 1. Test Case Generation

- Generate at least 50 test cases per formula (mix of categories)
- Include calendar edge cases (year-end, holidays, leap years)
- Cover full parameter ranges (min, typical, max values)
- Test exception handling (negative values, out-of-range)

### 2. Reference Implementations

- Use exact precision specification (Decimal arithmetic)
- Include comprehensive parameter validation
- Handle all edge cases from specification
- Document assumptions clearly in docstrings

### 3. Validation

- Use appropriate tolerance based on precision requirements
- Review failed tests carefully (may indicate spec issues)
- Compare multiple implementations for consistency
- Run validation before each release

### 4. CI/CD

- Require 100% pass rate for merges to main branch
- Allow 95%+ pass rate for development branches
- Review validation reports in PRs
- Investigate discrepancies immediately

## Troubleshooting

### Issue: "Failed to generate reference implementation"

**Cause**: LaTeX formula cannot be parsed

**Solution**: 
- Check formula syntax in specification
- Ensure all variables are defined
- Simplify complex LaTeX expressions
- Add custom conversion rules if needed

### Issue: "Validation failing with small discrepancies"

**Cause**: Floating-point precision issues

**Solution**:
- Increase tolerance: `tolerance=1e-8` instead of `1e-10`
- Specify precision: `precision=4` for 4 decimal places
- Use Decimal arithmetic in implementation
- Check rounding mode (ROUND_HALF_UP vs ROUND_HALF_EVEN)

### Issue: "Test cases not covering edge case"

**Cause**: Edge case not captured in specification

**Solution**:
- Add edge case to specification explicitly
- Use TestCase.create() to add manual test cases
- Document edge case in formula definition
- Regenerate tests after specification update

## Examples

### Example 1: Simple Formula Validation

```python
from src.domain.testing import TestCaseGenerator, ReferenceImplementation, CrossValidator

# 1. Generate test cases
generator = TestCaseGenerator()
test_cases = generator.generate_from_formula(nav_formula, document_ir)
print(f"Generated {len(test_cases)} test cases")

# 2. Generate reference
ref_gen = ReferenceImplementation()
reference = ref_gen.generate_reference(nav_formula, document_ir, precision=4)

# 3. User implementation
def my_nav_calc(total_assets, total_liabilities, shares_outstanding):
    return round((total_assets - total_liabilities) / shares_outstanding, 4)

# 4. Validate
validator = CrossValidator()
report = validator.validate_implementation(
    implementation=my_nav_calc,
    reference=reference,
    test_cases=test_cases,
)

# 5. Review results
print(report)
if not report.success:
    for failed in report.get_failed_tests():
        print(f"FAILED: {failed}")
```

### Example 2: Multi-Implementation Comparison

```python
# Compare backtesting, production, and reference
comparison = validator.compare_implementations(
    implementations={
        "backtesting": backtesting_nav,
        "production": production_nav,
        "reference": reference_nav,
    },
    test_cases=test_cases,
    tolerance=1e-10,
)

print(f"Consistency: {comparison.consistency_rate:.1f}%")

# Find inconsistencies
for result in comparison.results:
    if not result.consistent:
        print(f"\nInconsistent test: {result.test_case_name}")
        print(result.get_output_summary())
        print(f"Max discrepancy: {result.max_discrepancy}")
```

## Future Enhancements

- [ ] Frontend validation dashboard
- [ ] Real-time validation in document editor
- [ ] Test case versioning and history
- [ ] Performance benchmarking in validation
- [ ] Automated test case prioritization
- [ ] Machine learning for edge case detection

## Support

For issues or questions:
- Review [ADR-019](../decisions/019-implementation-testing-verification.md)
- Check API documentation: `/api/v1/docs`
- Run validation locally with `--verbose` flag
- Examine validation report JSON for details
