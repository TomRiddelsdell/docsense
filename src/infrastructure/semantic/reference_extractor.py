"""Cross-reference extraction from document content."""

import re
import uuid
from typing import List, Dict, Any

from src.domain.value_objects.semantic_ir import (
    CrossReference,
    IRSection,
    TermDefinition,
    FormulaReference,
    TableData,
)


class ReferenceExtractor:
    """Extract cross-references from document content."""

    def extract(
        self,
        markdown: str,
        sections: List[IRSection],
        definitions: List[TermDefinition],
        formulae: List[FormulaReference],
        tables: List[TableData],
    ) -> List[CrossReference]:
        """
        Extract cross-references between document entities.

        Args:
            markdown: Markdown content
            sections: Document sections
            definitions: Term definitions
            formulae: Formula references
            tables: Tables

        Returns:
            List of CrossReference objects
        """
        references = []
        ref_counter = 1

        # Build entity maps
        entity_map = self._build_entity_map(sections, definitions, formulae, tables)

        # Find references in text
        # Pattern: "see Section X", "as defined in Y", "Table Z shows", etc.
        patterns = [
            (r'(?:see|refer to|as in)\s+(Section\s+\d+(?:\.\d+)*)', 'section'),
            (r'(?:Table|table)\s+(\d+(?:\.\d+)*)', 'table'),
            (r'(?:Formula|formula|equation)\s+(\d+)', 'formula'),
            (r'as\s+defined\s+in\s+"([^"]+)"', 'definition'),
            (r'(?:Annex|Appendix)\s+([A-Z])', 'section'),
        ]

        for pattern, ref_type in patterns:
            for match in re.finditer(pattern, markdown, re.IGNORECASE):
                reference_text = match.group(0)
                target_identifier = match.group(1)

                # Try to resolve the target
                target_id = self._resolve_target(
                    target_identifier, ref_type, entity_map
                )

                if target_id:
                    # Find source context (which section contains this reference)
                    line_number = markdown[: match.start()].count('\n') + 1
                    source_section = self._find_section_by_line(line_number, sections)

                    if source_section:
                        ref_id = f"ref-{ref_counter}"
                        references.append(
                            CrossReference(
                                id=ref_id,
                                source_id=source_section.id,
                                source_type='section',
                                target_id=target_id,
                                target_type=ref_type,
                                reference_text=reference_text,
                                resolved=True,
                            )
                        )
                        ref_counter += 1

        return references

    def _build_entity_map(
        self,
        sections: List[IRSection],
        definitions: List[TermDefinition],
        formulae: List[FormulaReference],
        tables: List[TableData],
    ) -> Dict[str, Dict[str, Any]]:
        """Build a map of all entities for reference resolution."""
        entity_map = {
            'section': {},
            'definition': {},
            'formula': {},
            'table': {},
        }

        # Map sections by title patterns
        for section in sections:
            # Extract section numbers if present
            match = re.match(r'(\d+(?:\.\d+)*)', section.title)
            if match:
                entity_map['section'][match.group(1)] = section.id

        # Map definitions by term
        for definition in definitions:
            entity_map['definition'][definition.term.lower()] = definition.id

        # Map formulas by ID
        for idx, formula in enumerate(formulae, 1):
            entity_map['formula'][str(idx)] = formula.id
            if formula.name:
                entity_map['formula'][formula.name.lower()] = formula.id

        # Map tables by ID
        for idx, table in enumerate(tables, 1):
            entity_map['table'][str(idx)] = table.id

        return entity_map

    def _resolve_target(
        self, identifier: str, ref_type: str, entity_map: Dict[str, Dict[str, Any]]
    ) -> str | None:
        """Resolve a reference identifier to an entity ID."""
        if ref_type not in entity_map:
            return None

        identifier_lower = identifier.lower()
        type_map = entity_map[ref_type]

        # Try exact match first
        if identifier in type_map:
            return type_map[identifier]

        # Try lowercase match
        if identifier_lower in type_map:
            return type_map[identifier_lower]

        return None

    def _find_section_by_line(
        self, line_number: int, sections: List[IRSection]
    ) -> IRSection | None:
        """Find which section contains a given line number."""
        for section in sections:
            if section.contains_line(line_number):
                return section
        return None
