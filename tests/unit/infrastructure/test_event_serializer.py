import pytest
from enum import Enum
from uuid import uuid4
from datetime import datetime, timezone

from src.infrastructure.persistence.event_serializer import EventSerializer
from src.infrastructure.converters.base import DocumentFormat
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

    def test_serialize_enum_in_nested_dict(self, serializer):
        """Test that Enum values in nested dicts are serialized to their values.
        
        This covers the bug where DocumentFormat enum in metadata caused
        'Object of type DocumentFormat is not JSON serializable' error.
        """
        event = DocumentConverted(
            event_id=uuid4(),
            aggregate_id=uuid4(),
            occurred_at=datetime.now(timezone.utc),
            version=1,
            markdown_content="# Test",
            sections=[],
            metadata={
                "title": "Test Document",
                "original_format": DocumentFormat.PDF,
                "page_count": 10
            },
            conversion_warnings=[]
        )
        
        data = serializer.serialize(event)
        
        assert data["metadata"]["original_format"] == "pdf"
        assert data["metadata"]["title"] == "Test Document"
        assert data["metadata"]["page_count"] == 10

    def test_serialize_enum_in_list(self, serializer):
        """Test that Enum values in lists are serialized to their values."""
        event = DocumentConverted(
            event_id=uuid4(),
            aggregate_id=uuid4(),
            occurred_at=datetime.now(timezone.utc),
            version=1,
            markdown_content="# Test",
            sections=[
                {"format": DocumentFormat.MARKDOWN},
                {"format": DocumentFormat.PDF}
            ],
            metadata={},
            conversion_warnings=[]
        )
        
        data = serializer.serialize(event)
        
        assert data["sections"][0]["format"] == "md"
        assert data["sections"][1]["format"] == "pdf"

    def test_serialize_deeply_nested_enum(self, serializer):
        """Test that Enum values in deeply nested structures are serialized."""
        event = DocumentConverted(
            event_id=uuid4(),
            aggregate_id=uuid4(),
            occurred_at=datetime.now(timezone.utc),
            version=1,
            markdown_content="# Test",
            sections=[],
            metadata={
                "nested": {
                    "deeply": {
                        "format": DocumentFormat.WORD
                    }
                }
            },
            conversion_warnings=[]
        )
        
        data = serializer.serialize(event)
        
        assert data["metadata"]["nested"]["deeply"]["format"] == "docx"

    def test_serialize_all_document_formats(self, serializer):
        """Test all DocumentFormat enum values serialize correctly."""
        for doc_format in DocumentFormat:
            event = DocumentConverted(
                event_id=uuid4(),
                aggregate_id=uuid4(),
                occurred_at=datetime.now(timezone.utc),
                version=1,
                markdown_content="# Test",
                sections=[],
                metadata={"original_format": doc_format},
                conversion_warnings=[]
            )
            
            data = serializer.serialize(event)
            
            assert data["metadata"]["original_format"] == doc_format.value


