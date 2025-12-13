# ADR-019: Implementation Testing and Verification Framework

**Status**: Accepted  
**Date**: 2024-12-08  
**Related**: [ADR-017](017-implementation-precision-specification.md), [ADR-018](018-market-calendar-validation.md)

## Context

Even with complete precision specifications (ADR-017) and calendar validation (ADR-018), we need a mechanism to verify that implementations actually match the specifications. Current challenges:

### 1. Specification-Implementation Gap
Developers may:
- Misinterpret specifications despite clarity
- Make implementation shortcuts that violate specifications
- Introduce bugs that cause deviations
- Use different libraries with subtle behavioral differences

### 2. Silent Calculation Errors
Without verification:
- Different implementations produce different results
- Errors may be small enough to go unnoticed initially
- Compounding errors grow over time
- Root cause is difficult to trace after the fact

### 3. Testing Inadequacy
Traditional unit tests:
- Test code structure, not specification conformance
- May not cover edge cases from specifications
- Don't validate against reference implementations
- Don't ensure cross-implementation consistency

### 4. Multi-Implementation Scenarios
Multiple implementations of the same specification (e.g., backtesting engine, production engine, validation engine) must produce identical results, but without verification framework:
- No automated comparison mechanism
- Manual validation is time-consuming and error-prone
- Discrepancies discovered late in development cycle

## Decision

We will implement a **Testing and Verification Framework** that:
1. Generates executable test cases from specifications
2. Provides reference implementations for validation
3. Enables cross-validation between implementations
4. Detects and reports specification-implementation discrepancies

### 1. Test Case Generation from Specifications

Automatically generate test cases from specification documents:

```python
# In domain/testing/test_generator.py

class TestCaseGenerator:
    """Generate executable test cases from semantic specifications"""
    
    def generate_from_formula(
        self,
        formula: FormulaNode,
        semantic_ir: SemanticIR
    ) -> List[TestCase]:
        """
        Generate test cases covering:
        - Normal cases with typical values
        - Boundary cases at parameter limits
        - Edge cases from precision specification
        - Error cases from exception specifications
        """
        test_cases = []
        
        # Extract parameters and their specifications
        params = self._extract_parameters(formula, semantic_ir)
        
        # Normal case: typical values
        test_cases.append(TestCase(
            name=f"{formula.name}_normal_case",
            category="normal",
            inputs=self._generate_typical_values(params),
            expected_output=None,  # To be computed by reference impl
            description="Typical parameter values"
        ))
        
        # Boundary cases: min/max of each parameter
        for param in params:
            if param.has_range:
                test_cases.append(TestCase(
                    name=f"{formula.name}_boundary_{param.name}_min",
                    category="boundary",
                    inputs={**self._generate_typical_values(params), param.name: param.min},
                    expected_output=None,
                    description=f"{param.name} at minimum value"
                ))
                test_cases.append(TestCase(
                    name=f"{formula.name}_boundary_{param.name}_max",
                    category="boundary",
                    inputs={**self._generate_typical_values(params), param.name: param.max},
                    expected_output=None,
                    description=f"{param.name} at maximum value"
                ))
        
        # Edge cases from precision specifications
        for edge_case in formula.edge_cases:
            test_cases.append(TestCase(
                name=f"{formula.name}_edge_{edge_case.name}",
                category="edge",
                inputs=self._generate_edge_case_inputs(edge_case),
                expected_output=edge_case.expected_behavior,
                description=edge_case.description
            ))
        
        return test_cases

@dataclass
class TestCase:
    """Executable test case with expected results"""
    name: str
    category: str  # normal, boundary, edge, error
    inputs: Dict[str, Any]
    expected_output: Optional[Any]
    precision: Optional[int] = None  # decimal places for comparison
    tolerance: Optional[float] = None  # absolute tolerance for floating point
    description: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
```

### 2. Reference Implementation

Generate Python reference implementations directly from specifications:

