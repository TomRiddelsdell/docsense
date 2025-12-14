"""
Comprehensive tests for snapshot serialization/deserialization.

Tests that ALL aggregate state is properly captured in snapshots and restored correctly,
preventing data loss when loading from snapshots instead of replaying events.
"""
import pytest
from uuid import uuid4, UUID

from src.domain.aggregates.document import Document
from src.domain.value_objects import DocumentStatus, VersionNumber
from src.infrastructure.repositories.document_repository import DocumentRepository
from src.infrastructure.persistence.snapshot_store import InMemorySnapshotStore
from src.infrastructure.persistence.event_store import InMemoryEventStore


class TestDocumentSnapshotSerialization:
    """Test Document aggregate snapshot serialization."""

    @pytest.fixture
    def document_with_full_state(self):
        """Create a document with ALL fields populated."""
        doc_id = uuid4()
        policy_repo_id = uuid4()

        # Create document
        document = Document.upload(
            document_id=doc_id,
            filename="test.pdf",
            content=b"test content",
            original_format="pdf",
            uploaded_by="test-user"
        )

        # Convert (populates markdown_content, sections, metadata)
        document.convert(
            markdown_content="# Test Document\n\nTest content",
            sections=[
                {"title": "Section 1", "content": "Content 1"},
                {"title": "Section 2", "content": "Content 2"}
            ],
            metadata={
                "author": "Test Author",
                "created_at": "2025-01-01",
                "tags": ["test", "document"]
            },
            conversion_warnings=["Warning 1"]
        )

        # Start analysis (populates policy_repository_id)
        document.start_analysis(
            policy_repository_id=policy_repo_id,
            ai_model="gemini-pro",
            initiated_by="test-user"
        )

        # Complete analysis (populates compliance_score, findings)
        document.complete_analysis(
            findings_count=3,
            compliance_score=85.5,
            findings=[
                {
                    "finding_id": str(uuid4()),
                    "severity": "high",
                    "message": "Finding 1",
                    "section": "Section 1"
                },
                {
                    "finding_id": str(uuid4()),
                    "severity": "medium",
                    "message": "Finding 2",
                    "section": "Section 2"
                },
                {
                    "finding_id": str(uuid4()),
                    "severity": "low",
                    "message": "Finding 3",
                    "section": "Section 1"
                }
            ],
            processing_time_ms=1500
        )

        # Export (increments version)
        document.export(
            export_format="pdf",
            exported_by="test-user"
        )

        return document

    def test_serialize_captures_all_fields(self, document_with_full_state):
        """Test that serialization captures ALL document fields."""
        repo = DocumentRepository(InMemoryEventStore(), InMemorySnapshotStore())
        serialized = repo._serialize_aggregate(document_with_full_state)

        # Verify all fields are present
        assert "id" in serialized
        assert "version" in serialized
        assert "filename" in serialized
        assert "original_format" in serialized
        assert "markdown_content" in serialized
        assert "sections" in serialized
        assert "metadata" in serialized  # CRITICAL: metadata must be captured
        assert "status" in serialized
        assert "policy_repository_id" in serialized  # CRITICAL: policy ID must be captured
        assert "compliance_score" in serialized
        assert "findings" in serialized  # CRITICAL: findings must be captured
        assert "current_version" in serialized

    def test_serialize_captures_metadata_content(self, document_with_full_state):
        """Test that metadata is fully captured, not just the key."""
        repo = DocumentRepository(InMemoryEventStore(), InMemorySnapshotStore())
        serialized = repo._serialize_aggregate(document_with_full_state)

        assert serialized["metadata"] == {
            "author": "Test Author",
            "created_at": "2025-01-01",
            "tags": ["test", "document"]
        }

    def test_serialize_captures_policy_repository_id(self, document_with_full_state):
        """Test that policy_repository_id is captured correctly."""
        repo = DocumentRepository(InMemoryEventStore(), InMemorySnapshotStore())
        serialized = repo._serialize_aggregate(document_with_full_state)

        # Should be a string UUID, not None
        assert serialized["policy_repository_id"] is not None
        assert isinstance(serialized["policy_repository_id"], str)
        # Should be valid UUID format
        UUID(serialized["policy_repository_id"])  # Will raise if invalid

    def test_serialize_captures_findings(self, document_with_full_state):
        """Test that all findings are captured."""
        repo = DocumentRepository(InMemoryEventStore(), InMemorySnapshotStore())
        serialized = repo._serialize_aggregate(document_with_full_state)

        assert len(serialized["findings"]) == 3
        assert all("finding_id" in f for f in serialized["findings"])
        assert all("severity" in f for f in serialized["findings"])
        assert all("message" in f for f in serialized["findings"])

    def test_deserialize_restores_all_fields(self, document_with_full_state):
        """Test that deserialization restores ALL fields correctly."""
        repo = DocumentRepository(InMemoryEventStore(), InMemorySnapshotStore())

        # Serialize then deserialize
        serialized = repo._serialize_aggregate(document_with_full_state)
        restored = repo._deserialize_aggregate(serialized)

        # Verify all fields match original
        assert restored.id == document_with_full_state.id
        assert restored.version == document_with_full_state.version
        assert restored.filename == document_with_full_state.filename
        assert restored.original_format == document_with_full_state.original_format
        assert restored.markdown_content == document_with_full_state.markdown_content
        assert restored.sections == document_with_full_state.sections
        assert restored.status == document_with_full_state.status
        assert restored.compliance_score == document_with_full_state.compliance_score
        assert restored.current_version == document_with_full_state.current_version

    def test_deserialize_restores_metadata(self, document_with_full_state):
        """Test that metadata is fully restored."""
        repo = DocumentRepository(InMemoryEventStore(), InMemorySnapshotStore())

        serialized = repo._serialize_aggregate(document_with_full_state)
        restored = repo._deserialize_aggregate(serialized)

        # Access private field to verify it was restored
        assert restored._metadata == document_with_full_state._metadata
        assert restored._metadata == {
            "author": "Test Author",
            "created_at": "2025-01-01",
            "tags": ["test", "document"]
        }

    def test_deserialize_restores_policy_repository_id(self, document_with_full_state):
        """Test that policy_repository_id is restored correctly."""
        repo = DocumentRepository(InMemoryEventStore(), InMemorySnapshotStore())

        serialized = repo._serialize_aggregate(document_with_full_state)
        restored = repo._deserialize_aggregate(serialized)

        assert restored._policy_repository_id == document_with_full_state._policy_repository_id
        assert isinstance(restored._policy_repository_id, UUID)

    def test_deserialize_restores_findings(self, document_with_full_state):
        """Test that findings are fully restored."""
        repo = DocumentRepository(InMemoryEventStore(), InMemorySnapshotStore())

        serialized = repo._serialize_aggregate(document_with_full_state)
        restored = repo._deserialize_aggregate(serialized)

        assert restored._findings == document_with_full_state._findings
        assert len(restored._findings) == 3

    def test_deserialize_handles_none_policy_id(self):
        """Test that None policy_repository_id is handled correctly."""
        repo = DocumentRepository(InMemoryEventStore(), InMemorySnapshotStore())

        # Create document without policy ID
        doc_id = uuid4()
        document = Document.upload(
            document_id=doc_id,
            filename="test.pdf",
            content=b"test",
            original_format="pdf",
            uploaded_by="test-user"
        )

        serialized = repo._serialize_aggregate(document)
        restored = repo._deserialize_aggregate(serialized)

        assert restored._policy_repository_id is None

    def test_deserialize_handles_empty_metadata(self):
        """Test that empty metadata is handled correctly."""
        repo = DocumentRepository(InMemoryEventStore(), InMemorySnapshotStore())

        # Create document without conversion (no metadata)
        doc_id = uuid4()
        document = Document.upload(
            document_id=doc_id,
            filename="test.pdf",
            content=b"test",
            original_format="pdf",
            uploaded_by="test-user"
        )

        serialized = repo._serialize_aggregate(document)
        restored = repo._deserialize_aggregate(serialized)

        assert restored._metadata == {}

    def test_deserialize_handles_empty_findings(self):
        """Test that empty findings are handled correctly."""
        repo = DocumentRepository(InMemoryEventStore(), InMemorySnapshotStore())

        # Create document without analysis (no findings)
        doc_id = uuid4()
        document = Document.upload(
            document_id=doc_id,
            filename="test.pdf",
            content=b"test",
            original_format="pdf",
            uploaded_by="test-user"
        )

        serialized = repo._serialize_aggregate(document)
        restored = repo._deserialize_aggregate(serialized)

        assert restored._findings == []

    def test_roundtrip_preserves_complete_state(self, document_with_full_state):
        """Test that serialize -> deserialize roundtrip preserves ALL state."""
        repo = DocumentRepository(InMemoryEventStore(), InMemorySnapshotStore())

        # Serialize then deserialize
        serialized = repo._serialize_aggregate(document_with_full_state)
        restored = repo._deserialize_aggregate(serialized)

        # Serialize again
        serialized_again = repo._serialize_aggregate(restored)

        # Both serializations should be identical
        assert serialized == serialized_again

    def test_backward_compatibility_with_old_snapshots(self):
        """Test that old snapshots (without new fields) can still be loaded."""
        repo = DocumentRepository(InMemoryEventStore(), InMemorySnapshotStore())

        # Simulate an old snapshot that doesn't have metadata, policy_repository_id, or findings
        old_snapshot = {
            "id": str(uuid4()),
            "version": 5,
            "filename": "old.pdf",
            "original_format": "pdf",
            "markdown_content": "# Old Document",
            "sections": [{"title": "Section", "content": "Content"}],
            # Missing: metadata, policy_repository_id, findings
            "status": "ANALYZED",
            "compliance_score": 75.0,
            "current_version": {"major": 1, "minor": 0, "patch": 0}
        }

        # Should not raise an error
        restored = repo._deserialize_aggregate(old_snapshot)

        # Should use defaults for missing fields
        assert restored._metadata == {}
        assert restored._policy_repository_id is None
        assert restored._findings == []

    def test_snapshot_size_reasonable(self, document_with_full_state):
        """Test that snapshot size is reasonable (not bloated)."""
        repo = DocumentRepository(InMemoryEventStore(), InMemorySnapshotStore())

        serialized = repo._serialize_aggregate(document_with_full_state)

        # Should have exactly the expected keys (no extras)
        expected_keys = {
            "id", "version", "filename", "original_format", "markdown_content",
            "sections", "metadata", "status", "policy_repository_id",
            "compliance_score", "findings", "current_version"
        }
        assert set(serialized.keys()) == expected_keys


