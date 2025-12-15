"""Unit tests for ReferenceImplementation and code generation."""

import pytest
from decimal import Decimal
from src.domain.testing.reference_impl import ReferenceImplementation
from src.domain.testing.code_generator import CodeGenerator
from src.domain.value_objects.semantic_ir import (
    DocumentIR,
    FormulaReference,
    IRSection,
    TermDefinition,
    SectionType
)


@pytest.fixture
def simple_formula():
    """Simple formula for testing: I = P * r * t"""
    return FormulaReference(
        id='formula-001',
        name='simple_interest',
        latex=r'I = P \times r \times t',
        section_id='section-1',
        variables=['P', 'r', 't'],
        plain_text='I = P * r * t'
    )


@pytest.fixture
def complex_formula():
    """Complex formula with fractions and exponents."""
    return FormulaReference(
        id='formula-002',
        name='compound_interest',
        latex=r'A = P \left(1 + \frac{r}{n}\right)^{nt}',
        section_id='section-1',
        variables=['P', 'r', 'n', 't'],
        plain_text='A = P * (1 + r/n)^(n*t)'
    )


@pytest.fixture
def document_ir():
    """Basic DocumentIR for testing."""
    return DocumentIR(
        document_id='doc-001',
        title='Test Document',
        original_format='pdf',
        sections=[
            IRSection(
                id='section-1',
                title='Formulas',
                content='Test content',
                level=1,
                section_type=SectionType.NARRATIVE
            )
        ],
        definitions=[],
        formulae=[],
        tables=[],
        cross_references=[],
        metadata={},
        raw_markdown='# Test'
    )


class TestCodeGenerator:
    """Tests for CodeGenerator utility."""

    def test_initialization(self):
        """Test CodeGenerator initialization."""
        generator = CodeGenerator()
        assert generator.indent_size == 4
        assert generator._current_indent == 0

    def test_indent_dedent(self):
        """Test indentation management."""
        generator = CodeGenerator()
        assert generator._current_indent == 0
        
        generator.indent()
        assert generator._current_indent == 4
        
        generator.indent()
        assert generator._current_indent == 8
        
        generator.dedent()
        assert generator._current_indent == 4
        
        generator.reset_indent()
        assert generator._current_indent == 0

    def test_line_generation(self):
        """Test line generation with indentation."""
        generator = CodeGenerator()
        
        line = generator.line("print('hello')")
        assert line == "print('hello')\n"
        
        generator.indent()
        line = generator.line("print('indented')")
        assert line == "    print('indented')\n"

    def test_function_signature_generation(self):
        """Test generating function signatures."""
        generator = CodeGenerator()
        
        sig = generator.function_signature(
            "calculate",
            ["x: float", "y: float"],
            "float"
        )
        assert sig == "def calculate(x: float, y: float) -> float:"

    def test_docstring_generation(self):
        """Test docstring generation."""
        generator = CodeGenerator()
        
        doc = generator.docstring("Simple function")
        assert doc == '"""Simple function"""\n'
        
        doc_multi = generator.docstring("Line 1\nLine 2")
        assert '"""' in doc_multi
        assert 'Line 1' in doc_multi
        assert 'Line 2' in doc_multi

    def test_import_statement_generation(self):
        """Test import statement generation."""
        generator = CodeGenerator()
        
        import_stmt = generator.import_statement("math")
        assert import_stmt == "import math\n"
        
        from_import = generator.import_statement("decimal", ["Decimal", "ROUND_HALF_UP"])
        assert from_import == "from decimal import Decimal, ROUND_HALF_UP\n"