```python
# In domain/testing/reference_impl.py

class ReferenceImplementation:
    """Reference implementation generator from semantic specifications"""
    
    def generate_reference(
        self,
        formula: FormulaNode,
        semantic_ir: SemanticIR,
        calendar: Optional[MarketCalendar] = None
    ) -> Callable:
        """
        Generate Python reference implementation with:
        - Exact precision handling from specification
        - Complete edge case handling
        - Proper rounding rules
        - Calendar-aware date operations
        """
        # Generate function signature
        params = self._extract_parameters(formula, semantic_ir)
        
        # Generate function body
        code = self._generate_implementation_code(
            formula=formula,
            params=params,
            precision=formula.precision_spec,
            edge_cases=formula.edge_cases,
            calendar=calendar
        )
        
        # Create executable function
        namespace = self._create_namespace(calendar)
        exec(code, namespace)
        return namespace[formula.name]
    
    def _generate_implementation_code(
        self,
        formula: FormulaNode,
        params: List[Parameter],
        precision: PrecisionSpec,
        edge_cases: List[EdgeCase],
        calendar: Optional[MarketCalendar]
    ) -> str:
        """Generate Python code with exact specification semantics"""
        code_lines = []
        
        # Function signature
        param_sig = ", ".join(f"{p.name}: {p.type_annotation}" for p in params)
        return_type = formula.return_type or "float"
        code_lines.append(f"def {formula.name}({param_sig}) -> {return_type}:")
        code_lines.append(f'    """Reference implementation of {formula.name}')
        code_lines.append(f'    ')
        code_lines.append(f'    Generated from specification.')
        code_lines.append(f'    Precision: {precision.decimal_places} decimal places, {precision.rounding_rule}')
        code_lines.append(f'    """')
        
        # Parameter validation
        for param in params:
            if param.has_range:
                code_lines.append(f"    if not ({param.min} <= {param.name} <= {param.max}):")
                code_lines.append(f"        raise ValueError(f'{param.name}={{{param.name}}} out of range [{param.min}, {param.max}]')")
        
        # Edge case handling
        for edge_case in edge_cases:
            condition = self._generate_condition(edge_case.condition)
            behavior = self._generate_behavior(edge_case.behavior)
            code_lines.append(f"    if {condition}:")
            code_lines.append(f"        {behavior}")
        
        # Main calculation
        calculation = self._generate_calculation(formula, calendar)
        code_lines.append(f"    result = {calculation}")
        
        # Apply precision
        if precision.numeric_type == "decimal":
            code_lines.append(f"    from decimal import Decimal, ROUND_HALF_EVEN")
            code_lines.append(f"    result = Decimal(str(result)).quantize(")
            code_lines.append(f"        Decimal('0.{'0' * precision.decimal_places}'),")
            code_lines.append(f"        rounding={self._rounding_constant(precision.rounding_rule)}")
            code_lines.append(f"    )")
        else:
            code_lines.append(f"    result = round(result, {precision.decimal_places})")
        
        code_lines.append(f"    return result")
        
        return "\n".join(code_lines)

# Example generated code:
"""
def sharpe_ratio(
    excess_returns: np.ndarray,
    risk_free_rate: float,
    annualization_factor: int = 252
) -> float:
    '''Reference implementation of sharpe_ratio
    
    Generated from specification.
    Precision: 4 decimal places, banker's rounding
    '''
    if not (0.0 <= risk_free_rate <= 1.0):
        raise ValueError(f'risk_free_rate={risk_free_rate} out of range [0.0, 1.0]')
    if not (1 <= annualization_factor <= 365):
        raise ValueError(f'annualization_factor={annualization_factor} out of range [1, 365]')
    
    # Edge case: insufficient data
    if len(excess_returns) < 30:
        raise ValueError(f'Insufficient data: {len(excess_returns)} < 30 days required')
    
    # Edge case: zero volatility
    volatility = np.std(excess_returns) * np.sqrt(annualization_factor)
    if volatility == 0:
        return float('inf') if np.mean(excess_returns) > 0 else 0.0
    
    # Main calculation
    mean_return = np.mean(excess_returns) * annualization_factor
    result = mean_return / volatility
    
    # Apply precision: 4 decimal places, banker's rounding
    from decimal import Decimal, ROUND_HALF_EVEN
    result = Decimal(str(result)).quantize(
        Decimal('0.0000'),
        rounding=ROUND_HALF_EVEN
    )
    
    return float(result)
"""
```

### 3. Cross-Validation Framework

Compare multiple implementations against reference:

