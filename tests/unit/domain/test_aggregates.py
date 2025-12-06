import pytest
from uuid import uuid4, UUID
from typing import List

from src.domain.aggregates.base import Aggregate
from src.domain.aggregates.document import Document
from src.domain.aggregates.feedback_session import FeedbackSession
from src.domain.aggregates.policy_repository import PolicyRepository
from src.domain.events.base import DomainEvent
from src.domain.events.document_events import (
    DocumentUploaded,
    DocumentConverted,
    DocumentExported,
)
from src.domain.events.analysis_events import (
    AnalysisStarted,
    AnalysisCompleted,
)
from src.domain.events.feedback_events import (
    FeedbackGenerated,
    ChangeAccepted,
    ChangeRejected,
)
from src.domain.events.policy_events import (
    PolicyRepositoryCreated,
    PolicyAdded,
    DocumentAssignedToPolicy,
)
from src.domain.value_objects import DocumentStatus
from src.domain.exceptions import (
    InvalidDocumentState,
    AnalysisInProgress,
    AnalysisNotStarted,
    FeedbackNotFound,
    ChangeAlreadyProcessed,
    PolicyAlreadyExists,
    PolicyIdAlreadyExists,
    DocumentAlreadyAssigned,
)


class TestAggregate:
    def test_aggregate_has_id(self):
        agg_id = uuid4()
        
        class TestAggregate(Aggregate):
            def _when(self, event: DomainEvent) -> None:
                pass
        
        agg = TestAggregate(agg_id)
        assert agg.id == agg_id

    def test_aggregate_starts_at_version_zero(self):
        class TestAggregate(Aggregate):
            def _when(self, event: DomainEvent) -> None:
                pass
        
        agg = TestAggregate(uuid4())
        assert agg.version == 0

    def test_pending_events_starts_empty(self):
        class TestAggregate(Aggregate):
            def _when(self, event: DomainEvent) -> None:
                pass
        
        agg = TestAggregate(uuid4())
        assert agg.pending_events == []