class TestEventSerializerRoundTrip:
    """Round-trip serialization tests to ensure serialize/deserialize symmetry."""
    
    @pytest.fixture
    def serializer(self):
        return EventSerializer()

    def test_round_trip_document_uploaded(self, serializer):
        """Test serialize then deserialize produces equivalent event."""
        original = DocumentUploaded(
            event_id=uuid4(),
            aggregate_id=uuid4(),
            occurred_at=datetime.now(timezone.utc),
            version=1,
            filename="test.pdf",
            original_format="pdf",
            file_size_bytes=2048,
            uploaded_by="user@example.com"
        )
        
        data = serializer.serialize(original)
        restored = serializer.deserialize("DocumentUploaded", data)
        
        assert restored.event_id == original.event_id
        assert restored.aggregate_id == original.aggregate_id
        assert restored.filename == original.filename
        assert restored.original_format == original.original_format
        assert restored.file_size_bytes == original.file_size_bytes
        assert restored.uploaded_by == original.uploaded_by

    def test_round_trip_document_converted_with_metadata(self, serializer):
        """Test round-trip with complex metadata containing enums."""
        original = DocumentConverted(
            event_id=uuid4(),
            aggregate_id=uuid4(),
            occurred_at=datetime.now(timezone.utc),
            version=2,
            markdown_content="# Trading Algorithm\n\nTest content",
            sections=[
                {"id": "1", "title": "Introduction", "content": "Test"},
                {"id": "2", "title": "Parameters", "content": "Params"}
            ],
            metadata={
                "title": "Trading Doc",
                "author": "Analyst",
                "original_format": DocumentFormat.PDF,
                "page_count": 15
            },
            conversion_warnings=["Some images skipped"]
        )
        
        data = serializer.serialize(original)
        restored = serializer.deserialize("DocumentConverted", data)
        
        assert restored.event_id == original.event_id
        assert restored.markdown_content == original.markdown_content
        assert len(restored.sections) == 2
        assert restored.metadata["title"] == "Trading Doc"
        assert restored.metadata["original_format"] == "pdf"
        assert restored.conversion_warnings == ["Some images skipped"]

    def test_round_trip_analysis_started(self, serializer):
        """Test round-trip with UUID fields."""
        policy_id = uuid4()
        original = AnalysisStarted(
            event_id=uuid4(),
            aggregate_id=uuid4(),
            occurred_at=datetime.now(timezone.utc),
            version=3,
            policy_repository_id=policy_id,
            ai_model="gemini-pro",
            initiated_by="analyst@example.com"
        )
        
        data = serializer.serialize(original)
        restored = serializer.deserialize("AnalysisStarted", data)
        
        assert restored.event_id == original.event_id
        assert restored.policy_repository_id == original.policy_repository_id
        assert restored.ai_model == original.ai_model

    def test_round_trip_analysis_completed_with_nested_uuids(self, serializer):
        """Test round-trip with nested UUID in findings."""
        finding_id = uuid4()
        original = AnalysisCompleted(
            event_id=uuid4(),
            aggregate_id=uuid4(),
            occurred_at=datetime.now(timezone.utc),
            version=4,
            findings_count=2,
            compliance_score=0.85,
            findings=[
                {"id": str(finding_id), "issue": "Missing stop loss"},
                {"id": str(uuid4()), "issue": "No max position size"}
            ],
            processing_time_ms=1500
        )
        
        data = serializer.serialize(original)
        restored = serializer.deserialize("AnalysisCompleted", data)
        
        assert restored.event_id == original.event_id
        assert restored.findings_count == 2
        assert restored.compliance_score == 0.85
        assert len(restored.findings) == 2
        assert restored.findings[0]["id"] == str(finding_id)

    def test_round_trip_feedback_generated(self, serializer):
        """Test round-trip for FeedbackGenerated event."""
        feedback_id = uuid4()
        original = FeedbackGenerated(
            event_id=uuid4(),
            aggregate_id=uuid4(),
            occurred_at=datetime.now(timezone.utc),
            version=1,
            feedback_id=feedback_id,
            issue_description="Algorithm lacks proper risk controls",
            suggested_change="Add stop loss at 2% of portfolio value",
            confidence_score=0.92,
            policy_reference="SEC-RiskManagement-001",
            section_reference="Section 3.2"
        )
        
        data = serializer.serialize(original)
        restored = serializer.deserialize("FeedbackGenerated", data)
        
        assert restored.feedback_id == original.feedback_id
        assert restored.issue_description == original.issue_description
        assert restored.suggested_change == original.suggested_change
        assert restored.confidence_score == original.confidence_score

    def test_round_trip_policy_added(self, serializer):
        """Test round-trip for PolicyAdded event."""
        policy_id = uuid4()
        original = PolicyAdded(
            event_id=uuid4(),
            aggregate_id=uuid4(),
            occurred_at=datetime.now(timezone.utc),
            version=2,
            policy_id=policy_id,
            policy_name="Risk Disclosure Requirements",
            policy_content="All trading algorithms must disclose risk parameters",
            requirement_type="MUST",
            added_by="compliance@example.com"
        )
        
        data = serializer.serialize(original)
        restored = serializer.deserialize("PolicyAdded", data)
        
        assert restored.policy_id == original.policy_id
        assert restored.policy_name == original.policy_name
        assert restored.requirement_type == original.requirement_type

    def test_json_round_trip(self, serializer):
        """Test full JSON string round-trip."""
        original = DocumentUploaded(
            event_id=uuid4(),
            aggregate_id=uuid4(),
            occurred_at=datetime.now(timezone.utc),
            version=1,
            filename="algorithm.docx",
            original_format="docx",
            file_size_bytes=4096,
            uploaded_by="trader@example.com"
        )
        
        json_str = serializer.to_json(original)
        restored = serializer.from_json("DocumentUploaded", json_str)
        
        assert restored.event_id == original.event_id
        assert restored.filename == original.filename
        assert restored.original_format == original.original_format