```python
# In domain/testing/cross_validator.py

class CrossValidator:
    """Validate implementations against reference and each other"""
    
    def validate_implementation(
        self,
        implementation: Callable,
        reference: Callable,
        test_cases: List[TestCase],
        tolerance: float = 1e-10
    ) -> ValidationReport:
        """Run test cases and compare results"""
        results = []
        
        for test_case in test_cases:
            # Run reference implementation
            try:
                ref_output = reference(**test_case.inputs)
            except Exception as e:
                ref_output = f"ERROR: {e}"
            
            # Run test implementation
            try:
                impl_output = implementation(**test_case.inputs)
            except Exception as e:
                impl_output = f"ERROR: {e}"
            
            # Compare results
            match = self._compare_outputs(
                ref_output,
                impl_output,
                tolerance=test_case.tolerance or tolerance,
                precision=test_case.precision
            )
            
            results.append(TestResult(
                test_case=test_case,
                reference_output=ref_output,
                implementation_output=impl_output,
                match=match,
                discrepancy=self._calculate_discrepancy(ref_output, impl_output)
            ))
        
        return ValidationReport(
            total_tests=len(results),
            passed=sum(1 for r in results if r.match),
            failed=sum(1 for r in results if not r.match),
            results=results,
            discrepancy_summary=self._summarize_discrepancies(results)
        )
    
    def cross_validate(
        self,
        implementations: Dict[str, Callable],
        test_cases: List[TestCase]
    ) -> CrossValidationReport:
        """Compare multiple implementations with each other"""
        # Run all implementations on all test cases
        outputs = {}
        for name, impl in implementations.items():
            outputs[name] = []
            for test_case in test_cases:
                try:
                    result = impl(**test_case.inputs)
                    outputs[name].append(result)
                except Exception as e:
                    outputs[name].append(f"ERROR: {e}")
        
        # Find discrepancies
        discrepancies = []
        for i, test_case in enumerate(test_cases):
            test_outputs = {name: outputs[name][i] for name in implementations.keys()}
            if not self._all_match(test_outputs.values()):
                discrepancies.append(Discrepancy(
                    test_case=test_case,
                    outputs=test_outputs,
                    max_difference=self._max_difference(test_outputs.values())
                ))
        
        return CrossValidationReport(
            implementations=list(implementations.keys()),
            total_tests=len(test_cases),
            consistent_tests=len(test_cases) - len(discrepancies),
            discrepancies=discrepancies
        )

@dataclass
class ValidationReport:
    """Results of validating one implementation against reference"""
    total_tests: int
    passed: int
    failed: int
    results: List[TestResult]
    discrepancy_summary: Dict[str, Any]

@dataclass
class CrossValidationReport:
    """Results of cross-validating multiple implementations"""
    implementations: List[str]
    total_tests: int
    consistent_tests: int
    discrepancies: List[Discrepancy]
```

### 4. Specification Traceability

Link test results back to specifications:

```python
# In domain/testing/traceability.py

class SpecificationTraceability:
    """Track which specification elements are covered by tests"""
    
    def compute_coverage(
        self,
        semantic_ir: SemanticIR,
        test_cases: List[TestCase]
    ) -> CoverageReport:
        """
        Compute test coverage of specification elements:
        - Formulas covered by test cases
        - Parameters exercised at boundaries
        - Edge cases validated
        - Precision rules tested
        - Calendar scenarios tested
        """
        coverage = {
            "formulas": self._formula_coverage(semantic_ir, test_cases),
            "parameters": self._parameter_coverage(semantic_ir, test_cases),
            "edge_cases": self._edge_case_coverage(semantic_ir, test_cases),
            "precision_rules": self._precision_coverage(semantic_ir, test_cases),
            "calendar_scenarios": self._calendar_coverage(semantic_ir, test_cases)
        }
        
        return CoverageReport(
            overall_score=self._compute_overall_score(coverage),
            coverage=coverage,
            gaps=self._identify_gaps(semantic_ir, test_cases),
            recommendations=self._generate_recommendations(coverage)
        )
```

### 5. Continuous Validation

Integrate with CI/CD pipeline:

