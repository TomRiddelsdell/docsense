from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from ..base import AnalysisResult, Issue, Suggestion
from .policy_evaluator import ComplianceResult, PolicyEvaluationResult
from .feedback_generator import FeedbackItem, FeedbackGenerationResult


@dataclass
class AggregatedResult:
    id: UUID
    document_id: UUID
    success: bool
    analysis_result: AnalysisResult | None
    policy_evaluation: PolicyEvaluationResult | None
    feedback_items: list[FeedbackItem]
    overall_score: float
    total_issues: int
    critical_issues: int
    high_issues: int
    suggestions_generated: int
    processing_time_ms: int
    model_used: str
    created_at: datetime = field(default_factory=datetime.utcnow)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": str(self.id),
            "document_id": str(self.document_id),
            "success": self.success,
            "analysis_result": self.analysis_result.to_dict() if self.analysis_result else None,
            "policy_evaluation": self.policy_evaluation.to_dict() if self.policy_evaluation else None,
            "feedback_items": [item.to_dict() for item in self.feedback_items],
            "overall_score": self.overall_score,
            "total_issues": self.total_issues,
            "critical_issues": self.critical_issues,
            "high_issues": self.high_issues,
            "suggestions_generated": self.suggestions_generated,
            "processing_time_ms": self.processing_time_ms,
            "model_used": self.model_used,
            "created_at": self.created_at.isoformat(),
            "errors": self.errors,
            "warnings": self.warnings,
        }

    @property
    def needs_attention(self) -> bool:
        return self.critical_issues > 0 or self.high_issues > 0

    @property
    def compliance_score(self) -> float:
        if self.policy_evaluation:
            return self.policy_evaluation.overall_score
        return 1.0

    def get_summary(self) -> str:
        if not self.success:
            return f"Analysis failed: {'; '.join(self.errors)}"
        
        parts = []
        parts.append(f"Found {self.total_issues} issues")
        
        if self.critical_issues > 0:
            parts.append(f"({self.critical_issues} critical)")
        elif self.high_issues > 0:
            parts.append(f"({self.high_issues} high priority)")
        
        if self.policy_evaluation:
            score_pct = int(self.policy_evaluation.overall_score * 100)
            parts.append(f"Compliance: {score_pct}%")
        
        parts.append(f"{self.suggestions_generated} suggestions")
        
        return ". ".join(parts) + "."


class ResultAggregator:
    
    def __init__(self):
        pass

    def aggregate(
        self,
        document_id: UUID,
        analysis_result: AnalysisResult | None = None,
        policy_evaluation: PolicyEvaluationResult | None = None,
        feedback_result: FeedbackGenerationResult | None = None,
    ) -> AggregatedResult:
        errors = []
        warnings = []
        total_processing_time = 0
        model_used = "unknown"
        
        issues: list[Issue] = []
        suggestions: list[Suggestion] = []
        feedback_items: list[FeedbackItem] = []
        compliance_results: list[ComplianceResult] = []
        
        if analysis_result:
            if not analysis_result.success:
                errors.extend(analysis_result.errors)
            else:
                issues = analysis_result.issues
                suggestions = analysis_result.suggestions
            total_processing_time += analysis_result.processing_time_ms
            model_used = analysis_result.model_used
        
        if policy_evaluation:
            if not policy_evaluation.success:
                errors.extend(policy_evaluation.errors)
            else:
                compliance_results = policy_evaluation.compliance_results
        
        if feedback_result:
            if not feedback_result.success:
                errors.extend(feedback_result.errors)
            else:
                feedback_items = feedback_result.feedback_items
            if feedback_result.errors:
                warnings.extend(feedback_result.errors)
            total_processing_time += feedback_result.processing_time_ms
        
        critical_count = sum(1 for i in issues if i.severity.value == "critical")
        high_count = sum(1 for i in issues if i.severity.value == "high")
        
        overall_score = self._calculate_overall_score(
            issues=issues,
            compliance_results=compliance_results,
        )
        
        suggestions_count = len(suggestions)
        if feedback_items:
            suggestions_count = sum(1 for item in feedback_items if item.suggestion is not None)
        
        success = len(errors) == 0 or (analysis_result is not None and analysis_result.success)
        
        return AggregatedResult(
            id=uuid4(),
            document_id=document_id,
            success=success,
            analysis_result=analysis_result,
            policy_evaluation=policy_evaluation,
            feedback_items=feedback_items,
            overall_score=overall_score,
            total_issues=len(issues),
            critical_issues=critical_count,
            high_issues=high_count,
            suggestions_generated=suggestions_count,
            processing_time_ms=total_processing_time,
            model_used=model_used,
            errors=errors,
            warnings=warnings,
        )

    def _calculate_overall_score(
        self,
        issues: list[Issue],
        compliance_results: list[ComplianceResult],
    ) -> float:
        if not issues and not compliance_results:
            return 1.0
        
        issue_score = 1.0
        if issues:
            severity_weights = {
                "critical": 0.25,
                "high": 0.15,
                "medium": 0.08,
                "low": 0.03,
                "info": 0.01,
            }
            penalty = sum(
                severity_weights.get(i.severity.value, 0.05)
                for i in issues
            )
            issue_score = max(0.0, 1.0 - penalty)
        
        compliance_score = 1.0
        if compliance_results:
            from .policy_evaluator import ComplianceStatus
            compliant = sum(1 for r in compliance_results if r.status == ComplianceStatus.COMPLIANT)
            partial = sum(1 for r in compliance_results if r.status == ComplianceStatus.PARTIAL)
            applicable = sum(1 for r in compliance_results if r.status != ComplianceStatus.NOT_APPLICABLE)
            if applicable > 0:
                compliance_score = (compliant + partial * 0.5) / applicable
        
        return (issue_score * 0.6) + (compliance_score * 0.4)

    def merge_results(self, results: list[AggregatedResult]) -> AggregatedResult:
        if not results:
            raise ValueError("Cannot merge empty results list")
        
        if len(results) == 1:
            return results[0]
        
        first = results[0]
        all_issues: list[Issue] = []
        all_feedback: list[FeedbackItem] = []
        all_errors: list[str] = []
        all_warnings: list[str] = []
        total_time = 0
        
        for result in results:
            if result.analysis_result:
                all_issues.extend(result.analysis_result.issues)
            all_feedback.extend(result.feedback_items)
            all_errors.extend(result.errors)
            all_warnings.extend(result.warnings)
            total_time += result.processing_time_ms
        
        critical_count = sum(1 for i in all_issues if i.severity.value == "critical")
        high_count = sum(1 for i in all_issues if i.severity.value == "high")
        suggestions_count = sum(1 for item in all_feedback if item.suggestion is not None)
        
        overall_score = sum(r.overall_score for r in results) / len(results)
        
        return AggregatedResult(
            id=uuid4(),
            document_id=first.document_id,
            success=all(r.success for r in results),
            analysis_result=first.analysis_result,
            policy_evaluation=first.policy_evaluation,
            feedback_items=all_feedback,
            overall_score=overall_score,
            total_issues=len(all_issues),
            critical_issues=critical_count,
            high_issues=high_count,
            suggestions_generated=suggestions_count,
            processing_time_ms=total_time,
            model_used=first.model_used,
            errors=list(set(all_errors)),
            warnings=list(set(all_warnings)),
        )