class TestDocument:
    def test_upload_creates_document_with_uploaded_event(self):
        doc_id = uuid4()
        doc = Document.upload(
            document_id=doc_id,
            filename="algorithm.docx",
            content=b"content",
            original_format="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            uploaded_by="user@example.com",
        )
        
        assert doc.id == doc_id
        assert doc.filename == "algorithm.docx"
        assert doc.status == DocumentStatus.UPLOADED
        assert len(doc.pending_events) == 1
        assert isinstance(doc.pending_events[0], DocumentUploaded)

    def test_convert_updates_document_with_markdown(self):
        doc = Document.upload(
            document_id=uuid4(),
            filename="test.docx",
            content=b"content",
            original_format="docx",
            uploaded_by="user@example.com",
        )
        
        sections = [{"heading": "Overview", "content": "Content", "level": 1}]
        metadata = {"word_count": 100}
        
        doc.convert(
            markdown_content="# Overview\nContent",
            sections=sections,
            metadata=metadata,
        )
        
        assert doc.markdown_content == "# Overview\nContent"
        assert doc.status == DocumentStatus.CONVERTED
        assert len(doc.pending_events) == 2
        assert isinstance(doc.pending_events[1], DocumentConverted)

    def test_start_analysis_changes_status_to_analyzing(self):
        doc = Document.upload(
            document_id=uuid4(),
            filename="test.docx",
            content=b"content",
            original_format="docx",
            uploaded_by="user@example.com",
        )
        doc.convert("# Test", [], {})
        
        policy_repo_id = uuid4()
        doc.start_analysis(
            policy_repository_id=policy_repo_id,
            ai_model="gemini-pro",
            initiated_by="user@example.com",
        )
        
        assert doc.status == DocumentStatus.ANALYZING
        assert len(doc.pending_events) == 3

    def test_complete_analysis_updates_compliance_score(self):
        doc = Document.upload(
            document_id=uuid4(),
            filename="test.docx",
            content=b"content",
            original_format="docx",
            uploaded_by="user@example.com",
        )
        doc.convert("# Test", [], {})
        doc.start_analysis(uuid4(), "gemini-pro", "user@example.com")
        
        doc.complete_analysis(
            findings_count=2,
            compliance_score=0.85,
            findings=[{"issue": "Test"}],
            processing_time_ms=1500,
        )
        
        assert doc.status == DocumentStatus.ANALYZED
        assert doc.compliance_score == 0.85

    def test_export_records_export_event(self):
        doc = Document.upload(
            document_id=uuid4(),
            filename="test.docx",
            content=b"content",
            original_format="docx",
            uploaded_by="user@example.com",
        )
        doc.convert("# Test", [], {})
        doc.start_analysis(uuid4(), "gemini-pro", "user@example.com")
        doc.complete_analysis(2, 0.85, [], 1500)
        
        doc.export(
            export_format="docx",
            exported_by="user@example.com",
        )
        
        assert doc.status == DocumentStatus.EXPORTED
        assert isinstance(doc.pending_events[-1], DocumentExported)

    def test_clear_pending_events_returns_and_clears(self):
        doc = Document.upload(
            document_id=uuid4(),
            filename="test.docx",
            content=b"content",
            original_format="docx",
            uploaded_by="user@example.com",
        )
        
        events = doc.clear_pending_events()
        assert len(events) == 1
        assert doc.pending_events == []

    def test_reconstitute_from_events(self):
        doc_id = uuid4()
        events = [
            DocumentUploaded(
                aggregate_id=doc_id,
                filename="test.docx",
                original_format="docx",
                file_size_bytes=100,
                uploaded_by="user@example.com",
            ),
            DocumentConverted(
                aggregate_id=doc_id,
                markdown_content="# Test",
                sections=[],
                metadata={},
                conversion_warnings=[],
            ),
        ]
        
        doc = Document.reconstitute(events)
        
        assert doc.id == doc_id
        assert doc.filename == "test.docx"
        assert doc.markdown_content == "# Test"
        assert doc.status == DocumentStatus.CONVERTED
        assert doc.version == 2
        assert doc.pending_events == []

    def test_convert_fails_if_not_uploaded(self):
        doc = Document(uuid4())
        with pytest.raises(InvalidDocumentState) as exc_info:
            doc.convert("# Test", [], {})
        assert "convert" in str(exc_info.value)

    def test_start_analysis_fails_if_not_converted(self):
        doc = Document.upload(
            document_id=uuid4(),
            filename="test.docx",
            content=b"content",
            original_format="docx",
            uploaded_by="user@example.com",
        )
        with pytest.raises(InvalidDocumentState) as exc_info:
            doc.start_analysis(uuid4(), "gemini-pro", "user@example.com")
        assert "start_analysis" in str(exc_info.value)

    def test_start_analysis_fails_if_already_analyzing(self):
        doc = Document.upload(
            document_id=uuid4(),
            filename="test.docx",
            content=b"content",
            original_format="docx",
            uploaded_by="user@example.com",
        )
        doc.convert("# Test", [], {})
        doc.start_analysis(uuid4(), "gemini-pro", "user@example.com")
        
        with pytest.raises(AnalysisInProgress):
            doc.start_analysis(uuid4(), "gemini-pro", "user@example.com")

    def test_complete_analysis_fails_if_not_analyzing(self):
        doc = Document.upload(
            document_id=uuid4(),
            filename="test.docx",
            content=b"content",
            original_format="docx",
            uploaded_by="user@example.com",
        )
        doc.convert("# Test", [], {})
        
        with pytest.raises(AnalysisNotStarted):
            doc.complete_analysis(0, 0.9, [], 1000)

    def test_export_fails_if_not_analyzed(self):
        doc = Document.upload(
            document_id=uuid4(),
            filename="test.docx",
            content=b"content",
            original_format="docx",
            uploaded_by="user@example.com",
        )
        doc.convert("# Test", [], {})
        
        with pytest.raises(InvalidDocumentState) as exc_info:
            doc.export("docx", "user@example.com")
        assert "export" in str(exc_info.value)

    def test_can_reanalyze_after_export(self):
        doc = Document.upload(
            document_id=uuid4(),
            filename="test.docx",
            content=b"content",
            original_format="docx",
            uploaded_by="user@example.com",
        )
        doc.convert("# Test", [], {})
        doc.start_analysis(uuid4(), "gemini-pro", "user@example.com")
        doc.complete_analysis(2, 0.85, [], 1500)
        doc.export("docx", "user@example.com")
        
        assert doc.status == DocumentStatus.EXPORTED
        
        doc.start_analysis(uuid4(), "gemini-pro", "user@example.com")
        assert doc.status == DocumentStatus.ANALYZING


