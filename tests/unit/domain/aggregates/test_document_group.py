"""Unit tests for DocumentGroup aggregate."""

import pytest
from datetime import datetime
from uuid import uuid4

from src.domain.aggregates.document_group import DocumentGroup
from src.domain.events.document_group_events import (
    DocumentGroupCreated,
    DocumentAddedToGroup,
    DocumentRemovedFromGroup,
    PrimaryDocumentSet,
    GroupAnalysisStarted,
    GroupAnalysisCompleted,
    GroupCompletenessChanged,
    DocumentGroupDeleted,
)
from src.domain.exceptions import (
    InvalidGroupOperation,
    DocumentAlreadyInGroup,
    DocumentNotInGroup,
)
from src.domain.value_objects.group_status import GroupStatus


class TestDocumentGroupCreation:
    """Tests for DocumentGroup creation."""
    
    def test_create_group_with_valid_data(self):
        """Should create group with valid name and owner."""
        group_id = uuid4()
        name = "Trading Strategy v2.0"
        description = "Main methodology with appendices"
        owner = "usr001"
        
        group = DocumentGroup.create(
            group_id=group_id,
            name=name,
            description=description,
            owner_kerberos_id=owner,
        )
        
        assert group.id == group_id
        assert group.name == name
        assert group.description == description
        assert group.owner_kerberos_id == owner
        assert group.status == GroupStatus.PENDING
        assert group.member_count == 0
        assert not group.has_primary
        assert group.created_at is not None
        
        # Verify event
        events = group.pending_events
        assert len(events) == 1
        assert isinstance(events[0], DocumentGroupCreated)
        assert events[0].name == name
    
    def test_create_group_with_minimal_data(self):
        """Should create group with just name and owner."""
        group = DocumentGroup.create(
            group_id=uuid4(),
            name="Test Group",
            description="",
            owner_kerberos_id="usr001",
        )
        
        assert group.name == "Test Group"
        assert group.description == ""
    
    def test_create_group_trims_whitespace(self):
        """Should trim whitespace from name and description."""
        group = DocumentGroup.create(
            group_id=uuid4(),
            name="  Test Group  ",
            description="  Some description  ",
            owner_kerberos_id="usr001",
        )
        
        assert group.name == "Test Group"
        assert group.description == "Some description"
    
    def test_create_group_with_empty_name_fails(self):
        """Should reject empty group name."""
        with pytest.raises(InvalidGroupOperation, match="name cannot be empty"):
            DocumentGroup.create(
                group_id=uuid4(),
                name="",
                description="Test",
                owner_kerberos_id="usr001",
            )
    
    def test_create_group_with_whitespace_only_name_fails(self):
        """Should reject whitespace-only name."""
        with pytest.raises(InvalidGroupOperation, match="name cannot be empty"):
            DocumentGroup.create(
                group_id=uuid4(),
                name="   ",
                description="Test",
                owner_kerberos_id="usr001",
            )
    
    def test_create_group_with_long_name_fails(self):
        """Should reject name longer than 255 characters."""
        long_name = "A" * 256
        
        with pytest.raises(InvalidGroupOperation, match="cannot exceed 255 characters"):
            DocumentGroup.create(
                group_id=uuid4(),
                name=long_name,
                description="Test",
                owner_kerberos_id="usr001",
            )
    
    def test_create_group_with_invalid_owner_fails(self):
        """Should reject invalid Kerberos ID."""
        with pytest.raises(InvalidGroupOperation, match="must be exactly 6 characters"):
            DocumentGroup.create(
                group_id=uuid4(),
                name="Test Group",
                description="Test",
                owner_kerberos_id="invalid",  # Not 6 chars
            )