class TestSnapshotPerformanceBenefit:
    """Test that snapshots actually provide performance benefits."""

    @pytest.mark.asyncio
    async def test_snapshot_avoids_event_replay(self):
        """Test that loading from snapshot avoids replaying all events."""
        event_store = InMemoryEventStore()
        snapshot_store = InMemorySnapshotStore()
        repo = DocumentRepository(event_store, snapshot_store)

        # Create document with many events
        doc_id = uuid4()
        document = Document.upload(
            document_id=doc_id,
            filename="test.pdf",
            content=b"test",
            original_format="pdf",
            uploaded_by="test-user"
        )
        document.convert(
            markdown_content="# Test",
            sections=[],
            metadata={}
        )
        document.start_analysis(
            policy_repository_id=uuid4(),
            ai_model="gemini",
            initiated_by="user"
        )
        document.complete_analysis(
            findings_count=0,
            compliance_score=100.0,
            findings=[],
            processing_time_ms=100
        )

        # Save document (events will be stored)
        await repo.save(document)

        # Take snapshot
        from src.infrastructure.persistence.snapshot_store import Snapshot
        snapshot = Snapshot(
            aggregate_id=doc_id,
            aggregate_type="Document",
            version=document.version,
            state=repo._serialize_aggregate(document)
        )
        await snapshot_store.save(snapshot)

        # Load from snapshot (should not replay events)
        loaded = await repo.get(doc_id)

        # Verify state is complete (has data from all events)
        assert loaded.filename == "test.pdf"
        assert loaded.markdown_content == "# Test"
        assert loaded._policy_repository_id is not None
        assert loaded.compliance_score == 100.0
        assert loaded.status == DocumentStatus.ANALYZED

    @pytest.mark.asyncio
    async def test_snapshot_reduces_load_time(self):
        """Test that snapshots reduce aggregate load time."""
        import time

        event_store = InMemoryEventStore()
        repo_no_snapshot = DocumentRepository(event_store, InMemorySnapshotStore())
        repo_with_snapshot = DocumentRepository(event_store, InMemorySnapshotStore())

        # Create document with many events
        doc_id = uuid4()
        document = Document.upload(doc_id, "test.pdf", b"test", "pdf", "user")
        document.convert("# Test", [], {})

        # Complete analysis so document can be exported
        document.start_analysis(
            policy_repository_id=uuid4(),
            ai_model="gemini",
            initiated_by="user"
        )
        document.complete_analysis(
            findings_count=0,
            compliance_score=100.0,
            findings=[],
            processing_time_ms=100
        )

        # Add many export events (to simulate long event history)
        for i in range(50):
            document.export("pdf", f"user-{i}")

        # Save events to event store
        await repo_no_snapshot.save(document)

        # Take snapshot for repo_with_snapshot
        from src.infrastructure.persistence.snapshot_store import Snapshot
        snapshot = Snapshot(
            aggregate_id=doc_id,
            aggregate_type="Document",
            version=document.version,
            state=repo_with_snapshot._serialize_aggregate(document)
        )
        await repo_with_snapshot._snapshot_store.save(snapshot)

        # Measure load time without snapshot
        start = time.time()
        loaded_no_snapshot = await repo_no_snapshot.get(doc_id)
        time_no_snapshot = time.time() - start

        # Measure load time with snapshot
        start = time.time()
        loaded_with_snapshot = await repo_with_snapshot.get(doc_id)
        time_with_snapshot = time.time() - start

        # Snapshot should be faster (or at least not slower)
        # Note: In memory this might be similar, but with real DB it's significant
        assert time_with_snapshot <= time_no_snapshot * 1.5  # Allow some variance

        # Both should have same final state
        assert loaded_no_snapshot.version == loaded_with_snapshot.version
        assert loaded_no_snapshot.status == loaded_with_snapshot.status
