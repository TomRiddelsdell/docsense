"""Definition extraction from document text."""

import re
import uuid
from typing import List, Set, Optional

from src.domain.value_objects.semantic_ir import TermDefinition
from .lineage_extractor import LineageExtractor


class DefinitionExtractor:
    """Extract term definitions from document content."""

    def __init__(self):
        """Initialize definition extractor with lineage extractor."""
        self._lineage_extractor = LineageExtractor()

    # Patterns for common definition formats in trading documentation
    PATTERNS = [
        # "Term" means definition - stop at next quoted term or paragraph break
        (r'"([^"]+)"\s+means\s+(.+?)(?=\s*"[^"]+"\s+(?:means|refers to|shall mean|is defined as)|\n\n|$)', re.MULTILINE | re.DOTALL),
        # "Term" refers to definition - stop at next quoted term or paragraph break
        (
            r'"([^"]+)"\s+(?:refers to|shall mean|is defined as)\s+(.+?)(?=\s*"[^"]+"\s+(?:means|refers to|shall mean|is defined as)|\n\n|$)',
            re.MULTILINE | re.DOTALL,
        ),
        # Term: definition (glossary style) - must be all caps or Title Case, not sentence case
        (r'^([A-Z][A-Z\s]{2,40}|[A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,5}):\s*(.+?)(?=\n\n|\n[A-Z]|$)', re.MULTILINE),
        # Term – definition (em-dash or en-dash only, not hyphen)
        (
            r'^([A-Z][A-Z\s]{2,40}|[A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,5})\s*[–—]\s*(.+?)(?=\n\n|\n[A-Z]|$)',
            re.MULTILINE,
        ),
        # **Term**: definition (markdown bold)
        (r'\*\*([^*]+)\*\*:\s*(.+?)(?=\n\n|\n\*\*|$)', re.MULTILINE),
    ]

    def extract(self, content: str, section_id: str) -> List[TermDefinition]:
        """
        Extract term definitions from content.

        Args:
            content: Text content to extract definitions from
            section_id: ID of the section containing this content

        Returns:
            List of extracted TermDefinition objects with lineage
        """
        # First pass: extract all definitions without lineage
        definitions = []
        seen_terms = set()

        for pattern, flags in self.PATTERNS:
            for match in re.finditer(pattern, content, flags):
                term = match.group(1).strip()
                definition = match.group(2).strip()

                # Skip if term is too short or already seen
                if len(term) < 2 or term.lower() in seen_terms:
                    continue

                # Skip obvious false positives
                if not self._is_valid_term(term):
                    continue

                # Clean up the definition
                definition = self._clean_definition(definition)

                # Skip if definition is too short
                if len(definition) < 10:
                    continue

                # Extract aliases from the definition
                aliases = self._extract_aliases(definition)

                # Find line number (approximate)
                lines_before = content[: match.start()].count("\n")

                definition_id = f"def-{str(uuid.uuid4())[:8]}"
                definitions.append(
                    TermDefinition(
                        id=definition_id,
                        term=term,
                        definition=definition,
                        section_id=section_id,
                        aliases=aliases,
                        first_occurrence_line=lines_before + 1,
                        lineage=None,  # Will be added in second pass
                    )
                )

                seen_terms.add(term.lower())

        # Second pass: extract lineage now that we know all terms
        all_term_names = {d.term for d in definitions}
        self._lineage_extractor.update_known_terms(all_term_names)

        # Create new list with lineage
        definitions_with_lineage = []
        for term_def in definitions:
            lineage = self._lineage_extractor.extract_lineage(
                term_def.definition,
                all_term_names
            )

            # Create new TermDefinition with lineage (frozen dataclass)
            definitions_with_lineage.append(
                TermDefinition(
                    id=term_def.id,
                    term=term_def.term,
                    definition=term_def.definition,
                    section_id=term_def.section_id,
                    aliases=term_def.aliases,
                    first_occurrence_line=term_def.first_occurrence_line,
                    lineage=lineage,
                )
            )

        return definitions_with_lineage

    def _is_valid_term(self, term: str) -> bool:
        """
        Validate that a term is likely to be a real definition term.

        Args:
            term: Term to validate

        Returns:
            True if term appears to be valid, False otherwise
        """
        # Reject common sentence starters that aren't definitions
        invalid_starters = [
            'if', 'when', 'where', 'the', 'a', 'an', 'this', 'that',
            'these', 'those', 'it', 'as', 'for', 'and', 'or', 'but',
            'in', 'on', 'at', 'to', 'from', 'with', 'by', 'of'
        ]

        first_word = term.split()[0].lower()
        if first_word in invalid_starters:
            return False

        # Reject if it ends with common non-definition endings
        if term.lower().endswith((' non', ' a', ' the', ' of', ' to', ' and', ' or')):
            return False

        # Reject very short terms unless they're all caps (likely acronyms)
        if len(term) < 3 and not term.isupper():
            return False

        # Reject if contains too many common words (likely a sentence fragment)
        words = term.lower().split()
        common_words = {'the', 'a', 'an', 'of', 'to', 'in', 'on', 'at', 'for', 'with', 'by', 'as', 'is', 'are', 'be', 'may', 'will'}
        common_count = sum(1 for w in words if w in common_words)
        if len(words) > 2 and common_count / len(words) > 0.5:
            return False

        return True

    def _clean_definition(self, text: str) -> str:
        """
        Clean up extracted definition text.

        Args:
            text: Raw definition text

        Returns:
            Cleaned definition text
        """
        # Collapse multiple spaces/newlines
        text = re.sub(r'\s+', ' ', text).strip()

        # Remove trailing punctuation artifacts (but keep meaningful punctuation)
        text = re.sub(r'\s*\.\s*$', '', text)

        # Limit length to avoid capturing too much
        if len(text) > 500:
            # Try to cut at sentence boundary
            sentences = text[:500].split('. ')
            if len(sentences) > 1:
                text = '. '.join(sentences[:-1]) + '.'
            else:
                text = text[:500] + '...'

        return text

    def _extract_aliases(self, definition: str) -> List[str]:
        """
        Extract aliases mentioned in the definition.

        Args:
            definition: Definition text to extract aliases from

        Returns:
            List of alias strings
        """
        aliases = []

        # Pattern: "also known as X" or "also referred to as X"
        alias_patterns = [
            r'also (?:known|referred to) as ["\']?([^"\',.;]+)["\']?',
            r'\((?:the\s+)?["\']([^"\']+)["\']\)',  # (the "Alias")
            r'\(([A-Z][A-Za-z0-9]+)\)',  # (Alias) - acronym style
        ]

        for pattern in alias_patterns:
            for match in re.finditer(pattern, definition, re.IGNORECASE):
                alias = match.group(1).strip()
                if 1 < len(alias) < 50 and alias not in aliases:
                    aliases.append(alias)

        return aliases

    def merge_definitions(
        self, definitions: List[TermDefinition]
    ) -> List[TermDefinition]:
        """
        Merge duplicate definitions, keeping the most complete one.

        Args:
            definitions: List of definitions to merge

        Returns:
            List of unique definitions
        """
        term_map = {}

        for definition in definitions:
            key = definition.term.lower()

            if key not in term_map:
                term_map[key] = definition
            else:
                # Keep the one with the longer definition
                existing = term_map[key]
                if len(definition.definition) > len(existing.definition):
                    term_map[key] = definition

        return list(term_map.values())
