"""AI-powered semantic IR curation and enhancement."""

import json
import logging
from typing import List, Dict, Any, Optional
import uuid

from src.domain.value_objects.semantic_ir import (
    DocumentIR,
    TermDefinition,
    TermLineage,
    TermDependency,
    Parameter,
    DependencyType,
)
from src.infrastructure.ai.provider_factory import ProviderFactory
from .lineage_extractor import LineageExtractor

logger = logging.getLogger(__name__)


class SemanticIRCurator:
    """
    Uses AI to enhance and validate semantic IR extraction.

    This curator works in conjunction with rule-based extractors to:
    1. Find missed definitions that don't match common patterns
    2. Validate extracted definitions for correctness
    3. Suggest corrections for malformed extractions
    4. Identify new definition patterns to improve rules
    """

    def __init__(self, provider_factory: Optional[ProviderFactory] = None):
        """Initialize curator with AI provider."""
        self._provider_factory = provider_factory or ProviderFactory()
        self._max_definitions_per_call = 50  # Batch size for API calls
        self._lineage_extractor = LineageExtractor()

    async def curate(
        self,
        ir: DocumentIR,
        markdown: str,
        provider_type: str = "claude"
    ) -> DocumentIR:
        """
        AI-enhance the semantic IR.

        Args:
            ir: Initial semantic IR from rule-based extraction
            markdown: Full markdown content
            provider_type: AI provider to use (claude, gemini, openai)

        Returns:
            Enhanced DocumentIR with AI improvements
        """
        try:
            logger.info(f"Starting AI curation for document {ir.document_id}")

            # Run AI tasks
            missed_definitions = await self._find_missed_definitions(
                markdown, ir, provider_type
            )
            validation_results = await self._validate_definitions(
                ir.definitions[:self._max_definitions_per_call],  # Limit batch size
                markdown,
                provider_type
            )

            # Merge enhancements
            enhanced_ir = self._merge_enhancements(
                ir,
                missed_definitions,
                validation_results
            )

            logger.info(
                f"AI curation complete: added {len(missed_definitions)} definitions, "
                f"validated {len(validation_results)} existing definitions"
            )

            return enhanced_ir

        except Exception as e:
            logger.error(f"AI curation failed: {e}", exc_info=True)
            # Return original IR if curation fails
            return ir

    async def _find_missed_definitions(
        self,
        markdown: str,
        existing_ir: DocumentIR,
        provider_type: str
    ) -> List[TermDefinition]:
        """
        Use AI to find definitions missed by rule-based extraction.

        Args:
            markdown: Document markdown content
            existing_ir: Existing IR with rule-based definitions
            provider_type: AI provider to use

        Returns:
            List of newly discovered term definitions
        """
        try:
            provider = self._provider_factory.get_provider(provider_type)

            # Build list of already-found terms
            existing_terms = [d.term for d in existing_ir.definitions]

            # Create focused markdown sample (first 10k chars to stay within limits)
            sample_markdown = markdown[:10000] if len(markdown) > 10000 else markdown

            prompt = f"""Analyze this document excerpt and identify defined terms that may have been missed.

ALREADY FOUND TERMS (do not repeat these):
{json.dumps(existing_terms[:20], indent=2)}

DOCUMENT EXCERPT:
{sample_markdown}

Look for definitions using varied patterns:
- "X is defined to mean Y"
- "X (hereinafter 'Y')"
- "X, meaning Y"
- "For purposes of this document, X means Y"
- Acronyms: "Something Something (SS)"
- Contextual definitions where meaning is clear

Return ONLY a JSON array of objects with this structure:
[
  {{"term": "exact term", "definition": "complete definition", "confidence": "high|medium|low"}}
]

Focus on:
1. Financial/legal terms specific to this document
2. Acronyms and abbreviations
3. Terms with clear, explicit definitions

Return empty array [] if no additional terms found.
"""

            response = await provider.generate_text(prompt, max_tokens=2000)

            # Parse JSON response
            definitions = self._parse_definition_json(response)

            # Convert to TermDefinition objects with lineage
            term_definitions = []
            all_known_terms = {d.term for d in existing_ir.definitions}

            for d in definitions:
                if d.get("confidence") in ["high", "medium"]:  # Skip low confidence
                    # Extract lineage for this definition
                    lineage = self._lineage_extractor.extract_lineage(
                        d["definition"],
                        all_known_terms
                    )

                    term_def = TermDefinition(
                        id=f"ai-def-{str(uuid.uuid4())[:8]}",
                        term=d["term"],
                        definition=d["definition"],
                        section_id="ai-discovered",
                        aliases=[],
                        first_occurrence_line=0,
                        lineage=lineage,
                    )
                    term_definitions.append(term_def)

            logger.info(f"AI found {len(term_definitions)} additional definitions")
            return term_definitions

        except Exception as e:
            logger.error(f"Error finding missed definitions: {e}", exc_info=True)
            return []

    async def _validate_definitions(
        self,
        definitions: List[TermDefinition],
        markdown: str,
        provider_type: str
    ) -> List[Dict[str, Any]]:
        """
        Use AI to validate extracted definitions.

        Args:
            definitions: List of definitions to validate
            markdown: Document markdown content
            provider_type: AI provider to use

        Returns:
            List of validation results with suggested fixes
        """
        try:
            if not definitions:
                return []

            provider = self._provider_factory.get_provider(provider_type)

            # Prepare definitions for review
            defs_for_review = [
                {"term": d.term, "definition": d.definition[:200]}  # Truncate long defs
                for d in definitions[:20]  # Limit batch
            ]

            prompt = f"""Review these extracted term definitions for quality issues.

DEFINITIONS TO REVIEW:
{json.dumps(defs_for_review, indent=2)}

For each definition, check if:
1. The TERM is reasonable (not a sentence fragment or partial phrase)
2. The DEFINITION is complete (not cut off mid-sentence)
3. The term-definition pairing makes logical sense
4. The term doesn't start with common words like "means", "refers to", etc.

Return ONLY a JSON array of issues found:
[
  {{
    "term": "exact term with issue",
    "issue_type": "invalid_term|incomplete_definition|mismatched_pair",
    "severity": "high|medium|low",
    "description": "brief explanation",
    "suggested_fix": "corrected term or null"
  }}
]

Return empty array [] if all definitions look good.
"""

            response = await provider.generate_text(prompt, max_tokens=1500)

            # Parse validation results
            issues = self._parse_validation_json(response)

            logger.info(f"AI validation found {len(issues)} issues")
            return issues

        except Exception as e:
            logger.error(f"Error validating definitions: {e}", exc_info=True)
            return []

    def _merge_enhancements(
        self,
        ir: DocumentIR,
        missed_definitions: List[TermDefinition],
        validation_results: List[Dict[str, Any]]
    ) -> DocumentIR:
        """
        Merge AI enhancements into the original IR.

        Args:
            ir: Original semantic IR
            missed_definitions: New definitions found by AI
            validation_results: Validation issues found

        Returns:
            Enhanced DocumentIR
        """
        # Add missed definitions
        enhanced_definitions = list(ir.definitions)
        enhanced_definitions.extend(missed_definitions)

        # Remove invalid definitions based on validation
        high_severity_issues = [
            v for v in validation_results
            if v.get("severity") == "high"
        ]

        invalid_terms = {issue["term"] for issue in high_severity_issues}
        enhanced_definitions = [
            d for d in enhanced_definitions
            if d.term not in invalid_terms
        ]

        # Create enhanced IR
        enhanced_ir = DocumentIR(
            document_id=ir.document_id,
            title=ir.title,
            original_format=ir.original_format,
            sections=ir.sections,
            definitions=enhanced_definitions,
            formulae=ir.formulae,
            tables=ir.tables,
            cross_references=ir.cross_references,
            validation_issues=ir.validation_issues,
            metadata=ir.metadata,
            raw_markdown=ir.raw_markdown,
        )

        return enhanced_ir

    def _parse_definition_json(self, response: str) -> List[Dict[str, Any]]:
        """Parse AI response containing definition JSON."""
        try:
            # Try to extract JSON from response
            if '[' in response and ']' in response:
                start = response.find('[')
                end = response.rfind(']') + 1
                json_str = response[start:end]
                return json.loads(json_str)
            return []
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse definition JSON: {e}")
            return []

    def _parse_validation_json(self, response: str) -> List[Dict[str, Any]]:
        """Parse AI response containing validation JSON."""
        try:
            # Try to extract JSON from response
            if '[' in response and ']' in response:
                start = response.find('[')
                end = response.rfind(']') + 1
                json_str = response[start:end]
                return json.loads(json_str)
            return []
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse validation JSON: {e}")
            return []
