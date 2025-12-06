import pytest
from uuid import uuid4
from datetime import datetime, timezone

from src.infrastructure.persistence.event_serializer import EventSerializer
from src.domain.events import (
    DocumentUploaded,
    DocumentConverted,
    AnalysisStarted,
    AnalysisCompleted,
    FeedbackGenerated,
    ChangeAccepted,
    PolicyRepositoryCreated,
    PolicyAdded,
)


class TestEventSerializer:
    @pytest.fixture
    def serializer(self):
        return EventSerializer()

    @pytest.fixture
    def sample_document_uploaded(self):
        return DocumentUploaded(
            event_id=uuid4(),
            aggregate_id=uuid4(),
            occurred_at=datetime.now(timezone.utc),
            version=1,
            filename="test.pdf",
            original_format="pdf",
            file_size_bytes=1024,
            uploaded_by="user@example.com"
        )

    def test_serialize_document_uploaded(self, serializer, sample_document_uploaded):
        data = serializer.serialize(sample_document_uploaded)
        
        assert data["filename"] == "test.pdf"
        assert data["original_format"] == "pdf"
        assert data["file_size_bytes"] == 1024
        assert data["uploaded_by"] == "user@example.com"
        assert isinstance(data["event_id"], str)
        assert isinstance(data["aggregate_id"], str)

    def test_deserialize_document_uploaded(self, serializer, sample_document_uploaded):
        data = serializer.serialize(sample_document_uploaded)
        restored = serializer.deserialize("DocumentUploaded", data)
        
        assert restored.filename == sample_document_uploaded.filename
        assert restored.original_format == sample_document_uploaded.original_format
        assert restored.file_size_bytes == sample_document_uploaded.file_size_bytes
        assert restored.uploaded_by == sample_document_uploaded.uploaded_by

    def test_serialize_document_converted(self, serializer):
        event = DocumentConverted(
            event_id=uuid4(),
            aggregate_id=uuid4(),
            occurred_at=datetime.now(timezone.utc),
            version=2,
            markdown_content="# Test Content",
            sections=[{"heading": "Test", "content": "Content"}],
            metadata={"author": "test"},
            conversion_warnings=["warning1"]
        )
        
        data = serializer.serialize(event)
        
        assert data["markdown_content"] == "# Test Content"
        assert len(data["sections"]) == 1
        assert data["metadata"]["author"] == "test"

    def test_deserialize_document_converted(self, serializer):
        event = DocumentConverted(
            event_id=uuid4(),
            aggregate_id=uuid4(),
            occurred_at=datetime.now(timezone.utc),
            version=2,
            markdown_content="# Test",
            sections=[],
            metadata={},
            conversion_warnings=[]
        )
        
        data = serializer.serialize(event)
        restored = serializer.deserialize("DocumentConverted", data)
        
        assert restored.markdown_content == event.markdown_content

    def test_serialize_analysis_started(self, serializer):
        policy_id = uuid4()
        event = AnalysisStarted(
            event_id=uuid4(),
            aggregate_id=uuid4(),
            occurred_at=datetime.now(timezone.utc),
            version=3,
            policy_repository_id=policy_id,
            ai_model="gemini-pro",
            initiated_by="analyst@example.com"
        )
        
        data = serializer.serialize(event)
        
        assert data["policy_repository_id"] == str(policy_id)
        assert data["ai_model"] == "gemini-pro"

    def test_serialize_analysis_completed(self, serializer):
        event = AnalysisCompleted(
            event_id=uuid4(),
            aggregate_id=uuid4(),
            occurred_at=datetime.now(timezone.utc),
            version=4,
            findings_count=5,
            compliance_score=0.85,
            findings=[{"issue": "test issue"}],
            processing_time_ms=1500
        )
        
        data = serializer.serialize(event)
        
        assert data["findings_count"] == 5
        assert data["compliance_score"] == 0.85
        assert len(data["findings"]) == 1

    def test_serialize_feedback_generated(self, serializer):
        feedback_id = uuid4()
        event = FeedbackGenerated(
            event_id=uuid4(),
            aggregate_id=uuid4(),
            occurred_at=datetime.now(timezone.utc),
            version=1,
            feedback_id=feedback_id,
            issue_description="Missing stop loss",
            suggested_change="Add stop loss at 2%",
            confidence_score=0.9,
            policy_reference="SEC-001",
            section_reference="Risk Management"
        )
        
        data = serializer.serialize(event)
        
        assert data["feedback_id"] == str(feedback_id)
        assert data["issue_description"] == "Missing stop loss"
        assert data["confidence_score"] == 0.9

    def test_serialize_policy_repository_created(self, serializer):
        event = PolicyRepositoryCreated(
            event_id=uuid4(),
            aggregate_id=uuid4(),
            occurred_at=datetime.now(timezone.utc),
            version=1,
            name="SEC Policies",
            description="SEC compliance policies",
            created_by="admin@example.com"
        )
        
        data = serializer.serialize(event)
        
        assert data["name"] == "SEC Policies"
        assert data["description"] == "SEC compliance policies"

    def test_serialize_policy_added(self, serializer):
        policy_id = uuid4()
        event = PolicyAdded(
            event_id=uuid4(),
            aggregate_id=uuid4(),
            occurred_at=datetime.now(timezone.utc),
            version=2,
            policy_id=policy_id,
            policy_name="Risk Disclosure",
            policy_content="All risks must be disclosed",
            requirement_type="MUST",
            added_by="admin@example.com"
        )
        
        data = serializer.serialize(event)
        
        assert data["policy_id"] == str(policy_id)
        assert data["policy_name"] == "Risk Disclosure"
        assert data["requirement_type"] == "MUST"

    def test_to_json_and_from_json(self, serializer, sample_document_uploaded):
        json_str = serializer.to_json(sample_document_uploaded)
        restored = serializer.from_json("DocumentUploaded", json_str)
        
        assert restored.filename == sample_document_uploaded.filename
        assert restored.file_size_bytes == sample_document_uploaded.file_size_bytes

    def test_deserialize_unknown_event_type_raises_error(self, serializer):
        with pytest.raises(ValueError, match="Unknown event type"):
            serializer.deserialize("UnknownEvent", {})

    def test_register_custom_event_type(self, serializer, sample_document_uploaded):
        EventSerializer.register_event_type(DocumentUploaded)
        
        data = serializer.serialize(sample_document_uploaded)
        restored = serializer.deserialize("DocumentUploaded", data)
        
        assert restored.filename == sample_document_uploaded.filename

    def test_serialize_nested_uuid_in_list(self, serializer):
        uuid1 = uuid4()
        uuid2 = uuid4()
        event = AnalysisCompleted(
            event_id=uuid4(),
            aggregate_id=uuid4(),
            occurred_at=datetime.now(timezone.utc),
            version=1,
            findings_count=2,
            compliance_score=0.8,
            findings=[{"id": str(uuid1)}, {"id": str(uuid2)}],
            processing_time_ms=1000
        )
        
        data = serializer.serialize(event)
        
        assert len(data["findings"]) == 2

    def test_serialize_empty_lists_and_dicts(self, serializer):
        event = DocumentConverted(
            event_id=uuid4(),
            aggregate_id=uuid4(),
            occurred_at=datetime.now(timezone.utc),
            version=1,
            markdown_content="",
            sections=[],
            metadata={},
            conversion_warnings=[]
        )
        
        data = serializer.serialize(event)
        
        assert data["sections"] == []
        assert data["metadata"] == {}
