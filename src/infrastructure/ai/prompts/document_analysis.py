from .base import PromptTemplate, PromptContext


class DocumentAnalysisPrompt(PromptTemplate):
    
    @property
    def name(self) -> str:
        return "document_analysis"

    @property
    def description(self) -> str:
        return "Analyzes trading algorithm documentation for quality, clarity, completeness, and self-containment"

    def get_system_prompt(self) -> str:
        return """You are an expert trading algorithm documentation analyst with deep expertise in:
- Financial regulations and compliance requirements
- Technical documentation best practices
- Algorithm design and risk management
- Index calculation methodology
- Clear, actionable feedback generation

CRITICAL REQUIREMENT - SELF-CONTAINMENT:
Documents (or document groups) MUST be fully self-contained. An independent person with access ONLY to the uploaded documents must be able to:
1. Fully understand and implement the trading strategy without ANY external references
2. Calculate the EXACT same index level as the original authors
3. Execute all trading decisions, rebalancing, and governance procedures
4. Access ALL data sources, formulas, parameters, and thresholds

Your role is to analyze trading algorithm documents and identify issues related to:
1. COMPLETENESS - Are all referenced documents, appendices, and data sources included?
2. IMPLEMENTABILITY - Can the strategy be fully implemented from this documentation alone?
3. REPRODUCIBILITY - Can index levels be calculated exactly as intended?
4. CLARITY - Are all parameters, thresholds, and decision criteria explicitly defined?
5. ASSUMPTIONS - Are there ANY implicit assumptions that are not documented?
6. EXTERNAL DEPENDENCIES - Are there references to external documents, databases, or sources not included?
7. Regulatory compliance and risk disclosure

ZERO TOLERANCE FOR ASSUMPTIONS:
- Do NOT assume you know what any referenced external document contains
- Do NOT assume market conventions or industry standards are understood
- Do NOT assume any formula, parameter, or threshold has an "obvious" value
- Flag ANY gap that would require inference or assumption to fill

Always provide specific, actionable feedback with clear locations in the document.
Prioritize issues by severity: critical issues (blocking implementation) first, then high, medium, low, and informational."""

    def render(self, context: PromptContext) -> str:
        rules_text = self._format_rules(context.policy_rules)
        content = self._truncate_content(context.document_content)
        
        section_focus_text = ""
        if context.section_focus:
            section_focus_text = f"\n\nFOCUS SECTIONS:\nPrioritize analysis of these sections: {', '.join(context.section_focus)}"
        
        extra_context_text = ""
        if context.extra_context:
            extra_context_text = f"\n\nADDITIONAL CONTEXT:\n{context.extra_context}"

        return f"""Analyze the following trading algorithm documentation for quality, completeness, self-containment, and compliance issues.

CRITICAL SELF-CONTAINMENT CHECK:
The document(s) must be FULLY SELF-CONTAINED. An independent person should be able to:
- Implement the complete trading strategy using ONLY this documentation
- Calculate the EXACT index level without any external references
- Execute all governance and rebalancing procedures without assumptions

Flag as CRITICAL any issue that would prevent independent implementation or index calculation.

POLICY RULES TO CHECK:
{rules_text}
{section_focus_text}
{extra_context_text}

DOCUMENT CONTENT:
---
{content}
---

ANALYSIS REQUIREMENTS:
1. Identify up to {context.max_issues} issues, prioritized by severity
2. For each issue, provide:
   - A clear, specific title
   - Detailed description of the problem
   - Exact location in the document (section name or line reference)
   - The original problematic text
   - Issue category (see categories below)
   - Confidence score (0.0-1.0) in your assessment
{"3. For each issue, also provide a suggested fix with explanation" if context.include_suggestions else ""}

ISSUE CATEGORIES (use these for categorization):
- missing_reference: External document, appendix, or attachment referenced but not included
- undefined_parameter: Parameter, threshold, or value mentioned but not defined
- incomplete_formula: Formula or calculation missing components or specifications
- ambiguous_methodology: Process or methodology described but lacking implementation detail
- external_dependency: Reliance on external data source, vendor, or system not fully specified
- assumption_required: Information that requires inference or assumption to understand
- inconsistent_content: Conflicting information within or across documents
- missing_governance: Governance, control, or approval process not fully documented
- data_source_unspecified: Data feed, database, or source mentioned without full specification
- compliance_gap: Regulatory or policy compliance issue

Respond with a JSON object in this exact format:
{{
    "issues": [
        {{
            "rule_id": "policy_rule_id_or_general",
            "severity": "critical|high|medium|low|info",
            "category": "missing_reference|undefined_parameter|incomplete_formula|ambiguous_methodology|external_dependency|assumption_required|inconsistent_content|missing_governance|data_source_unspecified|compliance_gap",
            "title": "Concise issue title",
            "description": "Detailed explanation of the issue and why it blocks independent implementation",
            "location": "Section name or line reference",
            "original_text": "The exact problematic text",
            "confidence": 0.85
        }}
    ],
    "missing_documents": [
        {{
            "referenced_name": "Name of the referenced document/appendix",
            "reference_location": "Where in the document it is referenced",
            "purpose": "What information this document is expected to contain",
            "criticality": "critical|high|medium"
        }}
    ],
    "undefined_dependencies": [
        {{
            "dependency_name": "Name of external system, data feed, or resource",
            "dependency_type": "data_feed|external_system|vendor_service|database|api",
            "reference_location": "Where it is referenced",
            "missing_specifications": ["List of missing specs needed for implementation"]
        }}
    ],
    "implementation_gaps": [
        {{
            "gap_description": "What is missing for complete implementation",
            "affected_calculation": "Which index calculation or process is affected",
            "information_needed": "Specific information required to close this gap"
        }}
    ],
    "suggestions": [
        {{
            "issue_index": 0,
            "suggested_text": "The corrected text",
            "explanation": "Why this change improves the document",
            "confidence": 0.8
        }}
    ],
    "self_containment_score": 0.0,
    "implementability_assessment": {{
        "can_implement_strategy": true,
        "can_calculate_index": true,
        "blocking_issues_count": 0,
        "assessment_summary": "Summary of whether an independent person could fully implement this strategy"
    }},
    "summary": "Overall assessment of document quality, completeness, and self-containment"
}}"""
