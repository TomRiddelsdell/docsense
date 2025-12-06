import pytest
from uuid import uuid4

from src.infrastructure.ai.base import AnalysisResult, Issue, IssueSeverity, Suggestion
from src.infrastructure.ai.analysis.policy_evaluator import (
    ComplianceResult,
    ComplianceStatus,
    PolicyEvaluationResult,
)
from src.infrastructure.ai.analysis.feedback_generator import (
    FeedbackItem,
    FeedbackGenerationResult,
)
from src.infrastructure.ai.analysis.result_aggregator import (
    ResultAggregator,
    AggregatedResult,
)


class TestAggregatedResult:
    @pytest.fixture
    def sample_result(self):
        return AggregatedResult(
            id=uuid4(),
            document_id=uuid4(),
            success=True,
            analysis_result=None,
            policy_evaluation=None,
            feedback_items=[],
            overall_score=0.85,
            total_issues=5,
            critical_issues=1,
            high_issues=2,
            suggestions_generated=3,
            processing_time_ms=2000,
            model_used="gemini-2.5-flash",
        )

    def test_needs_attention_with_critical(self, sample_result):
        assert sample_result.needs_attention is True

    def test_needs_attention_without_critical(self):
        result = AggregatedResult(
            id=uuid4(),
            document_id=uuid4(),
            success=True,
            analysis_result=None,
            policy_evaluation=None,
            feedback_items=[],
            overall_score=0.95,
            total_issues=2,
            critical_issues=0,
            high_issues=0,
            suggestions_generated=1,
            processing_time_ms=1000,
            model_used="gpt-5",
        )
        
        assert result.needs_attention is False

    def test_compliance_score_with_evaluation(self):
        policy_eval = PolicyEvaluationResult(
            success=True,
            compliance_results=[],
            overall_score=0.75,
            critical_gaps=[],
            summary="",
        )
        
        result = AggregatedResult(
            id=uuid4(),
            document_id=uuid4(),
            success=True,
            analysis_result=None,
            policy_evaluation=policy_eval,
            feedback_items=[],
            overall_score=0.8,
            total_issues=0,
            critical_issues=0,
            high_issues=0,
            suggestions_generated=0,
            processing_time_ms=500,
            model_used="claude-sonnet-4-5",
        )
        
        assert result.compliance_score == 0.75

    def test_compliance_score_without_evaluation(self, sample_result):
        assert sample_result.compliance_score == 1.0

    def test_get_summary_success(self, sample_result):
        summary = sample_result.get_summary()
        
        assert "5 issues" in summary
        assert "critical" in summary.lower()

    def test_get_summary_failure(self):
        result = AggregatedResult(
            id=uuid4(),
            document_id=uuid4(),
            success=False,
            analysis_result=None,
            policy_evaluation=None,
            feedback_items=[],
            overall_score=0.0,
            total_issues=0,
            critical_issues=0,
            high_issues=0,
            suggestions_generated=0,
            processing_time_ms=100,
            model_used="test",
            errors=["Connection timeout"],
        )
        
        summary = result.get_summary()
        
        assert "failed" in summary.lower()
        assert "Connection timeout" in summary

    def test_to_dict(self, sample_result):
        data = sample_result.to_dict()
        
        assert data["success"] is True
        assert data["total_issues"] == 5
        assert data["model_used"] == "gemini-2.5-flash"