class TestDocumentGroupMembership:
    """Tests for adding/removing documents."""
    
    @pytest.fixture
    def group(self):
        """Create a test group."""
        return DocumentGroup.create(
            group_id=uuid4(),
            name="Test Group",
            description="Test",
            owner_kerberos_id="usr001",
        )
    
    def test_add_document_to_group(self, group):
        """Should add document to group."""
        doc_id = uuid4()
        
        group.add_document(doc_id)
        
        assert doc_id in group.member_document_ids
        assert group.member_count == 1
        
        # Verify event
        events = group.pending_events
        assert len(events) == 2  # Created + Added
        assert isinstance(events[1], DocumentAddedToGroup)
        assert events[1].document_id == doc_id
    
    def test_add_multiple_documents(self, group):
        """Should add multiple documents."""
        doc1 = uuid4()
        doc2 = uuid4()
        doc3 = uuid4()
        
        group.add_document(doc1)
        group.add_document(doc2)
        group.add_document(doc3)
        
        assert group.member_count == 3
        assert doc1 in group.member_document_ids
        assert doc2 in group.member_document_ids
        assert doc3 in group.member_document_ids
    
    def test_add_duplicate_document_fails(self, group):
        """Should reject adding same document twice."""
        doc_id = uuid4()
        
        group.add_document(doc_id)
        
        with pytest.raises(InvalidGroupOperation, match="already in group"):
            group.add_document(doc_id)
    
    def test_remove_document_from_group(self, group):
        """Should remove document from group."""
        doc_id = uuid4()
        group.add_document(doc_id)
        
        group.remove_document(doc_id)
        
        assert doc_id not in group.member_document_ids
        assert group.member_count == 0
        
        # Verify event
        events = group.pending_events
        assert isinstance(events[2], DocumentRemovedFromGroup)
        assert events[2].document_id == doc_id
    
    def test_remove_nonexistent_document_fails(self, group):
        """Should reject removing document not in group."""
        doc_id = uuid4()
        
        with pytest.raises(InvalidGroupOperation, match="not in group"):
            group.remove_document(doc_id)
    
    def test_remove_primary_document_fails(self, group):
        """Should reject removing the primary document."""
        doc_id = uuid4()
        group.add_document(doc_id)
        group.set_primary_document(doc_id)
        
        with pytest.raises(InvalidGroupOperation, match="Cannot remove primary"):
            group.remove_document(doc_id)


class TestPrimaryDocumentDesignation:
    """Tests for setting primary document."""
    
    @pytest.fixture
    def group_with_documents(self):
        """Create group with multiple documents."""
        group = DocumentGroup.create(
            group_id=uuid4(),
            name="Test Group",
            description="Test",
            owner_kerberos_id="usr001",
        )
        
        doc1 = uuid4()
        doc2 = uuid4()
        doc3 = uuid4()
        
        group.add_document(doc1)
        group.add_document(doc2)
        group.add_document(doc3)
        
        return group, doc1, doc2, doc3
    
    def test_set_primary_document(self, group_with_documents):
        """Should set primary document."""
        group, doc1, doc2, doc3 = group_with_documents
        
        group.set_primary_document(doc1)
        
        assert group.primary_document_id == doc1
        assert group.has_primary
        
        # Verify event
        events = group.pending_events
        assert isinstance(events[-1], PrimaryDocumentSet)
        assert events[-1].document_id == doc1
        assert events[-1].previous_primary_id is None
    
    def test_change_primary_document(self, group_with_documents):
        """Should change primary document."""
        group, doc1, doc2, doc3 = group_with_documents
        
        group.set_primary_document(doc1)
        group.set_primary_document(doc2)
        
        assert group.primary_document_id == doc2
        
        # Verify last event
        events = group.pending_events
        assert isinstance(events[-1], PrimaryDocumentSet)
        assert events[-1].document_id == doc2
        assert events[-1].previous_primary_id == doc1
    
    def test_set_primary_to_same_document_is_noop(self, group_with_documents):
        """Should not emit event when setting same primary."""
        group, doc1, doc2, doc3 = group_with_documents
        
        group.set_primary_document(doc1)
        event_count = len(group.pending_events)
        
        group.set_primary_document(doc1)  # Same document
        
        assert len(group.pending_events) == event_count  # No new event
    
    def test_set_primary_for_nonmember_fails(self):
        """Should reject setting primary for document not in group."""
        group = DocumentGroup.create(
            group_id=uuid4(),
            name="Test Group",
            description="Test",
            owner_kerberos_id="usr001",
        )
        
        doc_id = uuid4()
        
        with pytest.raises(InvalidGroupOperation, match="not in group"):
            group.set_primary_document(doc_id)


