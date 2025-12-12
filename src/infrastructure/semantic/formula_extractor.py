"""Formula extraction from document text."""

import re
import uuid
from typing import List, Set, Optional, Dict

from src.domain.value_objects.semantic_ir import FormulaReference, TermDefinition


class FormulaExtractor:
    """Extract and analyze mathematical formulas from document content."""

    # Common mathematical variable patterns
    VARIABLE_PATTERN = r'([A-Za-z][A-Za-z0-9_]*(?:_{[^}]+})?)'

    # LaTeX commands to ignore as variables
    LATEX_COMMANDS = {
        'sqrt', 'frac', 'sum', 'prod', 'int', 'partial',
        'alpha', 'beta', 'gamma', 'delta', 'epsilon', 'theta',
        'lambda', 'mu', 'pi', 'sigma', 'tau', 'phi', 'omega',
        'times', 'div', 'pm', 'leq', 'geq', 'neq', 'approx',
        'infty', 'ast', 'ln', 'log', 'exp', 'sin', 'cos', 'tan',
        'lim', 'max', 'min', 'sup', 'inf', 'left', 'right',
        'mathrm', 'mathbf', 'mathit', 'text', 'cdot', 'ldots',
    }

    def extract_from_markdown(
        self, markdown: str, section_id_map: Dict[int, str]
    ) -> List[FormulaReference]:
        """
        Extract formulas from markdown LaTeX blocks.

        Args:
            markdown: Markdown content with LaTeX formulas
            section_id_map: Map from line numbers to section IDs

        Returns:
            List of FormulaReference objects
        """
        formulas = []
        formula_counter = 1

        # Find all display math blocks ($$...$$)
        display_math_pattern = r'\$\$(.*?)\$\$'

        for match in re.finditer(display_math_pattern, markdown, re.DOTALL):
            latex = match.group(1).strip()

            # Skip empty formulas
            if not latex or len(latex) < 2:
                continue

            # Find line number
            lines_before = markdown[: match.start()].count("\n")
            line_number = lines_before + 1

            # Find section ID
            section_id = self._find_section_for_line(line_number, section_id_map)
            if not section_id:
                section_id = "section-unknown"

            formula_id = f"formula-{formula_counter}"
            formula = self._extract_formula_details(
                latex, formula_id, section_id, line_number
            )
            formulas.append(formula)
            formula_counter += 1

        return formulas

    def _find_section_for_line(
        self, line_number: int, section_id_map: Dict[int, str]
    ) -> Optional[str]:
        """
        Find the section ID for a given line number.

        Args:
            line_number: Line number in document
            section_id_map: Map from line ranges to section IDs

        Returns:
            Section ID or None
        """
        # Find the section that contains this line
        for start_line, section_id in sorted(section_id_map.items(), reverse=True):
            if line_number >= start_line:
                return section_id
        return None

    def _extract_formula_details(
        self, latex: str, formula_id: str, section_id: str, line_number: int
    ) -> FormulaReference:
        """
        Extract formula details from LaTeX string.

        Args:
            latex: LaTeX formula content
            formula_id: Unique ID for this formula
            section_id: Section containing the formula
            line_number: Line number of formula

        Returns:
            FormulaReference object
        """
        variables = self._extract_variables(latex)
        name = self._extract_formula_name(latex)

        return FormulaReference(
            id=formula_id,
            name=name,
            latex=latex,
            mathml=None,  # Can be generated later if needed
            plain_text=self._latex_to_plain(latex),
            variables=sorted(list(variables)),
            dependencies=[],  # Resolved in second pass
            section_id=section_id,
            line_number=line_number,
        )

    def _extract_variables(self, latex: str) -> Set[str]:
        """
        Extract variable names from LaTeX formula.

        Args:
            latex: LaTeX formula string

        Returns:
            Set of variable names
        """
        variables = set()

        # Remove LaTeX commands and brackets first
        cleaned = re.sub(r'\\[a-z]+\s*', ' ', latex)
        cleaned = re.sub(r'[{}()[\]]', ' ', cleaned)

        # Find all potential variables
        for match in re.finditer(self.VARIABLE_PATTERN, cleaned):
            var = match.group(1)

            # Skip single letters that are likely operators or constants
            if len(var) == 1 and var.lower() in {'a', 'b', 'c', 'x', 'y', 'z', 'e', 'i'}:
                continue

            # Filter out LaTeX commands
            base_var = var.split('_')[0].lower()
            if base_var not in self.LATEX_COMMANDS:
                # Keep original case for variables
                variables.add(var)

        return variables

    def _extract_formula_name(self, latex: str) -> Optional[str]:
        """
        Extract the name of the formula if present (LHS of equation).

        Args:
            latex: LaTeX formula string

        Returns:
            Formula name or None
        """
        # Pattern: Name = ... or Name_{subscript} = ...
        match = re.match(r'^([A-Za-z][A-Za-z0-9_]*(?:_{[^}]+})?)\s*=', latex)
        if match:
            return match.group(1)
        return None

    def _latex_to_plain(self, latex: str) -> str:
        """
        Convert LaTeX to plain text representation.

        Args:
            latex: LaTeX formula string

        Returns:
            Plain text approximation
        """
        plain = latex

        # Replace common LaTeX commands with readable equivalents
        replacements = {
            r'\\sqrt{([^}]+)}': r'sqrt(\1)',
            r'\\frac{([^}]+)}{([^}]+)}': r'(\1)/(\2)',
            r'\\sum': 'sum',
            r'\\prod': 'prod',
            r'\\int': 'integral',
            r'\\times': '*',
            r'\\div': '/',
            r'\\leq': '<=',
            r'\\geq': '>=',
            r'\\neq': '!=',
            r'\\approx': '≈',
        }

        for pattern, replacement in replacements.items():
            plain = re.sub(pattern, replacement, plain)

        # Remove remaining backslashes and braces
        plain = re.sub(r'\\[a-z]+\s*', '', plain)
        plain = re.sub(r'[{}]', '', plain)

        return plain.strip()

    def resolve_dependencies(
        self, formulas: List[FormulaReference], definitions: List[TermDefinition]
    ) -> List[FormulaReference]:
        """
        Resolve formula dependencies by matching variables to formulas and terms.

        Args:
            formulas: List of formulas to resolve
            definitions: List of term definitions

        Returns:
            List of formulas with dependencies resolved (creates new instances)
        """
        # Build lookup maps
        formula_names = {f.name: f.id for f in formulas if f.name}
        term_names = {d.term: d.id for d in definitions}

        # Add aliases
        for d in definitions:
            for alias in d.aliases:
                term_names[alias] = d.id

        resolved_formulas = []

        for formula in formulas:
            deps = []

            for var in formula.variables:
                # Check if variable is another formula
                if var in formula_names and formula_names[var] != formula.id:
                    deps.append(formula_names[var])
                # Check if variable is a defined term
                elif var in term_names:
                    deps.append(term_names[var])

            # Create new formula with dependencies
            resolved_formulas.append(
                FormulaReference(
                    id=formula.id,
                    name=formula.name,
                    latex=formula.latex,
                    mathml=formula.mathml,
                    plain_text=formula.plain_text,
                    variables=formula.variables,
                    dependencies=deps,
                    section_id=formula.section_id,
                    line_number=formula.line_number,
                )
            )

        return resolved_formulas
