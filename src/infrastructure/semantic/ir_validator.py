"""Validation service for semantic IR."""

import uuid
from typing import List, Set, Dict
from collections import defaultdict

from src.domain.value_objects.semantic_ir import (
    DocumentIR,
    ValidationIssue,
    ValidationSeverity,
    ValidationType,
)


class IRValidator:
    """Validate semantic IR and detect issues."""

    def validate(self, ir: DocumentIR) -> List[ValidationIssue]:
        """
        Run all validation checks on the IR.

        Args:
            ir: Document IR to validate

        Returns:
            List of validation issues found
        """
        issues = []
        issues.extend(self._check_duplicate_definitions(ir))
        issues.extend(self._check_undefined_variables(ir))
        issues.extend(self._check_circular_dependencies(ir))
        issues.extend(self._check_unresolved_references(ir))
        return issues

    def _check_duplicate_definitions(self, ir: DocumentIR) -> List[ValidationIssue]:
        """Check for duplicate term definitions."""
        issues = []
        term_map = defaultdict(list)

        # Group definitions by term (case-insensitive)
        for definition in ir.definitions:
            term_lower = definition.term.lower()
            term_map[term_lower].append(definition)

        # Report duplicates
        for term, definitions in term_map.items():
            if len(definitions) > 1:
                related_ids = [d.id for d in definitions]
                locations = ', '.join(d.section_id for d in definitions)

                issue = ValidationIssue(
                    id=f"val-{str(uuid.uuid4())[:8]}",
                    issue_type=ValidationType.DUPLICATE_DEFINITION,
                    severity=ValidationSeverity.WARNING,
                    message=f"Term '{definitions[0].term}' is defined multiple times",
                    location=locations,
                    related_ids=related_ids,
                    suggestion="Review definitions and merge or clarify distinctions",
                )
                issues.append(issue)

        return issues

    def _check_undefined_variables(self, ir: DocumentIR) -> List[ValidationIssue]:
        """Check for undefined variables in formulas."""
        issues = []

        # Get all defined terms
        defined_terms = ir.get_all_defined_terms_set()

        # Add formula names to defined terms
        for formula in ir.formulae:
            if formula.name:
                defined_terms.add(formula.name.lower())

        # Check each formula for undefined variables
        for formula in ir.formulae:
            undefined = formula.get_undefined_variables(defined_terms)

            if undefined:
                issue = ValidationIssue(
                    id=f"val-{str(uuid.uuid4())[:8]}",
                    issue_type=ValidationType.UNDEFINED_VARIABLE,
                    severity=ValidationSeverity.WARNING,
                    message=f"Formula {formula.id} contains undefined variables: {', '.join(undefined)}",
                    location=formula.section_id,
                    related_ids=[formula.id],
                    suggestion="Define these variables or add them to the glossary",
                )
                issues.append(issue)

        return issues

    def _check_circular_dependencies(self, ir: DocumentIR) -> List[ValidationIssue]:
        """Check for circular dependencies in formulas."""
        issues = []

        # Build dependency graph
        graph = {f.id: f.dependencies for f in ir.formulae}

        # Check each formula for circular dependencies using DFS
        for formula in ir.formulae:
            if self._has_circular_dependency(formula.id, graph, set()):
                issue = ValidationIssue(
                    id=f"val-{str(uuid.uuid4())[:8]}",
                    issue_type=ValidationType.CIRCULAR_DEPENDENCY,
                    severity=ValidationSeverity.ERROR,
                    message=f"Formula {formula.id} has circular dependencies",
                    location=formula.section_id,
                    related_ids=[formula.id] + formula.dependencies,
                    suggestion="Review formula dependencies and remove circular references",
                )
                issues.append(issue)

        return issues

    def _has_circular_dependency(
        self, node: str, graph: Dict[str, List[str]], visited: Set[str], path: Set[str] = None
    ) -> bool:
        """
        Check if a node has circular dependencies using DFS.

        Args:
            node: Current node to check
            graph: Dependency graph
            visited: Set of visited nodes
            path: Current path being explored

        Returns:
            True if circular dependency found
        """
        if path is None:
            path = set()

        if node in path:
            return True  # Circular dependency detected

        if node in visited:
            return False  # Already checked this node

        visited.add(node)
        path.add(node)

        # Check dependencies
        if node in graph:
            for dep in graph[node]:
                if dep in graph:  # Only check formula dependencies
                    if self._has_circular_dependency(dep, graph, visited, path):
                        return True

        path.remove(node)
        return False

    def _check_unresolved_references(self, ir: DocumentIR) -> List[ValidationIssue]:
        """Check for unresolved cross-references."""
        issues = []

        for ref in ir.cross_references:
            if not ref.resolved:
                issue = ValidationIssue(
                    id=f"val-{str(uuid.uuid4())[:8]}",
                    issue_type=ValidationType.MISSING_REFERENCE,
                    severity=ValidationSeverity.WARNING,
                    message=f"Reference to {ref.target_type} '{ref.reference_text}' could not be resolved",
                    location=ref.source_id,
                    related_ids=[ref.id],
                    suggestion=f"Check if the referenced {ref.target_type} exists",
                )
                issues.append(issue)

        return issues
