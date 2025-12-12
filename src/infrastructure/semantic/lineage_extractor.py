"""Extract term lineage information from definitions."""

import re
import logging
from typing import List, Dict, Set, Optional

from src.domain.value_objects.semantic_ir import (
    TermLineage,
    TermDependency,
    Parameter,
    DependencyType,
)

logger = logging.getLogger(__name__)


class LineageExtractor:
    """
    Extract lineage information from term definitions.

    This class analyzes definitions to identify:
    - References to other defined terms
    - Parameters and variables
    - Mathematical formulas and computations
    - Dependencies and relationships
    """

    def __init__(self, known_terms: Optional[List[str]] = None):
        """
        Initialize lineage extractor.

        Args:
            known_terms: List of known term names for reference matching
        """
        self._known_terms = set(known_terms or [])

        # Patterns for identifying parameters
        self._parameter_patterns = [
            # Variables in formulas: x, y, N, T, etc.
            r'\b([A-Z])\b(?!\w)',  # Single uppercase letter
            r'\b([a-z])\b(?=\s*[=+\-*/])',  # Single lowercase letter near math
            # Common parameter patterns
            r'(?:parameter|variable|value)\s+([A-Za-z_]\w*)',
            # Percentage patterns
            r'(\d+(?:\.\d+)?)\s*%',  # e.g., "5%"
            # Numeric values with units
            r'(\d+(?:,\d{3})*(?:\.\d+)?)\s*(USD|days|years|months|basis points|bp)',
        ]

        # Patterns for mathematical operations
        self._computation_patterns = [
            r'(?:sum|total|aggregate|combined?\s+(?:of|from))',
            r'(?:product|multiply|multiplied|times)',
            r'(?:difference|subtract|minus|less)',
            r'(?:quotient|divide|divided\s+by)',
            r'(?:average|mean|median)',
            r'(?:maximum|max|minimum|min)',
            r'(?:calculated|computed|derived)\s+(?:as|from|by)',
        ]

        # Patterns for conditional dependencies
        self._conditional_patterns = [
            r'(?:if|when|where|provided that|subject to)',
            r'(?:in the event|in case)',
            r'(?:unless|except)',
        ]

    def extract_lineage(
        self,
        definition: str,
        all_known_terms: Optional[Set[str]] = None,
    ) -> TermLineage:
        """
        Extract lineage information from a definition.

        Args:
            definition: The term definition text
            all_known_terms: Set of all known term names in the document

        Returns:
            TermLineage object with extracted dependencies and parameters
        """
        if all_known_terms:
            self._known_terms = all_known_terms

        # Extract different components
        input_terms = self._extract_term_dependencies(definition)
        parameters = self._extract_parameters(definition)
        is_computed = self._is_computed_term(definition)
        computation_desc = self._extract_computation_description(definition)
        formula = self._extract_formula(definition)
        conditions = self._extract_conditions(definition)

        return TermLineage(
            input_terms=input_terms,
            parameters=parameters,
            is_computed=is_computed,
            computation_description=computation_desc,
            formula=formula,
            conditions=conditions,
        )

    def _extract_term_dependencies(self, definition: str) -> List[TermDependency]:
        """Extract references to other defined terms."""
        dependencies = []
        seen = set()

        # Look for quoted terms (most reliable)
        quoted_pattern = r'"([^"]+)"'
        for match in re.finditer(quoted_pattern, definition):
            term = match.group(1)
            if term in self._known_terms and term not in seen:
                dependencies.append(
                    TermDependency(
                        name=term,
                        dependency_type=DependencyType.DIRECT_REFERENCE,
                        context=self._get_context(definition, match.start(), match.end()),
                    )
                )
                seen.add(term)

        # Look for capitalized multi-word terms that match known terms
        for known_term in self._known_terms:
            if known_term in seen:
                continue

            # Create a pattern that matches the term as a whole word sequence
            escaped_term = re.escape(known_term)
            pattern = r'\b' + escaped_term + r'\b'

            if re.search(pattern, definition, re.IGNORECASE):
                dependencies.append(
                    TermDependency(
                        name=known_term,
                        dependency_type=DependencyType.DIRECT_REFERENCE,
                        context=f"References '{known_term}'",
                    )
                )
                seen.add(known_term)

        return dependencies

    def _extract_parameters(self, definition: str) -> List[Parameter]:
        """Extract parameters and variables from the definition."""
        parameters = []
        seen = set()

        # Extract percentages
        pct_pattern = r'(\d+(?:\.\d+)?)\s*(?:%|percent|percentage)'
        for match in re.finditer(pct_pattern, definition, re.IGNORECASE):
            value = match.group(1)
            param_name = f"{value}%"
            if param_name not in seen:
                parameters.append(
                    Parameter(
                        name=param_name,
                        param_type="percentage",
                        units="percent",
                        context=self._get_context(definition, match.start(), match.end()),
                        default_value=float(value),
                    )
                )
                seen.add(param_name)

        # Extract numeric values with units
        numeric_pattern = r'(\d+(?:,\d{3})*(?:\.\d+)?)\s*(USD|dollars?|days?|years?|months?|basis\s+points?|bp)\b'
        for match in re.finditer(numeric_pattern, definition, re.IGNORECASE):
            value = match.group(1).replace(',', '')
            unit = match.group(2)
            param_name = f"{value} {unit}"
            if param_name not in seen:
                param_type = self._classify_parameter_type(unit)
                parameters.append(
                    Parameter(
                        name=param_name,
                        param_type=param_type,
                        units=unit,
                        context=self._get_context(definition, match.start(), match.end()),
                        default_value=float(value) if '.' in value else int(value),
                    )
                )
                seen.add(param_name)

        # Extract single-letter variables (common in formulas)
        if self._contains_formula(definition):
            var_pattern = r'\b([A-Za-z])\b(?=\s*[=+\-*/(),])'
            for match in re.finditer(var_pattern, definition):
                var = match.group(1)
                param_name = f"variable_{var}"
                if param_name not in seen:
                    parameters.append(
                        Parameter(
                            name=var,
                            param_type="variable",
                            context=self._get_context(definition, match.start(), match.end()),
                            description=f"Mathematical variable {var}",
                        )
                    )
                    seen.add(param_name)

        return parameters

    def _is_computed_term(self, definition: str) -> bool:
        """Determine if this term is computed/derived."""
        for pattern in self._computation_patterns:
            if re.search(pattern, definition, re.IGNORECASE):
                return True
        return self._contains_formula(definition)

    def _extract_computation_description(self, definition: str) -> str:
        """Extract a description of how the term is computed."""
        for pattern in self._computation_patterns:
            match = re.search(pattern, definition, re.IGNORECASE)
            if match:
                # Get surrounding context
                start = max(0, match.start() - 50)
                end = min(len(definition), match.end() + 100)
                context = definition[start:end].strip()
                return context[:200]  # Limit length
        return ""

    def _extract_formula(self, definition: str) -> Optional[str]:
        """Extract mathematical formula if present."""
        # Look for equation patterns
        formula_pattern = r'([A-Za-z]\s*=\s*[^.;]+(?:[+\-*/]\s*[^.;]+)*)'
        match = re.search(formula_pattern, definition)
        if match:
            return match.group(1).strip()

        # Look for LaTeX-style formulas
        latex_pattern = r'\$([^$]+)\$'
        match = re.search(latex_pattern, definition)
        if match:
            return match.group(1).strip()

        return None

    def _extract_conditions(self, definition: str) -> List[str]:
        """Extract conditional clauses."""
        conditions = []

        for pattern in self._conditional_patterns:
            for match in re.finditer(pattern, definition, re.IGNORECASE):
                # Get the conditional clause (next ~100 chars)
                start = match.start()
                end = min(len(definition), start + 150)
                condition = definition[start:end]

                # Stop at sentence boundary
                sentence_end = re.search(r'[.;]', condition)
                if sentence_end:
                    condition = condition[:sentence_end.start()]

                conditions.append(condition.strip())

        return conditions[:5]  # Limit to first 5 conditions

    def _contains_formula(self, definition: str) -> bool:
        """Check if definition contains mathematical formulas."""
        # Look for mathematical operators
        if re.search(r'[+\-*/=]', definition):
            # Check for numbers or variables nearby
            if re.search(r'\d+\s*[+\-*/]\s*\d+', definition):
                return True
            if re.search(r'[A-Za-z]\s*[+\-*/=]\s*[A-Za-z]', definition):
                return True
        return False

    def _classify_parameter_type(self, unit: str) -> str:
        """Classify parameter type based on units."""
        unit_lower = unit.lower()
        if 'usd' in unit_lower or 'dollar' in unit_lower:
            return 'currency'
        elif 'day' in unit_lower or 'month' in unit_lower or 'year' in unit_lower:
            return 'duration'
        elif 'basis' in unit_lower or 'bp' in unit_lower:
            return 'basis_points'
        return 'numeric'

    def _get_context(self, text: str, start: int, end: int, window: int = 50) -> str:
        """Get surrounding context for a match."""
        context_start = max(0, start - window)
        context_end = min(len(text), end + window)
        return text[context_start:context_end].strip()

    def update_known_terms(self, terms: Set[str]) -> None:
        """Update the set of known terms."""
        self._known_terms = terms
