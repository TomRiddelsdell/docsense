import pytest
from datetime import datetime
from uuid import uuid4, UUID

from src.domain.events.base import DomainEvent
from src.domain.events.document_events import (
    DocumentUploaded,
    DocumentConverted,
    DocumentExported,
)
from src.domain.events.analysis_events import (
    AnalysisStarted,
    AnalysisCompleted,
    AnalysisFailed,
)
from src.domain.events.feedback_events import (
    FeedbackGenerated,
    ChangeAccepted,
    ChangeRejected,
    ChangeModified,
)
from src.domain.events.policy_events import (
    PolicyRepositoryCreated,
    PolicyAdded,
    DocumentAssignedToPolicy,
)


class TestDomainEvent:
    def test_event_has_unique_id(self):
        event1 = DomainEvent(aggregate_id=uuid4())
        event2 = DomainEvent(aggregate_id=uuid4())
        assert event1.event_id != event2.event_id

    def test_event_has_occurred_at_timestamp(self):
        before = datetime.utcnow()
        event = DomainEvent(aggregate_id=uuid4())
        after = datetime.utcnow()
        assert before <= event.occurred_at <= after

    def test_event_type_returns_class_name(self):
        event = DomainEvent(aggregate_id=uuid4())
        assert event.event_type == "DomainEvent"

    def test_event_has_version(self):
        event = DomainEvent(aggregate_id=uuid4(), version=5)
        assert event.version == 5

    def test_event_is_immutable(self):
        event = DomainEvent(aggregate_id=uuid4())
        with pytest.raises(AttributeError):
            event.version = 10


class TestDocumentUploaded:
    def test_create_document_uploaded_event(self):
        aggregate_id = uuid4()
        event = DocumentUploaded(
            aggregate_id=aggregate_id,
            filename="algorithm.docx",
            original_format="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            file_size_bytes=1024,
            uploaded_by="user@example.com",
        )
        assert event.aggregate_id == aggregate_id
        assert event.filename == "algorithm.docx"
        assert event.file_size_bytes == 1024
        assert event.uploaded_by == "user@example.com"

    def test_event_type_is_document_uploaded(self):
        event = DocumentUploaded(
            aggregate_id=uuid4(),
            filename="test.pdf",
            original_format="application/pdf",
            file_size_bytes=500,
            uploaded_by="user@example.com",
        )
        assert event.event_type == "DocumentUploaded"

    def test_aggregate_type_is_document(self):
        event = DocumentUploaded(
            aggregate_id=uuid4(),
            filename="test.pdf",
            original_format="application/pdf",
            file_size_bytes=500,
            uploaded_by="user@example.com",
        )
        assert event.aggregate_type == "Document"


class TestDocumentConverted:
    def test_create_document_converted_event(self):
        aggregate_id = uuid4()
        sections = [{"heading": "Overview", "content": "Content", "level": 1}]
        metadata = {"word_count": 100}
        
        event = DocumentConverted(
            aggregate_id=aggregate_id,
            markdown_content="# Overview\nContent",
            sections=sections,
            metadata=metadata,
            conversion_warnings=[],
        )
        assert event.aggregate_id == aggregate_id
        assert event.markdown_content == "# Overview\nContent"
        assert event.sections == sections
        assert event.metadata == metadata

    def test_event_with_conversion_warnings(self):
        event = DocumentConverted(
            aggregate_id=uuid4(),
            markdown_content="# Test",
            sections=[],
            metadata={},
            conversion_warnings=["Image not supported", "Table simplified"],
        )
        assert len(event.conversion_warnings) == 2


class TestDocumentExported:
    def test_create_document_exported_event(self):
        aggregate_id = uuid4()
        event = DocumentExported(
            aggregate_id=aggregate_id,
            export_format="docx",
            exported_by="user@example.com",
            version_number="1.2.0",
        )
        assert event.export_format == "docx"
        assert event.exported_by == "user@example.com"
        assert event.version_number == "1.2.0"


class TestAnalysisStarted:
    def test_create_analysis_started_event(self):
        aggregate_id = uuid4()
        policy_repository_id = uuid4()
        
        event = AnalysisStarted(
            aggregate_id=aggregate_id,
            policy_repository_id=policy_repository_id,
            ai_model="gemini-pro",
            initiated_by="user@example.com",
        )
        assert event.aggregate_id == aggregate_id
        assert event.policy_repository_id == policy_repository_id
        assert event.ai_model == "gemini-pro"
        assert event.initiated_by == "user@example.com"

    def test_aggregate_type_is_document(self):
        event = AnalysisStarted(
            aggregate_id=uuid4(),
            policy_repository_id=uuid4(),
            ai_model="gemini-pro",
            initiated_by="user@example.com",
        )
        assert event.aggregate_type == "Document"