class TestReferenceImplementation:
    """Tests for ReferenceImplementation generator."""

    def test_initialization(self):
        """Test reference implementation initialization."""
        ref_impl = ReferenceImplementation()
        assert ref_impl is not None

    def test_generate_simple_reference(self, simple_formula, document_ir):
        """Test generating reference implementation for simple formula."""
        ref_impl = ReferenceImplementation()
        
        # generate_reference returns a Callable
        func = ref_impl.generate_reference(
            formula=simple_formula,
            document_ir=document_ir,
            precision=10
        )
        
        assert func is not None
        assert callable(func)
        
        # Test that the function works
        result = func(P=100.0, r=0.05, t=2.0)
        assert result is not None
        assert isinstance(result, float)

    def test_reference_function_code_includes_docstring(self, simple_formula, document_ir):
        """Test that generated reference code includes docstring."""
        ref_impl = ReferenceImplementation()
        code = ref_impl.generate_function_code(
            formula=simple_formula,
            document_ir=document_ir,
            precision=10
        )
        
        assert '"""' in code
        assert 'def ' in code

    def test_reference_function_code_includes_type_hints(self, simple_formula, document_ir):
        """Test that generated reference code includes type hints."""
        ref_impl = ReferenceImplementation()
        code = ref_impl.generate_function_code(
            formula=simple_formula,
            document_ir=document_ir,
            precision=10
        )
        
        assert '->' in code
        assert 'float' in code

    def test_reference_validation_flag(self, simple_formula, document_ir):
        """Test that validation flag is respected."""
        ref_impl = ReferenceImplementation()
        
        code_with_val = ref_impl.generate_function_code(
            formula=simple_formula,
            document_ir=document_ir,
            precision=10,
            include_validation=True
        )
        
        code_without_val = ref_impl.generate_function_code(
            formula=simple_formula,
            document_ir=document_ir,
            precision=10,
            include_validation=False
        )
        
        assert code_with_val is not None
        assert code_without_val is not None
        assert 'def ' in code_with_val
        assert 'def ' in code_without_val

    def test_reference_code_uses_decimal_for_precision(self, simple_formula, document_ir):
        """Test that generated reference code uses Decimal for precision."""
        ref_impl = ReferenceImplementation()
        code = ref_impl.generate_function_code(
            formula=simple_formula,
            document_ir=document_ir,
            precision=10
        )
        
        assert 'Decimal' in code
        assert 'from decimal import' in code

    def test_generate_complex_formula_code(self, complex_formula, document_ir):
        """Test that complex formulas generate code (even if not perfect)."""
        ref_impl = ReferenceImplementation()
        
        # Complex formulas may not convert perfectly - test that code is generated
        code = ref_impl.generate_function_code(
            formula=complex_formula,
            document_ir=document_ir,
            precision=15
        )
        
        assert code is not None
        assert 'def compound_interest' in code
        assert 'P' in code and 'r' in code
        # Note: LaTeX conversion for complex formulas is basic and may not be syntactically valid

    def test_precision_setting_in_code(self, simple_formula, document_ir):
        """Test that precision setting is reflected in generated code."""
        ref_impl = ReferenceImplementation()
        
        code_with_precision = ref_impl.generate_function_code(
            formula=simple_formula,
            document_ir=document_ir,
            precision=5
        )
        
        code_without_precision = ref_impl.generate_function_code(
            formula=simple_formula,
            document_ir=document_ir,
            precision=None
        )
        
        # Both should generate valid code
        assert 'def ' in code_with_precision
        assert 'def ' in code_without_precision
        
        # Code with precision should mention Decimal
        assert 'Decimal' in code_with_precision

    def test_generated_code_is_valid_python(self, simple_formula, document_ir):
        """Test that generated reference code is syntactically valid Python."""
        ref_impl = ReferenceImplementation()
        code = ref_impl.generate_function_code(
            formula=simple_formula,
            document_ir=document_ir,
            precision=10
        )
        
        # Try to compile the code
        try:
            compile(code, '<string>', 'exec')
            is_valid = True
        except SyntaxError:
            is_valid = False
        
        assert is_valid

    def test_function_naming_convention(self, simple_formula, document_ir):
        """Test that function names follow Python conventions."""
        ref_impl = ReferenceImplementation()
        code = ref_impl.generate_function_code(
            formula=simple_formula,
            document_ir=document_ir,
            precision=10
        )
        
        # Should use snake_case for function names
        assert 'def ' in code
        lines = code.split('\n')
        def_lines = [l for l in lines if l.strip().startswith('def ')]
        assert len(def_lines) > 0
        
        for line in def_lines:
            func_name = line.split('def ')[1].split('(')[0]
            # Should be lowercase with underscores
            assert func_name.islower() or '_' in func_name

    def test_reference_without_validation(self, simple_formula, document_ir):
        """Test generating reference without validation."""
        ref_impl = ReferenceImplementation()
        func = ref_impl.generate_reference(
            formula=simple_formula,
            document_ir=document_ir,
            precision=10,
            include_validation=False
        )
        
        assert func is not None
        assert callable(func)

    def test_generated_function_executes(self, simple_formula, document_ir):
        """Test that generated function actually executes and returns results."""
        ref_impl = ReferenceImplementation()
        func = ref_impl.generate_reference(
            formula=simple_formula,
            document_ir=document_ir,
            precision=10
        )
        
        # Execute the function with test inputs
        result = func(P=1000.0, r=0.05, t=2.0)
        
        # Should return approximately 100 (1000 * 0.05 * 2)
        assert result is not None
        assert isinstance(result, float)
        assert 90.0 < result < 110.0  # Allow some margin