class TestGroupAnalysis:
    """Tests for group analysis workflow."""
    
    @pytest.fixture
    def group_with_documents(self):
        """Create group with documents ready for analysis."""
        group = DocumentGroup.create(
            group_id=uuid4(),
            name="Test Group",
            description="Test",
            owner_kerberos_id="usr001",
        )
        
        group.add_document(uuid4())
        group.add_document(uuid4())
        
        return group
    
    def test_start_analysis(self, group_with_documents):
        """Should start group analysis."""
        group = group_with_documents
        analysis_id = uuid4()
        
        group.start_analysis(analysis_id, "usr001")
        
        # Verify event
        events = group.pending_events
        assert isinstance(events[-1], GroupAnalysisStarted)
        assert events[-1].analysis_id == analysis_id
        assert events[-1].initiated_by == "usr001"
        assert events[-1].document_count == 2
    
    def test_start_analysis_on_empty_group_fails(self):
        """Should reject analysis of empty group."""
        group = DocumentGroup.create(
            group_id=uuid4(),
            name="Test Group",
            description="Test",
            owner_kerberos_id="usr001",
        )
        
        with pytest.raises(InvalidGroupOperation, match="Cannot analyze empty group"):
            group.start_analysis(uuid4(), "usr001")
    
    def test_complete_analysis_with_no_external_refs(self, group_with_documents):
        """Should complete analysis marking group as complete."""
        group = group_with_documents
        analysis_id = uuid4()
        
        group.start_analysis(analysis_id, "usr001")
        group.complete_analysis(
            analysis_id=analysis_id,
            is_complete=True,
            internal_references_count=5,
            external_references=[],
            completeness_score=1.0,
        )
        
        assert group.status == GroupStatus.COMPLETE
        
        # Verify events
        events = group.pending_events
        assert isinstance(events[-2], GroupAnalysisCompleted)
        assert isinstance(events[-1], GroupCompletenessChanged)
        assert events[-1].new_status == "complete"
    
    def test_complete_analysis_with_external_refs(self, group_with_documents):
        """Should mark group incomplete when external refs found."""
        group = group_with_documents
        analysis_id = uuid4()
        
        group.start_analysis(analysis_id, "usr001")
        group.complete_analysis(
            analysis_id=analysis_id,
            is_complete=False,
            internal_references_count=3,
            external_references=["Corporate Actions Manual", "Data Agreement"],
            completeness_score=0.7,
        )
        
        assert group.status == GroupStatus.INCOMPLETE
        
        # Verify status change event
        events = group.pending_events
        assert isinstance(events[-1], GroupCompletenessChanged)
        assert events[-1].new_status == "incomplete"
        assert "2 external references" in events[-1].reason
    
    def test_complete_analysis_with_wrong_id_fails(self, group_with_documents):
        """Should reject completion for wrong analysis ID."""
        group = group_with_documents
        analysis_id = uuid4()
        wrong_id = uuid4()
        
        group.start_analysis(analysis_id, "usr001")
        
        with pytest.raises(InvalidGroupOperation, match="not in progress"):
            group.complete_analysis(
                analysis_id=wrong_id,  # Wrong ID
                is_complete=True,
                internal_references_count=0,
                external_references=[],
                completeness_score=1.0,
            )
    
    def test_complete_analysis_with_invalid_score_fails(self, group_with_documents):
        """Should reject invalid completeness score."""
        group = group_with_documents
        analysis_id = uuid4()
        
        group.start_analysis(analysis_id, "usr001")
        
        with pytest.raises(InvalidGroupOperation, match="must be between 0.0 and 1.0"):
            group.complete_analysis(
                analysis_id=analysis_id,
                is_complete=True,
                internal_references_count=0,
                external_references=[],
                completeness_score=1.5,  # Invalid
            )


