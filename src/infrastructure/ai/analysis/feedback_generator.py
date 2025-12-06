from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from ..base import AIProvider, AnalysisOptions, Issue, PolicyRule, Suggestion


@dataclass
class FeedbackItem:
    id: UUID
    issue: Issue
    suggestion: Suggestion | None
    policy_rule: PolicyRule | None
    priority: int
    created_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": str(self.id),
            "issue": self.issue.to_dict(),
            "suggestion": self.suggestion.to_dict() if self.suggestion else None,
            "policy_rule": {
                "id": self.policy_rule.id,
                "name": self.policy_rule.name,
                "requirement_type": self.policy_rule.requirement_type,
            } if self.policy_rule else None,
            "priority": self.priority,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class FeedbackGenerationResult:
    success: bool
    feedback_items: list[FeedbackItem]
    summary: str
    processing_time_ms: int
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "feedback_items": [item.to_dict() for item in self.feedback_items],
            "summary": self.summary,
            "processing_time_ms": self.processing_time_ms,
            "errors": self.errors,
        }


class FeedbackGenerator:
    
    SEVERITY_PRIORITY = {
        "critical": 1,
        "high": 2,
        "medium": 3,
        "low": 4,
        "info": 5,
    }

    def __init__(self, provider: AIProvider):
        self._provider = provider

    async def generate(
        self,
        document_content: str,
        issues: list[Issue],
        policy_rules: list[PolicyRule],
        options: AnalysisOptions | None = None,
    ) -> FeedbackGenerationResult:
        import time
        start_time = time.time()
        
        try:
            rule_map = {rule.id: rule for rule in policy_rules}
            
            feedback_items = []
            errors = []
            
            prioritized_issues = sorted(
                issues,
                key=lambda i: (self.SEVERITY_PRIORITY.get(i.severity.value, 5), -i.confidence)
            )
            
            for priority, issue in enumerate(prioritized_issues, 1):
                policy_rule = rule_map.get(issue.rule_id)
                
                suggestion = None
                if options and options.include_suggestions:
                    try:
                        suggestion = await self._provider.generate_suggestion(
                            issue=issue,
                            document_context=self._extract_context(document_content, issue.location),
                            policy_rule=policy_rule or self._create_generic_rule(),
                        )
                    except Exception as e:
                        errors.append(f"Failed to generate suggestion for issue {issue.id}: {str(e)}")
                
                feedback_item = FeedbackItem(
                    id=uuid4(),
                    issue=issue,
                    suggestion=suggestion,
                    policy_rule=policy_rule,
                    priority=priority,
                )
                feedback_items.append(feedback_item)
            
            processing_time = int((time.time() - start_time) * 1000)
            
            summary = self._generate_summary(feedback_items)
            
            return FeedbackGenerationResult(
                success=True,
                feedback_items=feedback_items,
                summary=summary,
                processing_time_ms=processing_time,
                errors=errors,
            )
            
        except Exception as e:
            processing_time = int((time.time() - start_time) * 1000)
            return FeedbackGenerationResult(
                success=False,
                feedback_items=[],
                summary="",
                processing_time_ms=processing_time,
                errors=[str(e)],
            )

    def _extract_context(self, document_content: str, location: str, context_chars: int = 500) -> str:
        location_lower = location.lower()
        content_lower = document_content.lower()
        
        idx = content_lower.find(location_lower)
        if idx == -1:
            return document_content[:context_chars * 2]
        
        start = max(0, idx - context_chars)
        end = min(len(document_content), idx + len(location) + context_chars)
        
        context = document_content[start:end]
        
        if start > 0:
            context = "..." + context
        if end < len(document_content):
            context = context + "..."
        
        return context

    def _create_generic_rule(self) -> PolicyRule:
        return PolicyRule(
            id="general",
            name="General Documentation Quality",
            description="Ensure documentation is clear, complete, and accurate",
            requirement_type="SHOULD",
            category="general",
            validation_criteria="Documentation should be clear and comprehensive",
        )

    def _generate_summary(self, feedback_items: list[FeedbackItem]) -> str:
        if not feedback_items:
            return "No issues found. The document appears to be well-written."
        
        severity_counts = {}
        for item in feedback_items:
            severity = item.issue.severity.value
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
        
        parts = []
        if severity_counts.get("critical", 0) > 0:
            parts.append(f"{severity_counts['critical']} critical")
        if severity_counts.get("high", 0) > 0:
            parts.append(f"{severity_counts['high']} high priority")
        if severity_counts.get("medium", 0) > 0:
            parts.append(f"{severity_counts['medium']} medium priority")
        if severity_counts.get("low", 0) > 0:
            parts.append(f"{severity_counts['low']} low priority")
        if severity_counts.get("info", 0) > 0:
            parts.append(f"{severity_counts['info']} informational")
        
        items_with_suggestions = sum(1 for item in feedback_items if item.suggestion is not None)
        
        summary = f"Found {len(feedback_items)} issues: {', '.join(parts)}."
        if items_with_suggestions > 0:
            summary += f" Generated {items_with_suggestions} suggestions for improvement."
        
        return summary