```yaml
# In .github/workflows/specification-validation.yml

name: Specification Validation

on: [push, pull_request]

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Generate Test Cases
        run: |
          python -m domain.testing.test_generator \
            --specs docs/ \
            --output tests/generated/
      
      - name: Generate Reference Implementations
        run: |
          python -m domain.testing.reference_impl \
            --specs docs/ \
            --output tests/reference/
      
      - name: Run Cross-Validation
        run: |
          pytest tests/generated/ \
            --reference tests/reference/ \
            --implementations src/ \
            --report validation-report.json
      
      - name: Check Validation Results
        run: |
          python -m domain.testing.check_validation \
            --report validation-report.json \
            --threshold 100  # Require 100% match
```

### 6. Validation Report Format

```json
{
  "validation_summary": {
    "timestamp": "2024-12-08T10:30:00Z",
    "implementations_tested": ["backtesting_engine", "production_engine", "validation_engine"],
    "total_test_cases": 847,
    "passed": 845,
    "failed": 2,
    "pass_rate": 0.9976
  },
  "failed_tests": [
    {
      "test_case": "sharpe_ratio_edge_zero_volatility",
      "category": "edge",
      "inputs": {
        "excess_returns": [0.0, 0.0, 0.0, 0.0, 0.0],
        "risk_free_rate": 0.02,
        "annualization_factor": 252
      },
      "reference_output": "inf",
      "implementation_outputs": {
        "backtesting_engine": "inf",
        "production_engine": "inf",
        "validation_engine": 999.0
      },
      "issue": "validation_engine caps infinite Sharpe at 999.0, specification requires 'inf'",
      "severity": "high",
      "specification_reference": "docs/strategies/sharpe-ratio.md#L45"
    }
  ],
  "cross_validation": {
    "discrepancies": 2,
    "max_discrepancy": 0.00001,
    "implementations_with_issues": ["validation_engine"]
  },
  "coverage": {
    "formulas_covered": 0.98,
    "parameters_at_boundaries": 0.95,
    "edge_cases_tested": 0.92,
    "precision_rules_validated": 1.00,
    "calendar_scenarios_tested": 0.88
  },
  "recommendations": [
    "Add test cases for calendar edge cases: year-end with multiple holidays",
    "Increase parameter boundary testing for lookback_period",
    "Fix validation_engine to handle infinite Sharpe ratio correctly"
  ]
}
```

## Consequences

### Positive

- **Verified implementations**: Automated validation against specifications
- **Catch discrepancies early**: Find implementation bugs before production
- **Cross-implementation consistency**: Ensure all implementations produce identical results
- **Specification coverage**: Track which specification elements are tested
- **Regression prevention**: Detect when changes break specification conformance
- **Documentation**: Test cases serve as executable examples

### Negative

- **Test generation complexity**: Generating meaningful test cases from specs is non-trivial
- **Reference implementation maintenance**: Reference code must be kept in sync with specs
- **Performance overhead**: Cross-validation can be time-consuming for large test suites
- **False positives**: Floating point comparisons may flag insignificant differences

### Risks

- **Test case quality**: Generated tests may miss important scenarios
- **Reference implementation bugs**: If reference is wrong, all implementations will match the wrong behavior
- **Specification ambiguity**: Incomplete specifications produce incomplete tests
- **Over-reliance**: May create false confidence if test coverage is insufficient

## Implementation

1. Create `domain/testing/test_generator.py` for test case generation
2. Create `domain/testing/reference_impl.py` for reference implementation generation
3. Create `domain/testing/cross_validator.py` for cross-validation
4. Create `domain/testing/traceability.py` for coverage tracking
5. Add CLI commands for test generation and validation
6. Integrate with CI/CD pipeline
7. Create UI for viewing validation reports
8. Add validation hooks to document analysis pipeline

**Dependencies**:
- pytest for test execution
- numpy/pandas for numerical operations
- hypothesis for property-based testing (advanced test case generation)

**Target**: Phase 13 in implementation plan (after ADR-017 and ADR-018)

## References

- [Enhancement Proposals](../analysis/vision-enhancement-proposals.md) - Section 3 (Verification & Testing Framework)
- [ADR-017: Implementation Precision](017-implementation-precision-specification.md) - Precision specifications to validate
- [ADR-018: Market Calendar Validation](018-market-calendar-validation.md) - Calendar scenarios to test
- [ADR-014: Semantic IR](014-semantic-intermediate-representation.md) - Source of specification metadata