class TestFeedbackSession:
    def test_create_session_for_document(self):
        session_id = uuid4()
        document_id = uuid4()
        
        session = FeedbackSession.create_for_document(
            session_id=session_id,
            document_id=document_id,
        )
        
        assert session.id == session_id
        assert session.document_id == document_id
        assert session.feedback_items == []

    def test_add_feedback_creates_feedback_item(self):
        session = FeedbackSession.create_for_document(
            session_id=uuid4(),
            document_id=uuid4(),
        )
        
        feedback_id = uuid4()
        session.add_feedback(
            feedback_id=feedback_id,
            issue_description="Missing risk disclosure",
            suggested_change="Add risk section",
            confidence_score=0.92,
            policy_reference="SEC Rule 10b-5",
            section_reference="Section 3",
        )
        
        assert len(session.feedback_items) == 1
        assert session.feedback_items[0]["feedback_id"] == feedback_id

    def test_accept_change_marks_feedback_accepted(self):
        session = FeedbackSession.create_for_document(
            session_id=uuid4(),
            document_id=uuid4(),
        )
        feedback_id = uuid4()
        session.add_feedback(
            feedback_id=feedback_id,
            issue_description="Test",
            suggested_change="Change",
            confidence_score=0.8,
            policy_reference="Policy",
            section_reference="Section",
        )
        
        session.accept_change(
            feedback_id=feedback_id,
            accepted_by="user@example.com",
            applied_change="Applied change",
        )
        
        assert session.feedback_items[0]["status"] == "ACCEPTED"

    def test_reject_change_marks_feedback_rejected(self):
        session = FeedbackSession.create_for_document(
            session_id=uuid4(),
            document_id=uuid4(),
        )
        feedback_id = uuid4()
        session.add_feedback(
            feedback_id=feedback_id,
            issue_description="Test",
            suggested_change="Change",
            confidence_score=0.8,
            policy_reference="Policy",
            section_reference="Section",
        )
        
        session.reject_change(
            feedback_id=feedback_id,
            rejected_by="user@example.com",
            rejection_reason="Not applicable",
        )
        
        assert session.feedback_items[0]["status"] == "REJECTED"

    def test_accept_change_fails_if_already_processed(self):
        session = FeedbackSession.create_for_document(
            session_id=uuid4(),
            document_id=uuid4(),
        )
        feedback_id = uuid4()
        session.add_feedback(
            feedback_id=feedback_id,
            issue_description="Test",
            suggested_change="Change",
            confidence_score=0.8,
            policy_reference="Policy",
            section_reference="Section",
        )
        session.accept_change(feedback_id, "user@example.com", "Applied")
        
        with pytest.raises(ChangeAlreadyProcessed):
            session.accept_change(feedback_id, "user@example.com", "Applied again")

    def test_reject_change_fails_if_already_processed(self):
        session = FeedbackSession.create_for_document(
            session_id=uuid4(),
            document_id=uuid4(),
        )
        feedback_id = uuid4()
        session.add_feedback(
            feedback_id=feedback_id,
            issue_description="Test",
            suggested_change="Change",
            confidence_score=0.8,
            policy_reference="Policy",
            section_reference="Section",
        )
        session.reject_change(feedback_id, "user@example.com", "Reason")
        
        with pytest.raises(ChangeAlreadyProcessed):
            session.reject_change(feedback_id, "user@example.com", "Reason again")

    def test_accept_change_fails_if_feedback_not_found(self):
        session = FeedbackSession.create_for_document(
            session_id=uuid4(),
            document_id=uuid4(),
        )
        
        with pytest.raises(FeedbackNotFound):
            session.accept_change(uuid4(), "user@example.com", "Applied")


