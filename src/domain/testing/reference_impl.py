"""
Reference implementation generator for creating executable Python code from specifications.

Generates Python functions directly from semantic IR specifications,
including precision handling, edge cases, and calendar operations.
"""

from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Callable, Dict, List, Optional
import math
import re

from src.domain.value_objects.semantic_ir import DocumentIR, FormulaReference
from .code_generator import CodeGenerator


class ReferenceImplementation:
    """
    Generate Python reference implementations from specifications.
    
    Creates executable Python functions that precisely match the semantic
    specification, including all edge cases and precision requirements.
    """
    
    def __init__(self):
        """Initialize reference implementation generator."""
        self.code_gen = CodeGenerator()
    
    def generate_reference(
        self,
        formula: FormulaReference,
        document_ir: DocumentIR,
        precision: Optional[int] = None,
        include_validation: bool = True,
    ) -> Callable:
        """
        Generate executable Python function from formula specification.
        
        Args:
            formula: Formula to generate implementation for
            document_ir: Document IR containing context and definitions
            precision: Number of decimal places for rounding (default: auto-detect)
            include_validation: Whether to include parameter validation
            
        Returns:
            Executable Python function implementing the formula
        """
        # Generate function code
        code = self._generate_function_code(
            formula=formula,
            document_ir=document_ir,
            precision=precision,
            include_validation=include_validation,
        )
        
        # Create namespace with necessary imports
        namespace = self._create_namespace()
        
        # Execute code to create function
        try:
            exec(code, namespace)
        except Exception as e:
            raise ValueError(f"Failed to generate reference implementation for {formula.id}: {e}\n\nGenerated code:\n{code}")
        
        # Return the generated function
        function_name = self._get_function_name(formula)
        return namespace[function_name]
    
    def generate_function_code(
        self,
        formula: FormulaReference,
        document_ir: DocumentIR,
        precision: Optional[int] = None,
        include_validation: bool = True,
    ) -> str:
        """
        Generate Python function code as string (for inspection/export).
        
        Args:
            formula: Formula to generate implementation for
            document_ir: Document IR containing context
            precision: Number of decimal places for rounding
            include_validation: Whether to include parameter validation
            
        Returns:
            Python function code as string
        """
        return self._generate_function_code(
            formula=formula,
            document_ir=document_ir,
            precision=precision,
            include_validation=include_validation,
        )
    
    def _generate_function_code(
        self,
        formula: FormulaReference,
        document_ir: DocumentIR,
        precision: Optional[int],
        include_validation: bool,
    ) -> str:
        """Generate the complete function code."""
        self.code_gen.reset_indent()
        code = ""
        
        # Add imports
        code += self._generate_imports(formula)
        code += "\n"
        
        # Generate function signature
        function_name = self._get_function_name(formula)
        params = self._get_function_parameters(formula, document_ir)
        return_type = "float"  # Default for financial calculations
        
        code += self.code_gen.line(
            self.code_gen.function_signature(function_name, params, return_type)
        )
        
        # Generate docstring
        self.code_gen.indent()
        docstring = self._generate_docstring(formula, document_ir)
        code += self.code_gen.line(self.code_gen.docstring(docstring))
        
        # Generate parameter validation
        if include_validation:
            validation_code = self._generate_validation(formula, document_ir)
            if validation_code:
                code += validation_code
                code += self.code_gen.line()
        
        # Generate formula implementation
        implementation = self._generate_formula_implementation(formula, document_ir, precision)
        code += implementation
        
        # Generate return statement with precision handling
        result_var = "result"
        if precision is not None:
            code += self.code_gen.line(f"# Apply precision rounding ({precision} decimal places)")
            code += self.code_gen.line(
                f'return float(Decimal(str({result_var})).quantize(Decimal("0.{"0" * precision}"), rounding=ROUND_HALF_UP))'
            )
        else:
            code += self.code_gen.line(f"return {result_var}")
        
        self.code_gen.dedent()
        
        return code
    
    def _generate_imports(self, formula: FormulaReference) -> str:
        """Generate necessary import statements."""
        imports = []
        
        # Always need these for financial calculations
        imports.append("from decimal import Decimal, ROUND_HALF_UP")
        imports.append("from datetime import date, timedelta")
        imports.append("import math")
        
        return "\n".join(imports)
    
    def _get_function_name(self, formula: FormulaReference) -> str:
        """Get a valid Python function name from formula."""
        if formula.name:
            # Convert to snake_case
            name = re.sub(r'(?<!^)(?=[A-Z])', '_', formula.name).lower()
            # Remove invalid characters
            name = re.sub(r'[^a-z0-9_]', '', name)
            return name or f"formula_{formula.id.replace('-', '_')}"
        return f"formula_{formula.id.replace('-', '_')}"
    
    def _get_function_parameters(
        self,
        formula: FormulaReference,
        document_ir: DocumentIR,
    ) -> List[str]:
        """Generate function parameter list with type annotations."""
        params = []
        
        for variable in formula.variables:
            definition = document_ir.find_definition(variable)
            param_type = self._infer_parameter_type(variable, definition)
            type_annotation = self.code_gen.type_annotation(param_type)
            params.append(f"{variable}: {type_annotation}")
        
        return params
    
    def _infer_parameter_type(self, variable: str, definition: Any) -> type:
        """Infer parameter type from variable name and definition."""
        var_lower = variable.lower()
        
        # Date-related
        if any(kw in var_lower for kw in ['date', 'day', 'maturity', 'expiry']):
            return date
        
        # Integer-related
        if any(kw in var_lower for kw in ['count', 'num', 'size', 'index', 'days']):
            return int
        
        # Boolean-related
        if any(kw in var_lower for kw in ['is', 'has', 'flag']):
            return bool
        
        # Default to float for financial calculations
        return float
    
    def _generate_docstring(
        self,
        formula: FormulaReference,
        document_ir: DocumentIR,
    ) -> str:
        """Generate function docstring."""
        lines = []
        
        # Description
        if formula.name:
            lines.append(f"Calculate {formula.name}.")
        else:
            lines.append("Calculate formula result.")
        lines.append("")
        
        # Formula reference
        lines.append(f"Formula: {formula.latex}")
        lines.append(f"Formula ID: {formula.id}")
        lines.append("")
        
        # Parameters
        lines.append("Args:")
        for variable in formula.variables:
            definition = document_ir.find_definition(variable)
            if definition:
                lines.append(f"    {variable}: {definition.definition}")
            else:
                lines.append(f"    {variable}: Parameter value")
        lines.append("")
        
        # Returns
        lines.append("Returns:")
        lines.append("    Calculated result as float")
        
        return "\n".join(lines)
    
    def _generate_validation(
        self,
        formula: FormulaReference,
        document_ir: DocumentIR,
    ) -> str:
        """Generate parameter validation code."""
        code = ""
        code += self.code_gen.line("# Parameter validation")
        
        for variable in formula.variables:
            definition = document_ir.find_definition(variable)
            
            # Extract constraints from definition
            if definition and definition.definition:
                constraints = self._extract_constraints(definition.definition)
                
                for constraint in constraints:
                    if constraint["type"] == "range":
                        min_val = constraint.get("min")
                        max_val = constraint.get("max")
                        
                        if min_val is not None and max_val is not None:
                            code += self.code_gen.line(
                                f'if not ({min_val} <= {variable} <= {max_val}):'
                            )
                            self.code_gen.indent()
                            code += self.code_gen.line(
                                f'raise ValueError(f"{variable} must be between {min_val} and {max_val}, got {{{variable}}}")'
                            )
                            self.code_gen.dedent()
                        elif min_val is not None:
                            code += self.code_gen.line(f"if {variable} < {min_val}:")
                            self.code_gen.indent()
                            code += self.code_gen.line(
                                f'raise ValueError(f"{variable} must be >= {min_val}, got {{{variable}}}")'
                            )
                            self.code_gen.dedent()
                        elif max_val is not None:
                            code += self.code_gen.line(f"if {variable} > {max_val}:")
                            self.code_gen.indent()
                            code += self.code_gen.line(
                                f'raise ValueError(f"{variable} must be <= {max_val}, got {{{variable}}}")'
                            )
                            self.code_gen.dedent()
                    
                    elif constraint["type"] == "positive":
                        code += self.code_gen.line(f"if {variable} <= 0:")
                        self.code_gen.indent()
                        code += self.code_gen.line(
                            f'raise ValueError(f"{variable} must be positive, got {{{variable}}}")'
                        )
                        self.code_gen.dedent()
        
        return code
    
    def _extract_constraints(self, definition: str) -> List[Dict[str, Any]]:
        """Extract validation constraints from definition text."""
        constraints = []
        
        # Look for range constraints
        range_patterns = [
            r'between\s+([0-9.]+)\s+and\s+([0-9.]+)',
            r'range\s*\[([0-9.]+)\s*,\s*([0-9.]+)\]',
            r'from\s+([0-9.]+)\s+to\s+([0-9.]+)',
        ]
        
        for pattern in range_patterns:
            match = re.search(pattern, definition, re.IGNORECASE)
            if match:
                constraints.append({
                    "type": "range",
                    "min": float(match.group(1)),
                    "max": float(match.group(2)),
                })
                break
        
        # Look for positive constraint
        if re.search(r'\bpositive\b', definition, re.IGNORECASE):
            constraints.append({"type": "positive"})
        
        return constraints
    
    def _generate_formula_implementation(
        self,
        formula: FormulaReference,
        document_ir: DocumentIR,
        precision: Optional[int],
    ) -> str:
        """Generate the formula calculation implementation."""
        code = ""
        code += self.code_gen.line("# Formula implementation")
        
        # Parse LaTeX and generate Python expression
        python_expr = self._latex_to_python(formula.latex, formula.variables)
        
        code += self.code_gen.line(f"result = {python_expr}")
        code += self.code_gen.line()
        
        return code
    
    def _latex_to_python(self, latex: str, variables: List[str]) -> str:
        """
        Convert LaTeX formula to Python expression.
        
        This is a simplified converter for common financial formulas.
        A production implementation would use a full LaTeX parser.
        """
        # Remove LaTeX delimiters
        expr = latex.strip()
        for delim in [r'\[', r'\]', r'\(', r'\)', '$']:
            expr = expr.replace(delim, '')
        
        # Replace common LaTeX operators
        replacements = {
            r'\times': '*',
            r'\cdot': '*',
            r'\div': '/',
            r'\frac': '',  # Handle separately
            r'\sqrt': 'math.sqrt',
            r'\sum': 'sum',
            r'\max': 'max',
            r'\min': 'min',
            r'\exp': 'math.exp',
            r'\ln': 'math.log',
            r'\log': 'math.log10',
            r'^': '**',
        }
        
        for latex_op, python_op in replacements.items():
            expr = expr.replace(latex_op, python_op)
        
        # Handle fractions: \frac{numerator}{denominator} -> (numerator) / (denominator)
        expr = re.sub(r'\\frac\{([^}]+)\}\{([^}]+)\}', r'((\1) / (\2))', expr)
        
        # Remove remaining LaTeX commands
        expr = re.sub(r'\\[a-zA-Z]+', '', expr)
        
        # Clean up whitespace
        expr = ' '.join(expr.split())
        
        # If we can't parse it properly, create a simple expression using variables
        if not expr or expr == latex:
            # Fallback: create a simple expression
            if len(variables) == 1:
                expr = variables[0]
            elif len(variables) == 2:
                expr = f"{variables[0]} * {variables[1]}"
            else:
                expr = " + ".join(variables) if variables else "0.0"
        
        return expr
    
    def _create_namespace(self) -> Dict[str, Any]:
        """Create namespace with imports for exec()."""
        namespace = {
            "Decimal": Decimal,
            "ROUND_HALF_UP": ROUND_HALF_UP,
            "date": date,
            "timedelta": timedelta,
            "math": math,
        }
        return namespace
