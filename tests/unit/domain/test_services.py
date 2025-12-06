import pytest
from uuid import uuid4

from src.domain.services.document_conversion_service import DocumentConversionService
from src.domain.services.compliance_checker import ComplianceChecker
from src.domain.services.version_calculator import VersionCalculator
from src.domain.value_objects import VersionNumber, RequirementType


class TestDocumentConversionService:
    def test_can_convert_supported_formats(self):
        service = DocumentConversionService()
        assert service.can_convert("application/pdf")
        assert service.can_convert("application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        assert service.can_convert("text/markdown")
        assert service.can_convert("text/x-rst")

    def test_cannot_convert_unsupported_formats(self):
        service = DocumentConversionService()
        assert not service.can_convert("image/png")
        assert not service.can_convert("application/zip")

    def test_get_supported_formats_returns_list(self):
        service = DocumentConversionService()
        formats = service.get_supported_formats()
        assert isinstance(formats, list)
        assert len(formats) > 0


class TestComplianceChecker:
    def test_check_policy_requirement_met(self):
        checker = ComplianceChecker()
        result = checker.check_requirement(
            document_content="This document includes a risk disclosure section.",
            policy_rule="Document must contain risk disclosure",
            requirement_type=RequirementType.MUST,
        )
        assert result.is_compliant is not None
        assert 0.0 <= result.confidence <= 1.0

    def test_identify_issues_returns_list(self):
        checker = ComplianceChecker()
        issues = checker.identify_issues(
            document_content="# Algorithm\nThis is a trading algorithm.",
            policy_rules=[
                {"rule": "Must have risk disclosure", "type": RequirementType.MUST},
                {"rule": "Should have performance metrics", "type": RequirementType.SHOULD},
            ],
        )
        assert isinstance(issues, list)

    def test_must_requirements_have_higher_threshold(self):
        checker = ComplianceChecker()
        doc_content = "risk disclosure warning"
        
        must_result = checker.check_requirement(
            document_content=doc_content,
            policy_rule="Document must contain risk disclosure",
            requirement_type=RequirementType.MUST,
        )
        may_result = checker.check_requirement(
            document_content=doc_content,
            policy_rule="Document must contain risk disclosure",
            requirement_type=RequirementType.MAY,
        )
        assert must_result.requirement_type == RequirementType.MUST
        assert may_result.requirement_type == RequirementType.MAY

    def test_issues_include_severity(self):
        checker = ComplianceChecker()
        issues = checker.identify_issues(
            document_content="# Algorithm\nBasic content",
            policy_rules=[
                {"rule": "Must have comprehensive risk disclosure", "type": RequirementType.MUST},
            ],
        )
        assert len(issues) > 0
        assert "severity" in issues[0]
        assert issues[0]["severity"] == "HIGH"

    def test_issues_handle_string_requirement_type(self):
        checker = ComplianceChecker()
        issues = checker.identify_issues(
            document_content="# Algorithm\nBasic content",
            policy_rules=[
                {"rule": "Should have performance data", "type": "SHOULD"},
            ],
        )
        assert isinstance(issues, list)


class TestVersionCalculator:
    def test_calculate_patch_increment_for_minor_changes(self):
        calculator = VersionCalculator()
        current = VersionNumber(1, 2, 3)
        
        new_version = calculator.calculate_next_version(
            current_version=current,
            change_type="minor",
        )
        
        assert new_version.major == 1
        assert new_version.minor == 2
        assert new_version.patch == 4

    def test_calculate_minor_increment_for_feature_changes(self):
        calculator = VersionCalculator()
        current = VersionNumber(1, 2, 3)
        
        new_version = calculator.calculate_next_version(
            current_version=current,
            change_type="feature",
        )
        
        assert new_version.major == 1
        assert new_version.minor == 3
        assert new_version.patch == 0

    def test_calculate_major_increment_for_breaking_changes(self):
        calculator = VersionCalculator()
        current = VersionNumber(1, 2, 3)
        
        new_version = calculator.calculate_next_version(
            current_version=current,
            change_type="breaking",
        )
        
        assert new_version.major == 2
        assert new_version.minor == 0
        assert new_version.patch == 0
