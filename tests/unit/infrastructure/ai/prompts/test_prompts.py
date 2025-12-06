import pytest

from src.infrastructure.ai.prompts.base import PromptTemplate, PromptContext
from src.infrastructure.ai.prompts.document_analysis import DocumentAnalysisPrompt
from src.infrastructure.ai.prompts.policy_compliance import PolicyCompliancePrompt
from src.infrastructure.ai.prompts.suggestion_generation import SuggestionGenerationPrompt


class TestPromptContext:
    def test_defaults(self):
        context = PromptContext()
        
        assert context.document_content == ""
        assert context.policy_rules == []
        assert context.max_issues == 50
        assert context.include_suggestions is True

    def test_custom_context(self):
        context = PromptContext(
            document_content="Test document",
            policy_rules=[{"id": "1", "name": "Rule 1", "description": "Test"}],
            max_issues=10,
            include_suggestions=False,
            extra_context="Additional info",
        )
        
        assert context.document_content == "Test document"
        assert len(context.policy_rules) == 1
        assert context.max_issues == 10

    def test_to_dict(self):
        context = PromptContext(document_content="Test")
        result = context.to_dict()
        
        assert result["document_content"] == "Test"
        assert "policy_rules" in result


class TestDocumentAnalysisPrompt:
    @pytest.fixture
    def prompt(self):
        return DocumentAnalysisPrompt()

    def test_name(self, prompt):
        assert prompt.name == "document_analysis"

    def test_description(self, prompt):
        assert "trading algorithm" in prompt.description.lower()

    def test_system_prompt(self, prompt):
        system = prompt.get_system_prompt()
        
        assert "expert" in system.lower()
        assert "trading algorithm" in system.lower()

    def test_render_basic(self, prompt):
        context = PromptContext(
            document_content="This is a test trading algorithm document.",
            policy_rules=[
                {"id": "1", "name": "Risk Disclosure", "description": "Must disclose risks"}
            ],
        )
        
        rendered = prompt.render(context)
        
        assert "test trading algorithm" in rendered
        assert "Risk Disclosure" in rendered
        assert "50" in rendered

    def test_render_with_focus_sections(self, prompt):
        context = PromptContext(
            document_content="Test document",
            section_focus=["Introduction", "Risk Management"],
        )
        
        rendered = prompt.render(context)
        
        assert "Introduction" in rendered
        assert "Risk Management" in rendered

    def test_render_with_extra_context(self, prompt):
        context = PromptContext(
            document_content="Test",
            extra_context="This is a SEC filing",
        )
        
        rendered = prompt.render(context)
        
        assert "SEC filing" in rendered


class TestPolicyCompliancePrompt:
    @pytest.fixture
    def prompt(self):
        return PolicyCompliancePrompt()

    def test_name(self, prompt):
        assert prompt.name == "policy_compliance"

    def test_description(self, prompt):
        assert "compliance" in prompt.description.lower()

    def test_system_prompt(self, prompt):
        system = prompt.get_system_prompt()
        
        assert "compliance" in system.lower()
        assert "SEC" in system or "regulatory" in system.lower()

    def test_render(self, prompt):
        context = PromptContext(
            document_content="Trading algorithm documentation",
            policy_rules=[
                {"id": "sec-1", "name": "SEC Rule 15c3-5", "description": "Risk controls"}
            ],
        )
        
        rendered = prompt.render(context)
        
        assert "SEC Rule 15c3-5" in rendered
        assert "compliance_results" in rendered


class TestSuggestionGenerationPrompt:
    @pytest.fixture
    def prompt(self):
        return SuggestionGenerationPrompt()

    def test_name(self, prompt):
        assert prompt.name == "suggestion_generation"

    def test_description(self, prompt):
        assert "suggestion" in prompt.description.lower()

    def test_system_prompt(self, prompt):
        system = prompt.get_system_prompt()
        
        assert "technical writer" in system.lower()

    def test_render_requires_issue_data(self, prompt):
        context = PromptContext(document_content="Test")
        
        with pytest.raises(ValueError, match="issue_data is required"):
            prompt.render(context)

    def test_render_with_issue(self, prompt):
        context = PromptContext(
            document_content="Test document with problematic section",
            issue_data={
                "title": "Missing Risk Disclosure",
                "severity": "high",
                "description": "The document lacks proper risk disclosure",
                "location": "Section 3",
                "original_text": "Returns may vary",
            },
            policy_rules=[
                {"id": "risk-1", "name": "Risk Disclosure", "description": "Must disclose all material risks", "requirement_type": "MUST", "validation_criteria": "Clear risk statements"}
            ],
        )
        
        rendered = prompt.render(context)
        
        assert "Missing Risk Disclosure" in rendered
        assert "Returns may vary" in rendered
        assert "Risk Disclosure" in rendered


class TestPromptTemplateTruncation:
    def test_truncate_long_content(self):
        prompt = DocumentAnalysisPrompt()
        long_content = "x" * 60000
        
        context = PromptContext(document_content=long_content)
        rendered = prompt.render(context)
        
        assert "[Content truncated for length]" in rendered

    def test_no_truncation_for_short_content(self):
        prompt = DocumentAnalysisPrompt()
        short_content = "This is a short document."
        
        context = PromptContext(document_content=short_content)
        rendered = prompt.render(context)
        
        assert "[Content truncated" not in rendered


class TestPromptTemplateFormatRules:
    def test_format_rules_empty(self):
        prompt = DocumentAnalysisPrompt()
        context = PromptContext(document_content="Test", policy_rules=[])
        
        rendered = prompt.render(context)
        
        assert "No specific policy rules provided" in rendered

    def test_format_rules_with_data(self):
        prompt = DocumentAnalysisPrompt()
        context = PromptContext(
            document_content="Test",
            policy_rules=[
                {
                    "name": "Rule 1",
                    "requirement_type": "MUST",
                    "description": "First rule",
                    "validation_criteria": "Check X",
                },
                {
                    "name": "Rule 2",
                    "requirement_type": "SHOULD",
                    "description": "Second rule",
                },
            ],
        )
        
        rendered = prompt.render(context)
        
        assert "Rule 1" in rendered
        assert "MUST" in rendered
        assert "Rule 2" in rendered