class TestGroupDeletion:
    """Tests for group deletion."""
    
    def test_delete_group(self):
        """Should delete group."""
        group = DocumentGroup.create(
            group_id=uuid4(),
            name="Test Group",
            description="Test",
            owner_kerberos_id="usr001",
        )
        
        group.delete(deleted_by="usr001", reason="No longer needed")
        
        # Verify event
        events = group.pending_events
        assert isinstance(events[-1], DocumentGroupDeleted)
        assert events[-1].deleted_by == "usr001"
        assert events[-1].reason == "No longer needed"


class TestEventReconstitution:
    """Tests for reconstituting aggregate from events."""
    
    def test_reconstitute_from_events(self):
        """Should rebuild aggregate state from events."""
        group_id = uuid4()
        doc1 = uuid4()
        doc2 = uuid4()
        analysis_id = uuid4()
        
        # Create events
        events = [
            DocumentGroupCreated(
                aggregate_id=group_id,
                name="Test Group",
                description="Description",
                owner_kerberos_id="usr001",
            ),
            DocumentAddedToGroup(
                aggregate_id=group_id,
                document_id=doc1,
            ),
            DocumentAddedToGroup(
                aggregate_id=group_id,
                document_id=doc2,
            ),
            PrimaryDocumentSet(
                aggregate_id=group_id,
                document_id=doc1,
            ),
            GroupAnalysisStarted(
                aggregate_id=group_id,
                analysis_id=analysis_id,
                initiated_by="usr001",
                document_count=2,
            ),
            GroupAnalysisCompleted(
                aggregate_id=group_id,
                analysis_id=analysis_id,
                is_complete=True,
                internal_references_count=3,
                external_references=[],
                completeness_score=1.0,
            ),
            GroupCompletenessChanged(
                aggregate_id=group_id,
                old_status="pending",
                new_status="complete",
                reason="Analysis completed",
            ),
        ]
        
        # Reconstitute
        group = DocumentGroup.reconstitute(events)
        
        # Verify state
        assert group.id == group_id
        assert group.name == "Test Group"
        assert group.description == "Description"
        assert group.owner_kerberos_id == "usr001"
        assert group.member_count == 2
        assert doc1 in group.member_document_ids
        assert doc2 in group.member_document_ids
        assert group.primary_document_id == doc1
        assert group.status == GroupStatus.COMPLETE
        assert len(group.pending_events) == 0  # No pending events after reconstitution


class TestGroupStatusValueObject:
    """Tests for GroupStatus value object."""
    
    def test_group_status_values(self):
        """Should have correct status values."""
        assert GroupStatus.PENDING.value == "pending"
        assert GroupStatus.COMPLETE.value == "complete"
        assert GroupStatus.INCOMPLETE.value == "incomplete"
    
    def test_from_analysis_with_no_external_refs(self):
        """Should return COMPLETE when no external refs."""
        status = GroupStatus.from_analysis(has_external_references=False)
        assert status == GroupStatus.COMPLETE
    
    def test_from_analysis_with_external_refs(self):
        """Should return INCOMPLETE when external refs exist."""
        status = GroupStatus.from_analysis(has_external_references=True)
        assert status == GroupStatus.INCOMPLETE
    
    def test_str_representation(self):
        """Should convert to string value."""
        assert str(GroupStatus.PENDING) == "pending"
        assert str(GroupStatus.COMPLETE) == "complete"
