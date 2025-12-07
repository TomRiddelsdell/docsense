from .base import PromptTemplate, PromptContext


class PolicyCompliancePrompt(PromptTemplate):
    
    @property
    def name(self) -> str:
        return "policy_compliance"

    @property
    def description(self) -> str:
        return "Evaluates document compliance against specific regulatory and internal policies with self-containment verification"

    def get_system_prompt(self) -> str:
        return """You are a regulatory compliance expert specializing in trading algorithm documentation.
Your expertise includes:
- SEC regulations for algorithmic trading
- FINRA rules and requirements
- MiFID II compliance standards
- Internal policy adherence
- Risk management documentation requirements
- Index methodology documentation standards

CRITICAL REQUIREMENT - DOCUMENT SELF-CONTAINMENT:
For compliance purposes, documents MUST be fully self-contained. An independent third party with access ONLY to the provided documents must be able to:
1. Fully implement the trading strategy or index methodology
2. Calculate the EXACT same index level as the original authors
3. Understand all data sources, formulas, parameters, and governance procedures
4. Execute all rebalancing, corporate action handling, and exception processes

COMPLIANCE DEPENDS ON COMPLETENESS:
A document that references external sources not included in the submission is automatically NON-COMPLIANT for:
- Reproducibility requirements
- Implementation requirements
- Audit trail requirements

Your role is to perform a thorough compliance check of trading algorithm documents against specific policy rules.
For each rule, determine:
- COMPLIANT: The document fully satisfies the requirement with all information self-contained
- PARTIAL: The document partially addresses the requirement but needs improvement or has external dependencies
- NON_COMPLIANT: The document fails to meet the requirement or relies on missing external references
- NOT_APPLICABLE: The rule does not apply to this document

ZERO TOLERANCE FOR ASSUMPTIONS:
- If external documents are referenced but not included, mark as NON_COMPLIANT
- If parameters or formulas require industry knowledge to interpret, mark as PARTIAL or NON_COMPLIANT
- If any calculation cannot be reproduced from the document alone, this is a compliance failure

Be precise and cite specific sections of the document as evidence for your assessments."""

    def render(self, context: PromptContext) -> str:
        rules_text = self._format_rules(context.policy_rules)
        content = self._truncate_content(context.document_content)
        
        extra_context_text = ""
        if context.extra_context:
            extra_context_text = f"\n\nADDITIONAL CONTEXT:\n{context.extra_context}"

        return f"""Perform a detailed compliance assessment of this trading algorithm document against the specified policy rules.

CRITICAL SELF-CONTAINMENT REQUIREMENT:
Before evaluating specific rules, verify that the document is FULLY SELF-CONTAINED:
- All referenced documents, appendices, and data sources must be included
- An independent person must be able to implement the strategy using ONLY this documentation
- Index calculations must be reproducible without external references
- Any external dependencies make the document NON-COMPLIANT for reproducibility rules

POLICY RULES TO EVALUATE:
{rules_text}
{extra_context_text}

DOCUMENT CONTENT:
---
{content}
---

COMPLIANCE ASSESSMENT REQUIREMENTS:
1. First, assess document self-containment (are there missing references?)
2. Evaluate the document against each policy rule
3. Assign a compliance status to each rule
4. Provide specific evidence from the document
5. Identify gaps and recommend remediation for non-compliant items
6. Prioritize findings by the rule's requirement type (MUST > SHOULD > MAY)
7. Flag any external document references that should be uploaded for complete review

Respond with a JSON object in this exact format:
{{
    "compliance_results": [
        {{
            "rule_id": "the_policy_rule_id",
            "rule_name": "The Policy Rule Name",
            "status": "compliant|partial|non_compliant|not_applicable",
            "evidence": "Specific text or section from document supporting this assessment",
            "location": "Section where evidence was found",
            "gaps": ["List of specific gaps if not fully compliant"],
            "missing_references": ["List of external documents/sources needed for this rule"],
            "remediation": "Recommended action to achieve compliance",
            "confidence": 0.9
        }}
    ],
    "self_containment_assessment": {{
        "is_self_contained": false,
        "missing_documents": ["List of referenced but missing documents"],
        "undefined_data_sources": ["List of data sources without full specification"],
        "external_dependencies": ["List of external systems or resources required"],
        "can_reproduce_calculations": false,
        "assessment_summary": "Summary of self-containment issues"
    }},
    "overall_compliance_score": 0.75,
    "critical_gaps": ["List of most important compliance gaps"],
    "documents_to_upload": ["List of documents that should be uploaded for complete review"],
    "summary": "Executive summary of compliance status, self-containment issues, and key recommendations"
}}"""
