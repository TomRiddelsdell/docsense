from .base import PromptTemplate, PromptContext


class SuggestionGenerationPrompt(PromptTemplate):
    
    @property
    def name(self) -> str:
        return "suggestion_generation"

    @property
    def description(self) -> str:
        return "Generates specific suggestions to fix identified documentation issues"

    def get_system_prompt(self) -> str:
        return """You are an expert technical writer specializing in trading algorithm documentation.
Your expertise includes:
- Clear, precise financial writing
- Regulatory compliance language
- Technical accuracy in algorithm descriptions
- Risk disclosure best practices

Your role is to generate specific, actionable text corrections that:
1. Address the identified issue completely
2. Maintain consistency with the document's style and tone
3. Ensure regulatory compliance where applicable
4. Improve clarity and readability
5. Are ready to be applied as-is (no placeholders or TODOs)

Always provide complete replacement text, not just suggestions for changes."""

    def render(self, context: PromptContext) -> str:
        if not context.issue_data:
            raise ValueError("issue_data is required for suggestion generation")
        
        issue = context.issue_data
        content = self._truncate_content(context.document_content, max_chars=10000)
        
        rule_text = ""
        if context.policy_rules:
            rule = context.policy_rules[0] if context.policy_rules else {}
            rule_text = f"""
APPLICABLE POLICY RULE:
Name: {rule.get('name', 'N/A')}
Description: {rule.get('description', 'N/A')}
Requirement Type: {rule.get('requirement_type', 'N/A')}
Validation Criteria: {rule.get('validation_criteria', 'N/A')}
Examples: {', '.join(rule.get('examples', []))}"""

        extra_context_text = ""
        if context.extra_context:
            extra_context_text = f"\n\nADDITIONAL CONTEXT:\n{context.extra_context}"

        return f"""Generate a specific text correction to fix the following issue in a trading algorithm document.

ISSUE DETAILS:
Title: {issue.get('title', 'Unknown')}
Severity: {issue.get('severity', 'medium')}
Description: {issue.get('description', 'No description')}
Location: {issue.get('location', 'Unknown')}
Original Text: {issue.get('original_text', 'No text provided')}
{rule_text}
{extra_context_text}

SURROUNDING DOCUMENT CONTEXT:
---
{content}
---

SUGGESTION REQUIREMENTS:
1. Provide complete replacement text that can be applied directly
2. Ensure the suggestion fully addresses the issue
3. Match the document's existing style and tone
4. If compliance-related, use appropriate regulatory language
5. Be specific and actionable - no placeholders or vague recommendations

Respond with a JSON object in this exact format:
{{
    "suggested_text": "The complete corrected text that should replace the original",
    "explanation": "Detailed explanation of what was changed and why",
    "changes_made": [
        "Specific change 1",
        "Specific change 2"
    ],
    "compliance_improvement": "How this change improves compliance (if applicable)",
    "confidence": 0.85
}}"""
