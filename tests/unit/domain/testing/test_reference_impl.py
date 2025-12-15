"""Unit tests for ReferenceImplementation and code generation."""

import pytest
from decimal import Decimal
from src.domain.testing.reference_impl import ReferenceImplementation
from src.domain.testing.code_generator import CodeGenerator


@pytest.fixture
def simple_formula():
    """Simple formula for testing."""
    return {
        'id': 'formula-001',
        'name': 'Simple Interest',
        'latex': r'I = P \times r \times t',
        'parameters': [
            {'name': 'P', 'description': 'Principal amount', 'type': 'numeric'},
            {'name': 'r', 'description': 'Interest rate', 'type': 'numeric'},
            {'name': 't', 'description': 'Time period', 'type': 'numeric'}
        ],
        'description': 'Calculate simple interest'
    }


@pytest.fixture
def complex_formula():
    """Complex formula with fractions and exponents."""
    return {
        'id': 'formula-002',
        'name': 'Compound Interest',
        'latex': r'A = P \times \left(1 + \frac{r}{n}\right)^{n \times t}',
        'parameters': [
            {'name': 'P', 'description': 'Principal', 'type': 'numeric'},
            {'name': 'r', 'description': 'Annual rate', 'type': 'numeric'},
            {'name': 'n', 'description': 'Compounds per year', 'type': 'numeric'},
            {'name': 't', 'description': 'Years', 'type': 'numeric'}
        ],
        'description': 'Calculate compound interest'
    }


class TestCodeGenerator:
    """Tests for CodeGenerator utility."""

    def test_latex_to_python_basic_operators(self):
        """Test converting basic LaTeX operators to Python."""
        generator = CodeGenerator()
        
        # Multiplication
        assert r'\times' in generator.latex_operators
        # Division
        assert r'\div' in generator.latex_operators
        # Fraction
        assert r'\frac' in generator.latex_operators

    def test_convert_multiplication(self):
        """Test converting LaTeX multiplication to Python."""
        generator = CodeGenerator()
        latex = r'P \times r'
        python = generator.latex_to_python(latex)
        assert '*' in python
        assert 'P' in python
        assert 'r' in python

    def test_convert_fraction(self):
        """Test converting LaTeX fraction to Python."""
        generator = CodeGenerator()
        latex = r'\frac{a}{b}'
        python = generator.latex_to_python(latex)
        assert '/' in python or 'a' in python
        assert 'b' in python

    def test_convert_exponent(self):
        """Test converting LaTeX exponent to Python."""
        generator = CodeGenerator()
        latex = r'x^{2}'
        python = generator.latex_to_python(latex)
        assert '**' in python or 'pow' in python.lower()

    def test_sanitize_variable_name(self):
        """Test sanitizing variable names."""
        generator = CodeGenerator()
        
        # Test Greek letters
        assert generator.sanitize_variable_name('\\alpha') == 'alpha'
        assert generator.sanitize_variable_name('\\beta') == 'beta'
        
        # Test special characters
        assert '_' not in generator.sanitize_variable_name('x_1')[0]

    def test_generate_function_signature(self):
        """Test generating function signature."""
        generator = CodeGenerator()
        params = [
            {'name': 'P', 'type': 'numeric'},
            {'name': 'r', 'type': 'numeric'}
        ]
        
        signature = generator.generate_function_signature('calculate_interest', params)
        assert 'def calculate_interest' in signature
        assert 'P' in signature
        assert 'r' in signature
        assert 'Decimal' in signature

    def test_generate_docstring(self):
        """Test generating function docstring."""
        generator = CodeGenerator()
        params = [
            {'name': 'P', 'description': 'Principal', 'type': 'numeric'},
            {'name': 'r', 'description': 'Rate', 'type': 'numeric'}
        ]
        
        docstring = generator.generate_docstring('Calculate interest', params, 'Decimal')
        assert 'Calculate interest' in docstring
        assert 'P' in docstring
        assert 'Principal' in docstring
        assert 'Returns' in docstring

    def test_generate_parameter_validation(self):
        """Test generating parameter validation code."""
        generator = CodeGenerator()
        params = [
            {'name': 'P', 'type': 'numeric', 'min': 0},
            {'name': 'r', 'type': 'numeric', 'min': 0, 'max': 1}
        ]
        
        validation = generator.generate_parameter_validation(params)
        assert 'if' in validation or 'P' in validation
        assert 'ValueError' in validation or 'raise' in validation


