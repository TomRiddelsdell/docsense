from .base import PromptTemplate, PromptContext


class DocumentAnalysisPrompt(PromptTemplate):
    
    @property
    def name(self) -> str:
        return "document_analysis"

    @property
    def description(self) -> str:
        return "Analyzes trading algorithm documentation for quality, clarity, and completeness"

    def get_system_prompt(self) -> str:
        return """You are an expert trading algorithm documentation analyst with deep expertise in:
- Financial regulations and compliance requirements
- Technical documentation best practices
- Algorithm design and risk management
- Clear, actionable feedback generation

Your role is to analyze trading algorithm documents and identify issues related to:
1. Clarity and completeness of algorithm descriptions
2. Risk disclosure and management procedures
3. Technical accuracy and consistency
4. Compliance with regulatory requirements
5. Documentation quality and readability

Always provide specific, actionable feedback with clear locations in the document.
Prioritize issues by severity: critical issues first, then high, medium, low, and informational."""

    def render(self, context: PromptContext) -> str:
        rules_text = self._format_rules(context.policy_rules)
        content = self._truncate_content(context.document_content)
        
        section_focus_text = ""
        if context.section_focus:
            section_focus_text = f"\n\nFOCUS SECTIONS:\nPrioritize analysis of these sections: {', '.join(context.section_focus)}"
        
        extra_context_text = ""
        if context.extra_context:
            extra_context_text = f"\n\nADDITIONAL CONTEXT:\n{context.extra_context}"

        return f"""Analyze the following trading algorithm documentation for quality, completeness, and compliance issues.

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
   - Confidence score (0.0-1.0) in your assessment
{"3. For each issue, also provide a suggested fix with explanation" if context.include_suggestions else ""}

Respond with a JSON object in this exact format:
{{
    "issues": [
        {{
            "rule_id": "policy_rule_id_or_general",
            "severity": "critical|high|medium|low|info",
            "title": "Concise issue title",
            "description": "Detailed explanation of the issue",
            "location": "Section name or line reference",
            "original_text": "The exact problematic text",
            "confidence": 0.85
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
    "summary": "Overall assessment of the document quality and main areas for improvement"
}}"""
