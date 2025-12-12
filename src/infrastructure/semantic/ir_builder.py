"""IR Builder to orchestrate semantic extraction."""

from typing import Dict, List

from src.infrastructure.converters.base import ConversionResult
from src.domain.value_objects.semantic_ir import DocumentIR

from .definition_extractor import DefinitionExtractor
from .formula_extractor import FormulaExtractor
from .table_extractor import TableExtractor
from .reference_extractor import ReferenceExtractor
from .section_classifier import SectionClassifier
from .ir_validator import IRValidator


class IRBuilder:
    """Orchestrates semantic extraction into DocumentIR."""

    def __init__(self):
        """Initialize extractors."""
        self.definition_extractor = DefinitionExtractor()
        self.formula_extractor = FormulaExtractor()
        self.table_extractor = TableExtractor()
        self.reference_extractor = ReferenceExtractor()
        self.section_classifier = SectionClassifier()
        self.validator = IRValidator()

    def build(self, conversion_result: ConversionResult, document_id: str) -> DocumentIR:
        """
        Build DocumentIR from conversion result.

        Args:
            conversion_result: Result from document conversion
            document_id: ID of the document

        Returns:
            Complete DocumentIR with semantic extraction
        """
        # 1. Classify sections
        ir_sections = self.section_classifier.classify_sections(conversion_result.sections)

        # 2. Build section-to-line mapping for lookup
        section_id_map = self._build_section_map(ir_sections)

        # 3. Extract definitions from each section
        definitions = []
        for section in ir_sections:
            section_defs = self.definition_extractor.extract(section.content, section.id)
            definitions.extend(section_defs)

        # Merge duplicate definitions
        definitions = self.definition_extractor.merge_definitions(definitions)

        # 4. Extract formulas from LaTeX blocks
        formulae = self.formula_extractor.extract_from_markdown(
            conversion_result.markdown_content, section_id_map
        )

        # 5. Extract tables
        tables = self.table_extractor.extract(
            conversion_result.markdown_content, section_id_map
        )

        # 6. Resolve formula dependencies
        formulae = self.formula_extractor.resolve_dependencies(formulae, definitions)

        # 7. Extract cross-references
        cross_refs = self.reference_extractor.extract(
            conversion_result.markdown_content, ir_sections, definitions, formulae, tables
        )

        # 8. Build IR
        ir = DocumentIR(
            document_id=document_id,
            title=conversion_result.metadata.title or "Untitled",
            original_format=conversion_result.metadata.original_format.value,
            sections=ir_sections,
            definitions=definitions,
            formulae=formulae,
            tables=tables,
            cross_references=cross_refs,
            metadata=self._extract_metadata_dict(conversion_result),
            raw_markdown=conversion_result.markdown_content,
        )

        # 9. Run validation
        ir.validation_issues = self.validator.validate(ir)

        return ir

    def _build_section_map(self, sections: List) -> Dict[int, str]:
        """
        Build a map from line numbers to section IDs.

        Args:
            sections: List of IR sections

        Returns:
            Dictionary mapping start line numbers to section IDs
        """
        section_map = {}
        for section in sections:
            if section.start_line is not None:
                section_map[section.start_line] = section.id
        return section_map

    def _extract_metadata_dict(self, conversion_result: ConversionResult) -> Dict:
        """
        Extract metadata as dictionary.

        Args:
            conversion_result: Conversion result containing metadata

        Returns:
            Metadata dictionary
        """
        metadata = conversion_result.metadata
        return {
            "title": metadata.title,
            "author": metadata.author,
            "created_date": metadata.created_date,
            "modified_date": metadata.modified_date,
            "page_count": metadata.page_count,
            "word_count": metadata.word_count,
            "original_format": metadata.original_format.value,
            "extra": metadata.extra,
        }
