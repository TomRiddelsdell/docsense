import pytest
from datetime import datetime
from uuid import uuid4

from src.infrastructure.ai.base import (
    AIProvider,
    AnalysisOptions,
    AnalysisResult,
    Issue,
    IssueSeverity,
    PolicyRule,
    ProviderType,
    Suggestion,
)


class TestPolicyRule:
    def test_create_policy_rule(self):
        rule = PolicyRule(
            id="rule-1",
            name="Test Rule",
            description="A test policy rule",
            requirement_type="MUST",
            category="compliance",
            validation_criteria="Must have X",
            examples=["example 1", "example 2"],
        )
        
        assert rule.id == "rule-1"
        assert rule.name == "Test Rule"
        assert rule.requirement_type == "MUST"
        assert len(rule.examples) == 2

    def test_from_dict(self):
        data = {
            "id": "rule-2",
            "name": "From Dict Rule",
            "description": "Created from dict",
            "requirement_type": "SHOULD",
            "category": "documentation",
            "validation_criteria": "Should have Y",
            "examples": ["ex1"],
        }
        
        rule = PolicyRule.from_dict(data)
        
        assert rule.id == "rule-2"
        assert rule.name == "From Dict Rule"
        assert rule.requirement_type == "SHOULD"

    def test_from_dict_defaults(self):
        data = {
            "id": "rule-3",
            "name": "Minimal Rule",
            "description": "Minimal",
        }
        
        rule = PolicyRule.from_dict(data)
        
        assert rule.requirement_type == "SHOULD"
        assert rule.category == "general"
        assert rule.examples == []


class TestAnalysisOptions:
    def test_defaults(self):
        options = AnalysisOptions()
        
        assert options.include_suggestions is True
        assert options.max_issues == 50
        assert options.severity_threshold == IssueSeverity.INFO
        assert options.temperature == 0.3
        assert options.model_name is None

    def test_custom_options(self):
        options = AnalysisOptions(
            include_suggestions=False,
            max_issues=10,
            severity_threshold=IssueSeverity.HIGH,
            model_name="gpt-5",
            temperature=0.5,
        )
        
        assert options.include_suggestions is False
        assert options.max_issues == 10
        assert options.severity_threshold == IssueSeverity.HIGH
        assert options.model_name == "gpt-5"

    def test_to_dict(self):
        options = AnalysisOptions(extra_context="test context")
        result = options.to_dict()
        
        assert result["include_suggestions"] is True
        assert result["extra_context"] == "test context"
        assert result["severity_threshold"] == "info"


class TestIssue:
    def test_create_issue(self):
        issue = Issue.create(
            rule_id="rule-1",
            severity=IssueSeverity.HIGH,
            title="Test Issue",
            description="A high severity issue",
            location="Section 1",
            original_text="problematic text",
            confidence=0.9,
        )
        
        assert issue.rule_id == "rule-1"
        assert issue.severity == IssueSeverity.HIGH
        assert issue.title == "Test Issue"
        assert issue.confidence == 0.9
        assert issue.id is not None

    def test_confidence_validation(self):
        with pytest.raises(ValueError):
            Issue.create(
                rule_id="rule-1",
                severity=IssueSeverity.LOW,
                title="Bad Issue",
                description="Invalid confidence",
                location="Somewhere",
                original_text="text",
                confidence=1.5,
            )

    def test_confidence_negative_validation(self):
        with pytest.raises(ValueError):
            Issue.create(
                rule_id="rule-1",
                severity=IssueSeverity.LOW,
                title="Bad Issue",
                description="Negative confidence",
                location="Somewhere",
                original_text="text",
                confidence=-0.1,
            )

    def test_to_dict(self):
        issue = Issue.create(
            rule_id="rule-1",
            severity=IssueSeverity.MEDIUM,
            title="Test",
            description="Desc",
            location="Loc",
            original_text="text",
            confidence=0.7,
        )
        
        result = issue.to_dict()
        
        assert result["rule_id"] == "rule-1"
        assert result["severity"] == "medium"
        assert "created_at" in result


class TestSuggestion:
    def test_create_suggestion(self):
        issue_id = uuid4()
        suggestion = Suggestion.create(
            issue_id=issue_id,
            suggested_text="Fixed text",
            explanation="This fixes the issue",
            confidence=0.85,
        )
        
        assert suggestion.issue_id == issue_id
        assert suggestion.suggested_text == "Fixed text"
        assert suggestion.confidence == 0.85

    def test_confidence_validation(self):
        with pytest.raises(ValueError):
            Suggestion.create(
                issue_id=uuid4(),
                suggested_text="text",
                explanation="exp",
                confidence=2.0,
            )

    def test_to_dict(self):
        issue_id = uuid4()
        suggestion = Suggestion.create(
            issue_id=issue_id,
            suggested_text="Better text",
            explanation="Improved clarity",
            confidence=0.8,
        )
        
        result = suggestion.to_dict()
        
        assert result["issue_id"] == str(issue_id)
        assert result["suggested_text"] == "Better text"


class TestAnalysisResult:
    def test_successful_result(self):
        issues = [
            Issue.create(
                rule_id="rule-1",
                severity=IssueSeverity.CRITICAL,
                title="Critical Issue",
                description="Desc",
                location="Loc",
                original_text="text",
                confidence=0.9,
            ),
            Issue.create(
                rule_id="rule-2",
                severity=IssueSeverity.HIGH,
                title="High Issue",
                description="Desc",
                location="Loc",
                original_text="text",
                confidence=0.8,
            ),
        ]
        
        result = AnalysisResult(
            success=True,
            issues=issues,
            suggestions=[],
            summary="Found 2 issues",
            processing_time_ms=1500,
            model_used="gemini-2.5-flash",
            token_count=1000,
        )
        
        assert result.success is True
        assert result.issue_count == 2
        assert len(result.critical_issues) == 1
        assert len(result.high_severity_issues) == 2

    def test_failed_result(self):
        result = AnalysisResult(
            success=False,
            issues=[],
            suggestions=[],
            summary="",
            processing_time_ms=100,
            model_used="gpt-5",
            errors=["API error"],
        )
        
        assert result.success is False
        assert result.issue_count == 0
        assert "API error" in result.errors

    def test_to_dict(self):
        result = AnalysisResult(
            success=True,
            issues=[],
            suggestions=[],
            summary="Clean",
            processing_time_ms=500,
            model_used="claude-sonnet-4-5",
        )
        
        data = result.to_dict()
        
        assert data["success"] is True
        assert data["summary"] == "Clean"
        assert data["model_used"] == "claude-sonnet-4-5"


class TestIssueSeverity:
    def test_severity_values(self):
        assert IssueSeverity.CRITICAL.value == "critical"
        assert IssueSeverity.HIGH.value == "high"
        assert IssueSeverity.MEDIUM.value == "medium"
        assert IssueSeverity.LOW.value == "low"
        assert IssueSeverity.INFO.value == "info"


class TestProviderType:
    def test_provider_values(self):
        assert ProviderType.GEMINI.value == "gemini"
        assert ProviderType.OPENAI.value == "openai"
        assert ProviderType.CLAUDE.value == "claude"