class TestResultAggregator:
    @pytest.fixture
    def aggregator(self):
        return ResultAggregator()

    @pytest.fixture
    def sample_analysis_result(self):
        return AnalysisResult(
            success=True,
            issues=[
                Issue.create("r1", IssueSeverity.CRITICAL, "Critical", "Desc", "Loc", "Text", 0.9),
                Issue.create("r2", IssueSeverity.HIGH, "High", "Desc", "Loc", "Text", 0.8),
                Issue.create("r3", IssueSeverity.MEDIUM, "Medium", "Desc", "Loc", "Text", 0.7),
            ],
            suggestions=[],
            summary="Found 3 issues",
            processing_time_ms=1500,
            model_used="gemini-2.5-flash",
            token_count=1000,
        )

    def test_aggregate_analysis_only(self, aggregator, sample_analysis_result):
        doc_id = uuid4()
        
        result = aggregator.aggregate(
            document_id=doc_id,
            analysis_result=sample_analysis_result,
        )
        
        assert result.success is True
        assert result.document_id == doc_id
        assert result.total_issues == 3
        assert result.critical_issues == 1
        assert result.high_issues == 1
        assert result.model_used == "gemini-2.5-flash"

    def test_aggregate_with_policy_evaluation(self, aggregator, sample_analysis_result):
        policy_eval = PolicyEvaluationResult(
            success=True,
            compliance_results=[
                ComplianceResult.create("1", "R1", ComplianceStatus.COMPLIANT, "", "", [], "", 0.9),
                ComplianceResult.create("2", "R2", ComplianceStatus.NON_COMPLIANT, "", "", ["Gap"], "", 0.8),
            ],
            overall_score=0.5,
            critical_gaps=["Major gap"],
            summary="Partial compliance",
        )
        
        result = aggregator.aggregate(
            document_id=uuid4(),
            analysis_result=sample_analysis_result,
            policy_evaluation=policy_eval,
        )
        
        assert result.policy_evaluation is not None
        assert result.policy_evaluation.overall_score == 0.5

    def test_aggregate_with_feedback(self, aggregator, sample_analysis_result):
        issue = Issue.create("r1", IssueSeverity.HIGH, "Test", "Desc", "Loc", "Text", 0.8)
        suggestion = Suggestion.create(issue.id, "Fixed", "Explanation", 0.9)
        
        feedback_items = [
            FeedbackItem(
                id=uuid4(),
                issue=issue,
                suggestion=suggestion,
                policy_rule=None,
                priority=1,
            )
        ]
        
        feedback_result = FeedbackGenerationResult(
            success=True,
            feedback_items=feedback_items,
            summary="Generated feedback",
            processing_time_ms=500,
        )
        
        result = aggregator.aggregate(
            document_id=uuid4(),
            analysis_result=sample_analysis_result,
            feedback_result=feedback_result,
        )
        
        assert len(result.feedback_items) == 1
        assert result.suggestions_generated == 1

    def test_aggregate_failed_analysis(self, aggregator):
        failed_analysis = AnalysisResult(
            success=False,
            issues=[],
            suggestions=[],
            summary="",
            processing_time_ms=100,
            model_used="test",
            errors=["API failure"],
        )
        
        result = aggregator.aggregate(
            document_id=uuid4(),
            analysis_result=failed_analysis,
        )
        
        assert "API failure" in result.errors

    def test_merge_results(self, aggregator):
        doc_id = uuid4()
        
        results = [
            AggregatedResult(
                id=uuid4(),
                document_id=doc_id,
                success=True,
                analysis_result=None,
                policy_evaluation=None,
                feedback_items=[],
                overall_score=0.8,
                total_issues=2,
                critical_issues=0,
                high_issues=1,
                suggestions_generated=1,
                processing_time_ms=1000,
                model_used="model1",
            ),
            AggregatedResult(
                id=uuid4(),
                document_id=doc_id,
                success=True,
                analysis_result=None,
                policy_evaluation=None,
                feedback_items=[],
                overall_score=0.9,
                total_issues=1,
                critical_issues=0,
                high_issues=0,
                suggestions_generated=1,
                processing_time_ms=500,
                model_used="model2",
            ),
        ]
        
        merged = aggregator.merge_results(results)
        
        assert merged.document_id == doc_id
        assert merged.processing_time_ms == 1500
        assert abs(merged.overall_score - 0.85) < 0.0001

    def test_merge_empty_results_raises(self, aggregator):
        with pytest.raises(ValueError):
            aggregator.merge_results([])
