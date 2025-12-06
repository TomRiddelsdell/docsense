import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from src.infrastructure.ai.base import (
    AIProvider,
    AnalysisResult,
    AnalysisOptions,
    Issue,
    IssueSeverity,
    PolicyRule,
)
from src.infrastructure.ai.analysis.policy_evaluator import (
    PolicyEvaluator,
    ComplianceResult,
    ComplianceStatus,
    PolicyEvaluationResult,
)


class TestComplianceStatus:
    def test_status_values(self):
        assert ComplianceStatus.COMPLIANT.value == "compliant"
        assert ComplianceStatus.PARTIAL.value == "partial"
        assert ComplianceStatus.NON_COMPLIANT.value == "non_compliant"
        assert ComplianceStatus.NOT_APPLICABLE.value == "not_applicable"


class TestComplianceResult:
    def test_create(self):
        result = ComplianceResult.create(
            rule_id="rule-1",
            rule_name="Test Rule",
            status=ComplianceStatus.COMPLIANT,
            evidence="Found in section 2",
            location="Section 2",
            gaps=[],
            remediation="N/A",
            confidence=0.95,
        )
        
        assert result.rule_id == "rule-1"
        assert result.status == ComplianceStatus.COMPLIANT
        assert result.confidence == 0.95
        assert result.id is not None

    def test_to_dict(self):
        result = ComplianceResult.create(
            rule_id="rule-2",
            rule_name="Another Rule",
            status=ComplianceStatus.PARTIAL,
            evidence="Partial evidence",
            location="Section 3",
            gaps=["Missing X", "Missing Y"],
            remediation="Add X and Y",
            confidence=0.7,
        )
        
        data = result.to_dict()
        
        assert data["rule_id"] == "rule-2"
        assert data["status"] == "partial"
        assert len(data["gaps"]) == 2


class TestPolicyEvaluationResult:
    def test_counts(self):
        results = [
            ComplianceResult.create("1", "R1", ComplianceStatus.COMPLIANT, "", "", [], "", 0.9),
            ComplianceResult.create("2", "R2", ComplianceStatus.COMPLIANT, "", "", [], "", 0.9),
            ComplianceResult.create("3", "R3", ComplianceStatus.PARTIAL, "", "", [], "", 0.7),
            ComplianceResult.create("4", "R4", ComplianceStatus.NON_COMPLIANT, "", "", [], "", 0.8),
        ]
        
        evaluation = PolicyEvaluationResult(
            success=True,
            compliance_results=results,
            overall_score=0.75,
            critical_gaps=["Gap 1"],
            summary="Test summary",
        )
        
        assert evaluation.compliant_count == 2
        assert evaluation.partial_count == 1
        assert evaluation.non_compliant_count == 1

    def test_to_dict(self):
        evaluation = PolicyEvaluationResult(
            success=True,
            compliance_results=[],
            overall_score=1.0,
            critical_gaps=[],
            summary="All compliant",
        )
        
        data = evaluation.to_dict()
        
        assert data["success"] is True
        assert data["overall_score"] == 1.0


class TestPolicyEvaluator:
    @pytest.fixture
    def mock_provider(self):
        provider = MagicMock(spec=AIProvider)
        provider.analyze_document = AsyncMock()
        return provider

    @pytest.fixture
    def evaluator(self, mock_provider):
        return PolicyEvaluator(mock_provider)

    @pytest.fixture
    def sample_rules(self):
        return [
            PolicyRule(
                id="rule-1",
                name="Risk Disclosure",
                description="Must disclose risks",
                requirement_type="MUST",
                category="compliance",
                validation_criteria="Clear risk statements",
            ),
            PolicyRule(
                id="rule-2",
                name="Algorithm Description",
                description="Should describe algorithm",
                requirement_type="SHOULD",
                category="documentation",
                validation_criteria="Clear algorithm description",
            ),
        ]

    @pytest.mark.asyncio
    async def test_evaluate_success_no_issues(self, evaluator, mock_provider, sample_rules):
        mock_provider.analyze_document.return_value = AnalysisResult(
            success=True,
            issues=[],
            suggestions=[],
            summary="No issues found",
            processing_time_ms=1000,
            model_used="test-model",
        )
        
        result = await evaluator.evaluate(
            document_content="Test document",
            policy_rules=sample_rules,
        )
        
        assert result.success is True
        assert len(result.compliance_results) == 2
        assert result.compliance_results[0].status == ComplianceStatus.COMPLIANT

    @pytest.mark.asyncio
    async def test_evaluate_with_issues(self, evaluator, mock_provider, sample_rules):
        issue = Issue.create(
            rule_id="rule-1",
            severity=IssueSeverity.HIGH,
            title="Missing risk",
            description="Risk not disclosed",
            location="Section 1",
            original_text="Returns expected",
            confidence=0.9,
        )
        
        mock_provider.analyze_document.return_value = AnalysisResult(
            success=True,
            issues=[issue],
            suggestions=[],
            summary="Found 1 issue",
            processing_time_ms=1500,
            model_used="test-model",
        )
        
        result = await evaluator.evaluate(
            document_content="Test document",
            policy_rules=sample_rules,
        )
        
        assert result.success is True
        rule1_result = next(r for r in result.compliance_results if r.rule_id == "rule-1")
        assert rule1_result.status == ComplianceStatus.NON_COMPLIANT

    @pytest.mark.asyncio
    async def test_evaluate_failure(self, evaluator, mock_provider, sample_rules):
        mock_provider.analyze_document.return_value = AnalysisResult(
            success=False,
            issues=[],
            suggestions=[],
            summary="",
            processing_time_ms=100,
            model_used="test-model",
            errors=["API error"],
        )
        
        result = await evaluator.evaluate(
            document_content="Test",
            policy_rules=sample_rules,
        )
        
        assert result.success is False
        assert "API error" in result.errors

    @pytest.mark.asyncio
    async def test_evaluate_exception(self, evaluator, mock_provider, sample_rules):
        mock_provider.analyze_document.side_effect = Exception("Connection failed")
        
        result = await evaluator.evaluate(
            document_content="Test",
            policy_rules=sample_rules,
        )
        
        assert result.success is False
        assert "Connection failed" in result.errors[0]