class TestPolicyRepository:
    def test_create_policy_repository(self):
        repo_id = uuid4()
        repo = PolicyRepository.create(
            repository_id=repo_id,
            name="SEC Compliance Policies",
            description="Policies for SEC compliance",
            created_by="admin@example.com",
        )
        
        assert repo.id == repo_id
        assert repo.name == "SEC Compliance Policies"
        assert repo.policies == []

    def test_add_policy_to_repository(self):
        repo = PolicyRepository.create(
            repository_id=uuid4(),
            name="Test Policies",
            description="Test",
            created_by="admin@example.com",
        )
        
        policy_id = uuid4()
        repo.add_policy(
            policy_id=policy_id,
            policy_name="Risk Disclosure",
            policy_content="All docs must have risk disclosure",
            requirement_type="MUST",
            added_by="admin@example.com",
        )
        
        assert len(repo.policies) == 1
        assert repo.policies[0]["policy_id"] == policy_id

    def test_assign_document_to_repository(self):
        repo = PolicyRepository.create(
            repository_id=uuid4(),
            name="Test Policies",
            description="Test",
            created_by="admin@example.com",
        )
        
        document_id = uuid4()
        repo.assign_document(
            document_id=document_id,
            assigned_by="user@example.com",
        )
        
        assert document_id in repo.assigned_documents

    def test_add_duplicate_policy_by_id_fails(self):
        repo = PolicyRepository.create(
            repository_id=uuid4(),
            name="Test Policies",
            description="Test",
            created_by="admin@example.com",
        )
        policy_id = uuid4()
        repo.add_policy(
            policy_id=policy_id,
            policy_name="Policy 1",
            policy_content="Content",
            requirement_type="MUST",
            added_by="admin@example.com",
        )
        
        with pytest.raises(PolicyIdAlreadyExists):
            repo.add_policy(
                policy_id=policy_id,
                policy_name="Policy 2",
                policy_content="Content",
                requirement_type="MUST",
                added_by="admin@example.com",
            )

    def test_add_duplicate_policy_by_name_fails(self):
        repo = PolicyRepository.create(
            repository_id=uuid4(),
            name="Test Policies",
            description="Test",
            created_by="admin@example.com",
        )
        repo.add_policy(
            policy_id=uuid4(),
            policy_name="Risk Disclosure",
            policy_content="Content",
            requirement_type="MUST",
            added_by="admin@example.com",
        )
        
        with pytest.raises(PolicyAlreadyExists):
            repo.add_policy(
                policy_id=uuid4(),
                policy_name="Risk Disclosure",
                policy_content="Other content",
                requirement_type="SHOULD",
                added_by="admin@example.com",
            )

    def test_assign_duplicate_document_fails(self):
        repo = PolicyRepository.create(
            repository_id=uuid4(),
            name="Test Policies",
            description="Test",
            created_by="admin@example.com",
        )
        document_id = uuid4()
        repo.assign_document(document_id, "user@example.com")
        
        with pytest.raises(DocumentAlreadyAssigned):
            repo.assign_document(document_id, "user@example.com")
