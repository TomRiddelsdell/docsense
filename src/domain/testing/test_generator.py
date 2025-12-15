"""
Test case generator for creating comprehensive test suites from specifications.

Generates test cases covering normal, boundary, edge, and error scenarios
from semantic IR specifications to validate implementation correctness.
"""

from datetime import date, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional, Set
from uuid import uuid4

from src.domain.value_objects.semantic_ir import DocumentIR, FormulaReference, TermDefinition
from .test_case import TestCase, TestCategory


class TestCaseGenerator:
    """
    Generate executable test cases from semantic specifications.
    
    Creates comprehensive test suites covering:
    - Normal cases with typical values
    - Boundary cases at parameter min/max
    - Edge cases from specifications
    - Error cases for exception handling
    """
    
    def __init__(self):
        """Initialize test case generator."""
        self._random_seed = 42  # For reproducible test generation
    
    def generate_from_formula(
        self,
        formula: FormulaReference,
        document_ir: DocumentIR,
        count_per_category: Optional[Dict[TestCategory, int]] = None,
    ) -> List[TestCase]:
        """
        Generate comprehensive test cases for a formula.
        
        Args:
            formula: Formula to generate tests for
            document_ir: Document IR containing definitions and context
            count_per_category: Number of tests per category (default: {NORMAL: 10, BOUNDARY: len(params)*2, EDGE: 5, ERROR: 3})
            
        Returns:
            List of test cases covering all categories
        """
        if count_per_category is None:
            count_per_category = {
                TestCategory.NORMAL: 10,
                TestCategory.BOUNDARY: len(formula.variables) * 2,
                TestCategory.EDGE: 5,
                TestCategory.ERROR: 3,
            }
        
        test_cases = []
        
        # Extract parameter information from definitions
        params = self._extract_parameters(formula, document_ir)
        
        # Generate normal test cases
        for i in range(count_per_category.get(TestCategory.NORMAL, 10)):
            test_cases.append(self._generate_normal_case(formula, params, i))
        
        # Generate boundary test cases
        boundary_cases = self._generate_boundary_cases(formula, params)
        test_cases.extend(boundary_cases[:count_per_category.get(TestCategory.BOUNDARY, len(boundary_cases))])
        
        # Generate edge test cases
        edge_cases = self._generate_edge_cases(formula, params)
        test_cases.extend(edge_cases[:count_per_category.get(TestCategory.EDGE, 5)])
        
        # Generate error test cases
        error_cases = self._generate_error_cases(formula, params)
        test_cases.extend(error_cases[:count_per_category.get(TestCategory.ERROR, 3)])
        
        return test_cases
    
    def generate_from_document(
        self,
        document_ir: DocumentIR,
        formulas_to_test: Optional[List[str]] = None,
    ) -> Dict[str, List[TestCase]]:
        """
        Generate test cases for all formulas in a document.
        
        Args:
            document_ir: Document IR to generate tests from
            formulas_to_test: Optional list of formula IDs to test (default: all)
            
        Returns:
            Dictionary mapping formula IDs to their test cases
        """
        results = {}
        
        formulas = document_ir.formulae
        if formulas_to_test:
            formulas = [f for f in formulas if f.id in formulas_to_test]
        
        for formula in formulas:
            results[formula.id] = self.generate_from_formula(formula, document_ir)
        
        return results
    
    def _extract_parameters(
        self,
        formula: FormulaReference,
        document_ir: DocumentIR,
    ) -> Dict[str, "ParameterSpec"]:
        """
        Extract parameter specifications from formula and document.
        
        Args:
            formula: Formula to extract parameters from
            document_ir: Document containing definitions
            
        Returns:
            Dictionary mapping parameter names to specifications
        """
        params = {}
        
        for variable in formula.variables:
            # Look up definition
            definition = document_ir.find_definition(variable)
            
            param_spec = ParameterSpec(
                name=variable,
                definition=definition.definition if definition else None,
                param_type=self._infer_type(variable, definition),
                has_range=False,
                min_value=None,
                max_value=None,
                typical_value=None,
            )
            
            # Try to extract range constraints from definition
            if definition and definition.definition:
                param_spec = self._extract_range_constraints(param_spec, definition.definition)
            
            params[variable] = param_spec
        
        return params
    
    def _infer_type(self, variable: str, definition: Optional[TermDefinition]) -> type:
        """Infer parameter type from variable name and definition."""
        var_lower = variable.lower()
        
        # Date-related variables
        if any(keyword in var_lower for keyword in ['date', 'day', 'time', 'maturity', 'expiry']):
            return date
        
        # Integer variables
        if any(keyword in var_lower for keyword in ['count', 'num', 'size', 'index', 'days']):
            return int
        
        # Boolean variables
        if any(keyword in var_lower for keyword in ['is', 'has', 'flag', 'bool']):
            return bool
        
        # Default to float/Decimal for financial calculations
        return float
    
    def _extract_range_constraints(self, param_spec: "ParameterSpec", definition: str) -> "ParameterSpec":
        """Extract min/max constraints from definition text."""
        import re
        
        # Look for patterns like "between X and Y", "range [X, Y]", "from X to Y"
        patterns = [
            r'between\s+([0-9.]+)\s+and\s+([0-9.]+)',
            r'range\s*\[([0-9.]+)\s*,\s*([0-9.]+)\]',
            r'from\s+([0-9.]+)\s+to\s+([0-9.]+)',
            r'minimum\s+([0-9.]+)',
            r'maximum\s+([0-9.]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, definition, re.IGNORECASE)
            if match:
                groups = match.groups()
                if len(groups) == 2:
                    param_spec.has_range = True
                    param_spec.min_value = float(groups[0])
                    param_spec.max_value = float(groups[1])
                    break
                elif 'minimum' in pattern:
                    param_spec.min_value = float(groups[0])
                elif 'maximum' in pattern:
                    param_spec.max_value = float(groups[0])
        
        return param_spec
    
    def _generate_normal_case(
        self,
        formula: FormulaReference,
        params: Dict[str, "ParameterSpec"],
        index: int,
    ) -> TestCase:
        """Generate a normal test case with typical values."""
        inputs = {}
        
        for param_name, param_spec in params.items():
            inputs[param_name] = self._generate_typical_value(param_spec, index)
        
        return TestCase.create(
            name=f"{formula.name or formula.id}_normal_{index}",
            category=TestCategory.NORMAL,
            inputs=inputs,
            description=f"Normal case {index} with typical parameter values",
            metadata={
                "formula_id": formula.id,
                "formula_name": formula.name,
                "section_id": formula.section_id,
            },
        )
    
    def _generate_boundary_cases(
        self,
        formula: FormulaReference,
        params: Dict[str, "ParameterSpec"],
    ) -> List[TestCase]:
        """Generate boundary test cases at parameter limits."""
        test_cases = []
        
        # Get typical values for all parameters
        typical_inputs = {
            name: self._generate_typical_value(spec, 0)
            for name, spec in params.items()
        }
        
        # Generate min/max test for each parameter with range
        for param_name, param_spec in params.items():
            if param_spec.has_range and param_spec.min_value is not None:
                # Test at minimum
                inputs = typical_inputs.copy()
                inputs[param_name] = self._convert_value(param_spec.min_value, param_spec.param_type)
                
                test_cases.append(TestCase.create(
                    name=f"{formula.name or formula.id}_boundary_{param_name}_min",
                    category=TestCategory.BOUNDARY,
                    inputs=inputs,
                    description=f"{param_name} at minimum value {param_spec.min_value}",
                    metadata={
                        "formula_id": formula.id,
                        "boundary_param": param_name,
                        "boundary_type": "min",
                    },
                ))
            
            if param_spec.has_range and param_spec.max_value is not None:
                # Test at maximum
                inputs = typical_inputs.copy()
                inputs[param_name] = self._convert_value(param_spec.max_value, param_spec.param_type)
                
                test_cases.append(TestCase.create(
                    name=f"{formula.name or formula.id}_boundary_{param_name}_max",
                    category=TestCategory.BOUNDARY,
                    inputs=inputs,
                    description=f"{param_name} at maximum value {param_spec.max_value}",
                    metadata={
                        "formula_id": formula.id,
                        "boundary_param": param_name,
                        "boundary_type": "max",
                    },
                ))
        
        return test_cases
    
    def _generate_edge_cases(
        self,
        formula: FormulaReference,
        params: Dict[str, "ParameterSpec"],
    ) -> List[TestCase]:
        """Generate edge test cases for special scenarios."""
        test_cases = []
        
        # Zero values edge case
        zero_inputs = {}
        for param_name, param_spec in params.items():
            if param_spec.param_type in (int, float, Decimal):
                zero_inputs[param_name] = self._convert_value(0, param_spec.param_type)
            else:
                zero_inputs[param_name] = self._generate_typical_value(param_spec, 0)
        
        test_cases.append(TestCase.create(
            name=f"{formula.name or formula.id}_edge_zero_values",
            category=TestCategory.EDGE,
            inputs=zero_inputs,
            description="Edge case with zero numeric values",
            metadata={"formula_id": formula.id, "edge_type": "zero"},
        ))
        
        # Large values edge case
        large_inputs = {}
        for param_name, param_spec in params.items():
            if param_spec.param_type in (int, float):
                large_inputs[param_name] = 1_000_000.0 if param_spec.param_type == float else 1_000_000
            else:
                large_inputs[param_name] = self._generate_typical_value(param_spec, 0)
        
        test_cases.append(TestCase.create(
            name=f"{formula.name or formula.id}_edge_large_values",
            category=TestCategory.EDGE,
            inputs=large_inputs,
            description="Edge case with large numeric values",
            metadata={"formula_id": formula.id, "edge_type": "large"},
        ))
        
        # Date edge cases (if applicable)
        date_params = [name for name, spec in params.items() if spec.param_type == date]
        if date_params:
            # Year-end edge case
            year_end_inputs = {name: self._generate_typical_value(params[name], 0) for name in params}
            for date_param in date_params:
                year_end_inputs[date_param] = date(2024, 12, 31)
            
            test_cases.append(TestCase.create(
                name=f"{formula.name or formula.id}_edge_year_end",
                category=TestCategory.EDGE,
                inputs=year_end_inputs,
                description="Edge case with year-end dates",
                metadata={"formula_id": formula.id, "edge_type": "year_end"},
            ))
            
            # Leap year edge case
            leap_year_inputs = {name: self._generate_typical_value(params[name], 0) for name in params}
            for date_param in date_params:
                leap_year_inputs[date_param] = date(2024, 2, 29)
            
            test_cases.append(TestCase.create(
                name=f"{formula.name or formula.id}_edge_leap_year",
                category=TestCategory.EDGE,
                inputs=leap_year_inputs,
                description="Edge case with leap year date",
                metadata={"formula_id": formula.id, "edge_type": "leap_year"},
            ))
        
        return test_cases
    
    def _generate_error_cases(
        self,
        formula: FormulaReference,
        params: Dict[str, "ParameterSpec"],
    ) -> List[TestCase]:
        """Generate error test cases for invalid inputs."""
        test_cases = []
        
        # Negative values where positive expected
        if any(spec.min_value and spec.min_value >= 0 for spec in params.values()):
            negative_inputs = {}
            for param_name, param_spec in params.items():
                if param_spec.param_type in (int, float) and (param_spec.min_value is None or param_spec.min_value >= 0):
                    negative_inputs[param_name] = -100.0 if param_spec.param_type == float else -100
                else:
                    negative_inputs[param_name] = self._generate_typical_value(param_spec, 0)
            
            test_cases.append(TestCase.create(
                name=f"{formula.name or formula.id}_error_negative_values",
                category=TestCategory.ERROR,
                inputs=negative_inputs,
                expected_exception=ValueError,
                description="Error case with negative values where positive expected",
                metadata={"formula_id": formula.id, "error_type": "negative"},
            ))
        
        # Out of range values
        for param_name, param_spec in params.items():
            if param_spec.has_range and param_spec.max_value is not None:
                out_of_range_inputs = {
                    name: self._generate_typical_value(params[name], 0)
                    for name in params
                }
                out_of_range_inputs[param_name] = self._convert_value(
                    param_spec.max_value * 2, param_spec.param_type
                )
                
                test_cases.append(TestCase.create(
                    name=f"{formula.name or formula.id}_error_{param_name}_out_of_range",
                    category=TestCategory.ERROR,
                    inputs=out_of_range_inputs,
                    expected_exception=ValueError,
                    description=f"Error case with {param_name} out of range",
                    metadata={"formula_id": formula.id, "error_type": "out_of_range", "error_param": param_name},
                ))
                break  # Only generate one out-of-range test
        
        return test_cases
    
    def _generate_typical_value(self, param_spec: "ParameterSpec", seed: int) -> Any:
        """Generate a typical value for a parameter based on its type and constraints."""
        if param_spec.param_type == date:
            # Return a date in the near future
            return date(2024, 1, 1) + timedelta(days=seed * 30)
        
        elif param_spec.param_type == bool:
            return seed % 2 == 0
        
        elif param_spec.param_type == int:
            if param_spec.has_range and param_spec.min_value is not None and param_spec.max_value is not None:
                # Use midpoint of range
                return int((param_spec.min_value + param_spec.max_value) / 2) + seed
            return 100 + seed * 10
        
        elif param_spec.param_type == float:
            if param_spec.has_range and param_spec.min_value is not None and param_spec.max_value is not None:
                # Use midpoint of range
                return (param_spec.min_value + param_spec.max_value) / 2 + seed * 0.1
            return 100.0 + seed * 1.5
        
        else:
            # Default to float
            return 100.0 + seed
    
    def _convert_value(self, value: Any, target_type: type) -> Any:
        """Convert a value to the target type."""
        if target_type == int:
            return int(value)
        elif target_type == float:
            return float(value)
        elif target_type == Decimal:
            return Decimal(str(value))
        elif target_type == bool:
            return bool(value)
        elif target_type == date and isinstance(value, date):
            return value
        return value


class ParameterSpec:
    """Specification for a formula parameter."""
    
    def __init__(
        self,
        name: str,
        definition: Optional[str],
        param_type: type,
        has_range: bool,
        min_value: Optional[float],
        max_value: Optional[float],
        typical_value: Optional[Any] = None,
    ):
        self.name = name
        self.definition = definition
        self.param_type = param_type
        self.has_range = has_range
        self.min_value = min_value
        self.max_value = max_value
        self.typical_value = typical_value
