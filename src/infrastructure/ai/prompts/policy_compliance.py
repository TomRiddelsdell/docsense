from .base import PromptTemplate, PromptContext


class PolicyCompliancePrompt(PromptTemplate):
    
    @property
    def name(self) -> str:
        return "policy_compliance"

    @property
    def description(self) -> str:
        return "Evaluates document compliance against specific regulatory and internal policies"

    def get_system_prompt(self) -> str:
        return """You are a regulatory compliance expert specializing in trading algorithm documentation.
Your expertise includes:
- SEC regulations for algorithmic trading
- FINRA rules and requirements
- MiFID II compliance standards
- Internal policy adherence
- Risk management documentation requirements

Your role is to perform a thorough compliance check of trading algorithm documents against specific policy rules.
For each rule, determine:
- COMPLIANT: The document fully satisfies the requirement
- PARTIAL: The document partially addresses the requirement but needs improvement
- NON_COMPLIANT: The document fails to meet the requirement
- NOT_APPLICABLE: The rule does not apply to this document

Be precise and cite specific sections of the document as evidence for your assessments."""

    def render(self, context: PromptContext) -> str:
        rules_text = self._format_rules(context.policy_rules)
        content = self._truncate_content(context.document_content)
        
        extra_context_text = ""
        if context.extra_context:
            extra_context_text = f"\n\nADDITIONAL CONTEXT:\n{context.extra_context}"

        return f"""Perform a detailed compliance assessment of this trading algorithm document against the specified policy rules.

POLICY RULES TO EVALUATE:
{rules_text}
{extra_context_text}

DOCUMENT CONTENT:
---
{content}
---

COMPLIANCE ASSESSMENT REQUIREMENTS:
1. Evaluate the document against each policy rule
2. Assign a compliance status to each rule
3. Provide specific evidence from the document
4. Identify gaps and recommend remediation for non-compliant items
5. Prioritize findings by the rule's requirement type (MUST > SHOULD > MAY)

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
            "remediation": "Recommended action to achieve compliance",
            "confidence": 0.9
        }}
    ],
    "overall_compliance_score": 0.75,
    "critical_gaps": ["List of most important compliance gaps"],
    "summary": "Executive summary of compliance status and key recommendations"
}}"""