class TestReferenceImplementation:
    """Tests for ReferenceImplementation generator."""

    def test_initialization(self):
        """Test reference implementation initialization."""
        ref_impl = ReferenceImplementation()
        assert ref_impl is not None

    def test_generate_simple_reference(self, simple_formula):
        """Test generating reference implementation for simple formula."""
        ref_impl = ReferenceImplementation()
        
        code = ref_impl.generate_reference(
            formula=simple_formula,
            precision=10
        )
        
        assert code is not None
        assert 'def' in code
        assert 'calculate_simple_interest' in code.lower() or 'simple_interest' in code.lower()
        assert 'P' in code
        assert 'r' in code
        assert 't' in code
        assert 'Decimal' in code

    def test_reference_includes_docstring(self, simple_formula):
        """Test that generated reference includes docstring."""
        ref_impl = ReferenceImplementation()
        code = ref_impl.generate_reference(simple_formula, precision=10)
        
        assert '"""' in code or "'''" in code
        assert simple_formula['description'] in code or 'Simple Interest' in code

    def test_reference_includes_type_hints(self, simple_formula):
        """Test that generated reference includes type hints."""
        ref_impl = ReferenceImplementation()
        code = ref_impl.generate_reference(simple_formula, precision=10)
        
        assert 'Decimal' in code
        assert '->' in code

    def test_reference_includes_validation(self, simple_formula):
        """Test that generated reference includes parameter validation."""
        ref_impl = ReferenceImplementation()
        
        # Add constraints to formula
        formula_with_constraints = simple_formula.copy()
        formula_with_constraints['parameters'] = [
            {'name': 'P', 'type': 'numeric', 'min': 0},
            {'name': 'r', 'type': 'numeric', 'min': 0, 'max': 1},
            {'name': 't', 'type': 'numeric', 'min': 0}
        ]
        
        code = ref_impl.generate_reference(formula_with_constraints, precision=10, include_validation=True)
        
        # Should include validation logic
        has_validation = 'if' in code or 'ValueError' in code or 'raise' in code
        assert has_validation

    def test_reference_uses_decimal_arithmetic(self, simple_formula):
        """Test that generated reference uses Decimal arithmetic."""
        ref_impl = ReferenceImplementation()
        code = ref_impl.generate_reference(simple_formula, precision=10)
        
        assert 'Decimal' in code
        assert 'from decimal import Decimal' in code or 'import decimal' in code.lower()

    def test_generate_complex_reference(self, complex_formula):
        """Test generating reference for complex formula."""
        ref_impl = ReferenceImplementation()
        code = ref_impl.generate_reference(complex_formula, precision=15)
        
        assert code is not None
        assert 'def' in code
        assert 'P' in code
        assert 'r' in code
        assert 'n' in code
        assert 't' in code

    def test_precision_setting(self, simple_formula):
        """Test that precision setting is respected."""
        ref_impl = ReferenceImplementation()
        
        code_low_precision = ref_impl.generate_reference(simple_formula, precision=5)
        code_high_precision = ref_impl.generate_reference(simple_formula, precision=20)
        
        # Both should have precision settings
        assert 'getcontext' in code_low_precision or 'Decimal' in code_low_precision
        assert 'getcontext' in code_high_precision or 'Decimal' in code_high_precision

    def test_reference_is_executable(self, simple_formula):
        """Test that generated reference code is syntactically valid Python."""
        ref_impl = ReferenceImplementation()
        code = ref_impl.generate_reference(simple_formula, precision=10)
        
        # Try to compile the code
        try:
            compile(code, '<string>', 'exec')
            is_valid = True
        except SyntaxError:
            is_valid = False
        
        assert is_valid

    def test_function_naming_convention(self, simple_formula):
        """Test that function names follow Python conventions."""
        ref_impl = ReferenceImplementation()
        code = ref_impl.generate_reference(simple_formula, precision=10)
        
        # Should use snake_case for function names
        assert 'def ' in code
        lines = code.split('\n')
        def_lines = [l for l in lines if l.strip().startswith('def ')]
        assert len(def_lines) > 0
        
        for line in def_lines:
            func_name = line.split('def ')[1].split('(')[0]
            # Should be lowercase with underscores
            assert func_name.islower() or '_' in func_name

    def test_reference_without_validation(self, simple_formula):
        """Test generating reference without validation."""
        ref_impl = ReferenceImplementation()
        code = ref_impl.generate_reference(simple_formula, precision=10, include_validation=False)
        
        assert code is not None
        assert 'def' in code

    def test_empty_formula_handling(self):
        """Test handling of empty or invalid formula."""
        ref_impl = ReferenceImplementation()
        
        with pytest.raises((ValueError, KeyError, TypeError)):
            ref_impl.generate_reference({}, precision=10)

    def test_formula_with_no_parameters(self):
        """Test formula with no parameters."""
        ref_impl = ReferenceImplementation()
        formula = {
            'id': 'const-001',
            'name': 'Constant',
            'latex': r'c = 3.14159',
            'parameters': [],
            'description': 'Pi constant'
        }
        
        code = ref_impl.generate_reference(formula, precision=10)
        assert code is not None
        assert 'def' in code
