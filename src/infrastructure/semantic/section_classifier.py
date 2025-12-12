"""Section type classification for semantic IR."""

import re
from typing import List

from src.infrastructure.converters.base import DocumentSection
from src.domain.value_objects.semantic_ir import IRSection, SectionType


class SectionClassifier:
    """Classify sections by their semantic type."""

    # Keywords for different section types
    DEFINITION_KEYWORDS = {'definition', 'glossary', 'terminology', 'terms'}
    FORMULA_KEYWORDS = {'formula', 'calculation', 'equation', 'computation'}
    TABLE_KEYWORDS = {'table', 'schedule', 'parameters', 'configuration'}
    ANNEX_KEYWORDS = {'annex', 'appendix', 'attachment', 'exhibit'}
    CODE_KEYWORDS = {'code', 'implementation', 'algorithm', 'pseudocode'}

    def classify_sections(self, sections: List[DocumentSection]) -> List[IRSection]:
        """
        Classify document sections by their semantic type.

        Args:
            sections: List of basic document sections

        Returns:
            List of IR sections with type classification
        """
        ir_sections = []

        for section in sections:
            section_type = self._classify_section(section)

            ir_section = IRSection(
                id=section.id,
                title=section.title,
                content=section.content,
                level=section.level,
                section_type=section_type,
                parent_id=None,  # Can be computed based on level hierarchy
                start_line=section.start_line,
                end_line=section.end_line,
            )
            ir_sections.append(ir_section)

        # Compute parent relationships
        self._compute_parent_relationships(ir_sections)

        return ir_sections

    def _classify_section(self, section: DocumentSection) -> SectionType:
        """
        Classify a single section by analyzing its title and content.

        Args:
            section: Document section to classify

        Returns:
            Classified SectionType
        """
        title_lower = section.title.lower()
        content_lower = section.content.lower()

        # Check title for keywords
        if any(kw in title_lower for kw in self.DEFINITION_KEYWORDS):
            return SectionType.DEFINITION

        if any(kw in title_lower for kw in self.GLOSSARY_KEYWORDS):
            return SectionType.GLOSSARY

        if any(kw in title_lower for kw in self.FORMULA_KEYWORDS):
            return SectionType.FORMULA

        if any(kw in title_lower for kw in self.TABLE_KEYWORDS):
            return SectionType.TABLE

        if any(kw in title_lower for kw in self.ANNEX_KEYWORDS):
            return SectionType.ANNEX

        if any(kw in title_lower for kw in self.CODE_KEYWORDS):
            return SectionType.CODE

        # Check content for LaTeX formulas
        if '$$' in section.content or re.search(r'\$[^$]+\$', section.content):
            if section.content.count('$$') >= 2:
                return SectionType.FORMULA

        # Check content for tables
        if '|' in section.content and section.content.count('|') > 10:
            return SectionType.TABLE

        # Check content for definitions
        if re.search(r'"[^"]+" (?:means|refers to|is defined as)', content_lower):
            return SectionType.DEFINITION

        # Default to narrative
        return SectionType.NARRATIVE

    @property
    def GLOSSARY_KEYWORDS(self):
        """Alias for definition keywords."""
        return self.DEFINITION_KEYWORDS

    def _compute_parent_relationships(self, sections: List[IRSection]) -> None:
        """
        Compute parent-child relationships based on section levels.

        Args:
            sections: List of IR sections to update (modified in place)
        """
        # Stack to track parent sections at each level
        parent_stack = []

        for i, section in enumerate(sections):
            # Pop parents that are not ancestors of current section
            while parent_stack and parent_stack[-1][0] >= section.level:
                parent_stack.pop()

            # Set parent ID if we have a parent
            if parent_stack:
                # Create new IRSection with parent_id set
                sections[i] = IRSection(
                    id=section.id,
                    title=section.title,
                    content=section.content,
                    level=section.level,
                    section_type=section.section_type,
                    parent_id=parent_stack[-1][1],  # Parent's ID
                    start_line=section.start_line,
                    end_line=section.end_line,
                )

            # Push current section as potential parent
            parent_stack.append((section.level, section.id))
