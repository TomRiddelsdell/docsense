"""Tests for Document access control extensions."""

import pytest
from uuid import uuid4

from src.domain.aggregates.document import Document
from src.domain.events.document_events import (
    DocumentUploaded,
    DocumentSharedWithGroup,
    DocumentMadePrivate,
)
from src.domain.value_objects.document_visibility import DocumentVisibility


class TestDocumentAccessControl:
    """Tests for document ownership and access control."""
    
    def test_upload_sets_owner(self):
        """Test that uploading a document sets the owner."""
        doc_id = uuid4()
        owner_id = "jsmith"
        
        document = Document.upload(
            document_id=doc_id,
            filename="algorithm.pdf",
            content=b"test content",
            original_format="application/pdf",
            uploaded_by=owner_id,
        )
        
        assert document.owner_kerberos_id == owner_id
        assert document.visibility == "private"
        assert len(document.shared_with_groups) == 0
        
        # Check event
        event = document.pending_events[0]
        assert isinstance(event, DocumentUploaded)
        assert event.owner_kerberos_id == owner_id
    
    def test_share_with_group_adds_group(self):
        """Test sharing document with a group."""
        document = Document.upload(
            document_id=uuid4(),
            filename="algo.pdf",
            content=b"content",
            original_format="application/pdf",
            uploaded_by="jsmith",
        )
        document.clear_pending_events()
        
        document.share_with_group("equity-trading", "jsmith")
        
        assert "equity-trading" in document.shared_with_groups
        assert document.visibility == "group"
        
        # Check event
        assert len(document.pending_events) == 1
        event = document.pending_events[0]
        assert isinstance(event, DocumentSharedWithGroup)
        assert event.group == "equity-trading"
        assert event.shared_by == "jsmith"
    
    def test_share_with_group_changes_visibility_to_group(self):
        """Test that sharing changes visibility from private to group."""
        document = Document.upload(
            document_id=uuid4(),
            filename="algo.pdf",
            content=b"content",
            original_format="application/pdf",
            uploaded_by="jsmith",
        )
        
        assert document.visibility == "private"
        
        document.share_with_group("equity-trading", "jsmith")
        
        assert document.visibility == "group"
    
    def test_share_with_multiple_groups(self):
        """Test sharing document with multiple groups."""
        document = Document.upload(
            document_id=uuid4(),
            filename="algo.pdf",
            content=b"content",
            original_format="application/pdf",
            uploaded_by="jsmith",
        )
        document.clear_pending_events()
        
        document.share_with_group("equity-trading", "jsmith")
        document.share_with_group("risk-mgmt", "jsmith")
        
        assert "equity-trading" in document.shared_with_groups
        assert "risk-mgmt" in document.shared_with_groups
        assert len(document.shared_with_groups) == 2
    
    def test_share_with_group_idempotent(self):
        """Test sharing with same group twice is idempotent."""
        document = Document.upload(
            document_id=uuid4(),
            filename="algo.pdf",
            content=b"content",
            original_format="application/pdf",
            uploaded_by="jsmith",
        )
        document.share_with_group("equity-trading", "jsmith")
        document.clear_pending_events()
        
        document.share_with_group("equity-trading", "jsmith")
        
        # No new event
        assert len(document.pending_events) == 0
    
    def test_make_private_clears_groups(self):
        """Test making document private clears all groups."""
        document = Document.upload(
            document_id=uuid4(),
            filename="algo.pdf",
            content=b"content",
            original_format="application/pdf",
            uploaded_by="jsmith",
        )
        document.share_with_group("equity-trading", "jsmith")
        document.share_with_group("risk-mgmt", "jsmith")
        document.clear_pending_events()
        
        document.make_private("jsmith")
        
        assert len(document.shared_with_groups) == 0
        assert document.visibility == "private"
        
        # Check event
        assert len(document.pending_events) == 1
        event = document.pending_events[0]
        assert isinstance(event, DocumentMadePrivate)
        assert event.changed_by == "jsmith"
    
    def test_make_private_idempotent(self):
        """Test making already private document private is idempotent."""
        document = Document.upload(
            document_id=uuid4(),
            filename="algo.pdf",
            content=b"content",
            original_format="application/pdf",
            uploaded_by="jsmith",
        )
        document.clear_pending_events()
        
        # Already private with no groups
        document.make_private("jsmith")
        
        # No event since already private
        assert len(document.pending_events) == 0
    
    def test_can_view_owner_always_true(self):
        """Test that document owner can always view."""
        document = Document.upload(
            document_id=uuid4(),
            filename="algo.pdf",
            content=b"content",
            original_format="application/pdf",
            uploaded_by="jsmith",
        )
        
        assert document.can_view("jsmith", set()) is True
    
    def test_can_view_private_non_owner_false(self):
        """Test that non-owner cannot view private document."""
        document = Document.upload(
            document_id=uuid4(),
            filename="algo.pdf",
            content=b"content",
            original_format="application/pdf",
            uploaded_by="jsmith",
        )
        
        assert document.can_view("adoe", {"equity-trading"}) is False
    
    def test_can_view_group_member_true(self):
        """Test that group member can view shared document."""
        document = Document.upload(
            document_id=uuid4(),
            filename="algo.pdf",
            content=b"content",
            original_format="application/pdf",
            uploaded_by="jsmith",
        )
        document.share_with_group("equity-trading", "jsmith")
        
        # User in equity-trading can view
        assert document.can_view("adoe", {"equity-trading", "other-group"}) is True
    
    def test_can_view_non_group_member_false(self):
        """Test that non-group member cannot view shared document."""
        document = Document.upload(
            document_id=uuid4(),
            filename="algo.pdf",
            content=b"content",
            original_format="application/pdf",
            uploaded_by="jsmith",
        )
        document.share_with_group("equity-trading", "jsmith")
        
        # User not in equity-trading cannot view
        assert document.can_view("adoe", {"other-group"}) is False
    
    def test_can_view_multiple_groups(self):
        """Test access with multiple shared groups."""
        document = Document.upload(
            document_id=uuid4(),
            filename="algo.pdf",
            content=b"content",
            original_format="application/pdf",
            uploaded_by="jsmith",
        )
        document.share_with_group("equity-trading", "jsmith")
        document.share_with_group("risk-mgmt", "jsmith")
        
        # User in equity-trading can view
        assert document.can_view("adoe", {"equity-trading"}) is True
        
        # User in risk-mgmt can view
        assert document.can_view("bdoe", {"risk-mgmt"}) is True
        
        # User in neither group cannot view
        assert document.can_view("cdoe", {"other-group"}) is False
    
    def test_reconstitute_preserves_ownership(self):
        """Test that event reconstitution preserves ownership and sharing."""
        doc_id = uuid4()
        events = [
            DocumentUploaded(
                aggregate_id=doc_id,
                filename="algo.pdf",
                original_format="application/pdf",
                file_size_bytes=1024,
                uploaded_by="jsmith",
                owner_kerberos_id="jsmith",
            ),
            DocumentSharedWithGroup(
                aggregate_id=doc_id,
                group="equity-trading",
                shared_by="jsmith",
            ),
            DocumentSharedWithGroup(
                aggregate_id=doc_id,
                group="risk-mgmt",
                shared_by="jsmith",
            ),
        ]
        
        document = Document.reconstitute(events)
        
        assert document.owner_kerberos_id == "jsmith"
        assert document.visibility == "group"
        assert "equity-trading" in document.shared_with_groups
        assert "risk-mgmt" in document.shared_with_groups
        assert len(document.pending_events) == 0


class TestDocumentVisibility:
    """Tests for DocumentVisibility enum."""
    
    def test_visibility_values(self):
        """Test DocumentVisibility enum has expected values."""
        assert DocumentVisibility.PRIVATE.value == "private"
        assert DocumentVisibility.GROUP.value == "group"
        assert DocumentVisibility.ORGANIZATION.value == "organization"
        assert DocumentVisibility.PUBLIC.value == "public"
    
    def test_from_string_valid(self):
        """Test from_string converts valid strings."""
        assert DocumentVisibility.from_string("private") == DocumentVisibility.PRIVATE
        assert DocumentVisibility.from_string("GROUP") == DocumentVisibility.GROUP
        assert DocumentVisibility.from_string("Organization") == DocumentVisibility.ORGANIZATION
    
    def test_from_string_invalid(self):
        """Test from_string raises ValueError for invalid strings."""
        with pytest.raises(ValueError, match="Invalid visibility 'invalid'"):
            DocumentVisibility.from_string("invalid")
