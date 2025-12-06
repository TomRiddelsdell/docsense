from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class PromptContext:
    document_content: str = ""
    policy_rules: list[dict[str, Any]] = field(default_factory=list)
    section_focus: list[str] = field(default_factory=list)
    issue_data: dict[str, Any] | None = None
    extra_context: str = ""
    max_issues: int = 50
    include_suggestions: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "document_content": self.document_content,
            "policy_rules": self.policy_rules,
            "section_focus": self.section_focus,
            "issue_data": self.issue_data,
            "extra_context": self.extra_context,
            "max_issues": self.max_issues,
            "include_suggestions": self.include_suggestions,
        }


class PromptTemplate(ABC):
    
    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        pass

    @abstractmethod
    def render(self, context: PromptContext) -> str:
        pass

    @abstractmethod
    def get_system_prompt(self) -> str:
        pass

    def _format_rules(self, rules: list[dict[str, Any]]) -> str:
        if not rules:
            return "No specific policy rules provided."
        
        formatted = []
        for i, rule in enumerate(rules, 1):
            rule_text = f"{i}. {rule.get('name', 'Unnamed Rule')}"
            if rule.get('requirement_type'):
                rule_text += f" [{rule['requirement_type']}]"
            rule_text += f"\n   Description: {rule.get('description', 'No description')}"
            if rule.get('validation_criteria'):
                rule_text += f"\n   Criteria: {rule['validation_criteria']}"
            formatted.append(rule_text)
        
        return "\n".join(formatted)

    def _truncate_content(self, content: str, max_chars: int = 50000) -> str:
        if len(content) <= max_chars:
            return content
        
        half = max_chars // 2
        return (
            content[:half] +
            "\n\n... [Content truncated for length] ...\n\n" +
            content[-half:]
        )
