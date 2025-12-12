"""Tests for formula extractor."""

import pytest
from src.infrastructure.semantic.formula_extractor import FormulaExtractor
from src.domain.value_objects.semantic_ir import TermDefinition


class TestFormulaExtractor:
    """Test suite for FormulaExtractor."""

    @pytest.fixture
    def extractor(self):
        """Create a FormulaExtractor instance."""
        return FormulaExtractor()

    def test_extract_simple_formula(self, extractor):
        """Test extraction of a simple formula."""
        markdown = """
Some text before.

$$
x = a + b
$$

Some text after.
"""
        section_map = {1: "section-1"}

        formulas = extractor.extract_from_markdown(markdown, section_map)

        assert len(formulas) == 1
        assert "a + b" in formulas[0].latex
        assert formulas[0].section_id == "section-1"

    def test_extract_formula_with_name(self, extractor):
        """Test extraction of named formula (LHS = RHS)."""
        markdown = """
$$
AssetVolatility = \\sqrt{\\frac{252}{N} \\sum r_i^2}
$$
"""
        section_map = {1: "section-1"}

        formulas = extractor.extract_from_markdown(markdown, section_map)

        assert len(formulas) == 1
        assert formulas[0].name == "AssetVolatility"
        assert "sqrt" in formulas[0].latex.lower()

    def test_extract_variables_from_formula(self, extractor):
        """Test variable extraction from LaTeX formula."""
        latex = "\\frac{AssetPrice}{IndexValue} \\times WeightFactor"

        variables = extractor._extract_variables(latex)

        assert "AssetPrice" in variables
        assert "IndexValue" in variables
        assert "WeightFactor" in variables
        # LaTeX commands should not be included
        assert "frac" not in variables
        assert "times" not in variables

    def test_latex_commands_filtered(self, extractor):
        """Test that LaTeX commands are filtered from variables."""
        latex = "\\sqrt{x} + \\sum_{i=1}^n a_i + \\alpha \\beta"

        variables = extractor._extract_variables(latex)

        # Should not include LaTeX commands
        assert "sqrt" not in variables
        assert "sum" not in variables
        assert "alpha" not in variables
        assert "beta" not in variables

    def test_extract_formula_name(self, extractor):
        """Test formula name extraction."""
        latex1 = "VolatilityFactor = 0.5 * RiskMetric"
        latex2 = "x = y + z"  # Simple variable on LHS

        name1 = extractor._extract_formula_name(latex1)
        name2 = extractor._extract_formula_name(latex2)

        assert name1 == "VolatilityFactor"
        assert name2 == "x"  # LHS variable extraction

    def test_latex_to_plain_text(self, extractor):
        """Test conversion of LaTeX to plain text."""
        latex = "\\sqrt{\\frac{a}{b}} \\times c"

        plain = extractor._latex_to_plain(latex)

        assert "sqrt" in plain.lower()
        assert "\\" not in plain  # LaTeX backslashes removed
        assert "{" not in plain  # Braces removed
        assert "}" not in plain

    def test_resolve_formula_dependencies(self, extractor):
        """Test resolution of formula dependencies."""
        from src.domain.value_objects.semantic_ir import FormulaReference

        formulas = [
            FormulaReference(
                id="formula-1",
                name="Result",
                latex="Result = Factor1 * Factor2",
                section_id="section-1",
                variables=["Factor1", "Factor2"],
            ),
            FormulaReference(
                id="formula-2",
                name="Factor1",
                latex="Factor1 = BaseValue * 2",
                section_id="section-1",
                variables=["BaseValue"],
            ),
        ]

        definitions = [
            TermDefinition(
                id="def-1",
                term="BaseValue",
                definition="The starting value",
                section_id="section-1",
            ),
        ]

        resolved = extractor.resolve_dependencies(formulas, definitions)

        # formula-1 should depend on formula-2 (Factor1)
        result_formula = next(f for f in resolved if f.id == "formula-1")
        assert "formula-2" in result_formula.dependencies

        # formula-2 should depend on def-1 (BaseValue)
        factor_formula = next(f for f in resolved if f.id == "formula-2")
        assert "def-1" in factor_formula.dependencies

    def test_multiple_formulas_extraction(self, extractor):
        """Test extraction of multiple formulas from markdown."""
        markdown = """
First formula:
$$
x = a + b
$$

Second formula:
$$
y = c * d
$$

Third formula:
$$
z = x + y
$$
"""
        section_map = {1: "section-1"}

        formulas = extractor.extract_from_markdown(markdown, section_map)

        assert len(formulas) == 3
        assert formulas[0].id == "formula-1"
        assert formulas[1].id == "formula-2"
        assert formulas[2].id == "formula-3"

    def test_empty_formula_skipped(self, extractor):
        """Test that empty formulas are skipped."""
        markdown = """
$$
$$

$$

$$

$$
x = y
$$
"""
        section_map = {1: "section-1"}

        formulas = extractor.extract_from_markdown(markdown, section_map)

        # Should only extract the non-empty formula
        assert len(formulas) == 1
        assert "x = y" in formulas[0].latex

    def test_section_mapping(self, extractor):
        """Test that formulas are mapped to correct sections."""
        markdown = """Line 1
Line 2
$$
formula1
$$
Line 5
Line 6
$$
formula2
$$
"""
        # Line 3 is in section-1, line 7 is in section-2
        section_map = {1: "section-1", 5: "section-2"}

        formulas = extractor.extract_from_markdown(markdown, section_map)

        assert len(formulas) == 2
        assert formulas[0].section_id == "section-1"
        assert formulas[1].section_id == "section-2"

    def test_formula_with_complex_latex(self, extractor):
        """Test extraction of complex LaTeX formulas."""
        markdown = """
$$
\\sigma_{LT} = \\sqrt{\\frac{216}{3 \\times N_{init}}} \\sum_{i=1}^{N} \\left(\\ln\\frac{A_i}{A_{i-3}}\\right)^2
$$
"""
        section_map = {1: "section-1"}

        formulas = extractor.extract_from_markdown(markdown, section_map)

        assert len(formulas) == 1
        assert "sigma" in formulas[0].latex or "σ" in formulas[0].latex
        assert "sqrt" in formulas[0].latex.lower()
        assert "sum" in formulas[0].latex.lower()

    def test_resolve_dependencies_with_aliases(self, extractor):
        """Test dependency resolution with term aliases."""
        from src.domain.value_objects.semantic_ir import FormulaReference

        formulas = [
            FormulaReference(
                id="formula-1",
                name="Result",
                latex="Result = LTV * Factor",
                section_id="section-1",
                variables=["LTV", "Factor"],
            ),
        ]

        definitions = [
            TermDefinition(
                id="def-1",
                term="Long-Term Volatility",
                definition="The volatility measure",
                section_id="section-1",
                aliases=["LTV"],  # LTV is an alias
            ),
        ]

        resolved = extractor.resolve_dependencies(formulas, definitions)

        # Should resolve LTV to def-1 through alias
        assert "def-1" in resolved[0].dependencies