class TestAnalysisCompleted:
    def test_create_analysis_completed_event(self):
        aggregate_id = uuid4()
        findings = [
            {"issue": "Missing risk disclosure", "severity": "high"},
            {"issue": "Vague performance claims", "severity": "medium"},
        ]
        
        event = AnalysisCompleted(
            aggregate_id=aggregate_id,
            findings_count=2,
            compliance_score=0.75,
            findings=findings,
            processing_time_ms=1500,
        )
        assert event.findings_count == 2
        assert event.compliance_score == 0.75
        assert len(event.findings) == 2
        assert event.processing_time_ms == 1500


class TestAnalysisFailed:
    def test_create_analysis_failed_event(self):
        aggregate_id = uuid4()
        event = AnalysisFailed(
            aggregate_id=aggregate_id,
            error_message="API rate limit exceeded",
            error_code="RATE_LIMIT",
            retryable=True,
        )
        assert event.error_message == "API rate limit exceeded"
        assert event.error_code == "RATE_LIMIT"
        assert event.retryable is True


class TestFeedbackGenerated:
    def test_create_feedback_generated_event(self):
        aggregate_id = uuid4()
        feedback_id = uuid4()
        
        event = FeedbackGenerated(
            aggregate_id=aggregate_id,
            feedback_id=feedback_id,
            issue_description="Missing risk disclosure section",
            suggested_change="Add a risk disclosure section following SEC guidelines",
            confidence_score=0.92,
            policy_reference="SEC Rule 10b-5",
            section_reference="Section 3.2",
        )
        assert event.feedback_id == feedback_id
        assert event.issue_description == "Missing risk disclosure section"
        assert event.confidence_score == 0.92

    def test_aggregate_type_is_feedback_session(self):
        event = FeedbackGenerated(
            aggregate_id=uuid4(),
            feedback_id=uuid4(),
            issue_description="Test",
            suggested_change="Test change",
            confidence_score=0.8,
            policy_reference="Test policy",
            section_reference="Section 1",
        )
        assert event.aggregate_type == "FeedbackSession"


class TestChangeAccepted:
    def test_create_change_accepted_event(self):
        aggregate_id = uuid4()
        feedback_id = uuid4()
        
        event = ChangeAccepted(
            aggregate_id=aggregate_id,
            feedback_id=feedback_id,
            accepted_by="user@example.com",
            applied_change="Added risk disclosure section",
        )
        assert event.feedback_id == feedback_id
        assert event.accepted_by == "user@example.com"
        assert event.applied_change == "Added risk disclosure section"


class TestChangeRejected:
    def test_create_change_rejected_event(self):
        aggregate_id = uuid4()
        feedback_id = uuid4()
        
        event = ChangeRejected(
            aggregate_id=aggregate_id,
            feedback_id=feedback_id,
            rejected_by="user@example.com",
            rejection_reason="Already covered in another section",
        )
        assert event.feedback_id == feedback_id
        assert event.rejected_by == "user@example.com"
        assert event.rejection_reason == "Already covered in another section"


class TestChangeModified:
    def test_create_change_modified_event(self):
        aggregate_id = uuid4()
        feedback_id = uuid4()
        
        event = ChangeModified(
            aggregate_id=aggregate_id,
            feedback_id=feedback_id,
            modified_by="user@example.com",
            original_change="Add risk disclosure",
            modified_change="Add condensed risk summary",
        )
        assert event.feedback_id == feedback_id
        assert event.original_change == "Add risk disclosure"
        assert event.modified_change == "Add condensed risk summary"


class TestPolicyRepositoryCreated:
    def test_create_policy_repository_created_event(self):
        aggregate_id = uuid4()
        
        event = PolicyRepositoryCreated(
            aggregate_id=aggregate_id,
            name="SEC Compliance Policies",
            description="Policies for SEC regulatory compliance",
            created_by="admin@example.com",
        )
        assert event.name == "SEC Compliance Policies"
        assert event.description == "Policies for SEC regulatory compliance"
        assert event.created_by == "admin@example.com"

    def test_aggregate_type_is_policy_repository(self):
        event = PolicyRepositoryCreated(
            aggregate_id=uuid4(),
            name="Test",
            description="Test",
            created_by="admin@example.com",
        )
        assert event.aggregate_type == "PolicyRepository"


class TestPolicyAdded:
    def test_create_policy_added_event(self):
        aggregate_id = uuid4()
        policy_id = uuid4()
        
        event = PolicyAdded(
            aggregate_id=aggregate_id,
            policy_id=policy_id,
            policy_name="Risk Disclosure Requirements",
            policy_content="All documents must include risk disclosure...",
            requirement_type="MUST",
            added_by="admin@example.com",
        )
        assert event.policy_id == policy_id
        assert event.policy_name == "Risk Disclosure Requirements"
        assert event.requirement_type == "MUST"


class TestDocumentAssignedToPolicy:
    def test_create_document_assigned_event(self):
        aggregate_id = uuid4()
        document_id = uuid4()
        
        event = DocumentAssignedToPolicy(
            aggregate_id=aggregate_id,
            document_id=document_id,
            assigned_by="user@example.com",
        )
        assert event.document_id == document_id
        assert event.assigned_by == "user@example.com"
