"""
Integration tests for document authorization (Phase 13).

Tests document-level access control with:
- User authentication via Kerberos headers
- Owner-based access control
- Group-based sharing
- Role-based permissions (ADMIN, CONTRIBUTOR, VIEWER)
- Share/make-private operations
"""

import pytest
from uuid import uuid4
from unittest.mock import AsyncMock, Mock, patch

from src.domain.aggregates.document import Document
from src.domain.aggregates.user import User
from src.domain.value_objects.user_role import UserRole
from src.domain.services.authorization_service import AuthorizationService


class TestDocumentAuthorization:
    """Test document authorization at domain level."""
    
    @pytest.fixture
    def owner_user(self):
        """Create document owner user."""
        user = User.register(
            kerberos_id="owner1",
            groups={"team-a", "team-b"},
            display_name="Owner User",
            email="owner@example.com",
            initial_roles={UserRole.CONTRIBUTOR}
        )
        return user
    
    @pytest.fixture
    def group_member_user(self):
        """Create user who is member of team-a."""
        user = User.register(
            kerberos_id="user01",
            groups={"team-a"},
            display_name="Team Member",
            email="member@example.com",
            initial_roles={UserRole.CONTRIBUTOR}
        )
        return user
    
    @pytest.fixture
    def non_member_user(self):
        """Create user who is not in any shared groups."""
        user = User.register(
            kerberos_id="user02",
            groups={"team-c"},
            display_name="Non Member",
            email="nonmember@example.com",
            initial_roles={UserRole.CONTRIBUTOR}
        )
        return user
    
    @pytest.fixture
    def admin_user(self):
        """Create admin user."""
        user = User.register(
            kerberos_id="admin1",
            groups={"admin-group"},
            display_name="Admin User",
            email="admin@example.com",
            initial_roles={UserRole.ADMIN}
        )
        return user
    
    @pytest.fixture
    def viewer_user(self):
        """Create viewer user (read-only)."""
        user = User.register(
            kerberos_id="view01",
            groups={"team-a"},
            display_name="Viewer User",
            email="viewer@example.com",
            initial_roles={UserRole.VIEWER}
        )
        return user
    
    @pytest.fixture
    def private_document(self, owner_user):
        """Create a private document owned by owner1."""
        doc = Document.upload(
            filename="test.pdf",
            content=b"test content",
            content_type="application/pdf",
            uploaded_by=owner_user.kerberos_id
        )
        return doc
    
    @pytest.fixture
    def shared_document(self, owner_user):
        """Create a document shared with team-a."""
        doc = Document.upload(
            filename="shared.pdf",
            content=b"shared content",
            content_type="application/pdf",
            uploaded_by=owner_user.kerberos_id
        )
        doc.share_with_group("team-a", owner_user.kerberos_id)
        return doc
    
    @pytest.fixture
    def auth_service(self):
        """Create AuthorizationService instance."""
        return AuthorizationService()
    
    def test_owner_can_view_own_document(self, auth_service, owner_user, private_document):
        """Owner can always view their own document."""
        assert auth_service.can_view_document(owner_user, private_document)
    
    def test_owner_can_edit_own_document(self, auth_service, owner_user, private_document):
        """Owner can always edit their own document."""
        assert auth_service.can_edit_document(owner_user, private_document)
    
    def test_owner_can_share_own_document(self, auth_service, owner_user, private_document):
        """Owner can share their own document."""
        assert auth_service.can_share_document(owner_user, private_document)
    
    def test_owner_can_delete_own_document(self, auth_service, owner_user, private_document):
        """Owner can delete their own document."""
        assert auth_service.can_delete_document(owner_user, private_document)
    
    def test_non_owner_cannot_view_private_document(
        self, auth_service, non_member_user, private_document
    ):
        """Non-owner cannot view private document."""
        assert not auth_service.can_view_document(non_member_user, private_document)
    
    def test_non_owner_cannot_edit_document(
        self, auth_service, non_member_user, private_document
    ):
        """Non-owner cannot edit document."""
        assert not auth_service.can_edit_document(non_member_user, private_document)
    
    def test_non_owner_cannot_share_document(
        self, auth_service, non_member_user, private_document
    ):
        """Non-owner cannot share document."""
        assert not auth_service.can_share_document(non_member_user, private_document)
    
    def test_non_owner_cannot_delete_document(
        self, auth_service, non_member_user, private_document
    ):
        """Non-owner cannot delete document."""
        assert not auth_service.can_delete_document(non_member_user, private_document)
    
    def test_group_member_can_view_shared_document(
        self, auth_service, group_member_user, shared_document
    ):
        """Group member can view document shared with their group."""
        assert auth_service.can_view_document(group_member_user, shared_document)
    
    def test_group_member_cannot_edit_shared_document(
        self, auth_service, group_member_user, shared_document
    ):
        """Group member cannot edit document they don't own."""
        assert not auth_service.can_edit_document(group_member_user, shared_document)
    
    def test_non_group_member_cannot_view_shared_document(
        self, auth_service, non_member_user, shared_document
    ):
        """User not in shared group cannot view document."""
        assert not auth_service.can_view_document(non_member_user, shared_document)
    
    def test_admin_can_view_any_document(
        self, auth_service, admin_user, private_document
    ):
        """Admin can view any document regardless of ownership."""
        assert auth_service.can_view_document(admin_user, private_document)
    
    def test_admin_can_edit_any_document(
        self, auth_service, admin_user, private_document
    ):
        """Admin can edit any document regardless of ownership."""
        assert auth_service.can_edit_document(admin_user, private_document)
    
    def test_admin_can_share_any_document(
        self, auth_service, admin_user, private_document
    ):
        """Admin can share any document regardless of ownership."""
        assert auth_service.can_share_document(admin_user, private_document)
    
    def test_admin_can_delete_any_document(
        self, auth_service, admin_user, private_document
    ):
        """Admin can delete any document regardless of ownership."""
        assert auth_service.can_delete_document(admin_user, private_document)
    
    def test_viewer_can_view_shared_document(
        self, auth_service, viewer_user, shared_document
    ):
        """Viewer can view documents shared with their group."""
        assert auth_service.can_view_document(viewer_user, shared_document)
    
    def test_viewer_cannot_edit_document(
        self, auth_service, viewer_user, shared_document
    ):
        """Viewer cannot edit documents (lacks EDIT permission)."""
        assert not auth_service.can_edit_document(viewer_user, shared_document)
    
    def test_viewer_cannot_share_document(
        self, auth_service, viewer_user):
        """Viewer cannot share documents (lacks SHARE permission)."""
        # Create document owned by viewer
        doc = Document.upload(
            filename="viewer_doc.pdf",
            content=b"content",
            content_type="application/pdf",
            uploaded_by=viewer_user.kerberos_id
        )
        assert not auth_service.can_share_document(viewer_user, doc)
    
    def test_viewer_cannot_delete_document(
        self, auth_service, viewer_user
    ):
        """Viewer cannot delete documents (lacks DELETE permission)."""
        # Create document owned by viewer
        doc = Document.upload(
            filename="viewer_doc.pdf",
            content=b"content",
            content_type="application/pdf",
            uploaded_by=viewer_user.kerberos_id
        )
        assert not auth_service.can_delete_document(viewer_user, doc)
    
    def test_share_document_changes_visibility(self, owner_user):
        """Sharing document changes visibility to 'group'."""
        doc = Document.upload(
            filename="test.pdf",
            content=b"content",
            content_type="application/pdf",
            uploaded_by=owner_user.kerberos_id
        )
        assert doc.visibility == "private"
        
        doc.share_with_group("team-a", owner_user.kerberos_id)
        assert doc.visibility == "group"
        assert "team-a" in doc.shared_with_groups
    
    def test_make_private_removes_all_groups(self, owner_user):
        """Making document private removes all group shares."""
        doc = Document.upload(
            filename="test.pdf",
            content=b"content",
            content_type="application/pdf",
            uploaded_by=owner_user.kerberos_id
        )
        doc.share_with_group("team-a", owner_user.kerberos_id)
        doc.share_with_group("team-b", owner_user.kerberos_id)
        
        assert len(doc.shared_with_groups) == 2
        
        doc.make_private(owner_user.kerberos_id)
        assert doc.visibility == "private"
        assert len(doc.shared_with_groups) == 0
    
    def test_share_with_multiple_groups(self, owner_user, group_member_user):
        """Document can be shared with multiple groups."""
        doc = Document.upload(
            filename="test.pdf",
            content=b"content",
            content_type="application/pdf",
            uploaded_by=owner_user.kerberos_id
        )
        
        doc.share_with_group("team-a", owner_user.kerberos_id)
        doc.share_with_group("team-b", owner_user.kerberos_id)
        
        assert len(doc.shared_with_groups) == 2
        assert "team-a" in doc.shared_with_groups
        assert "team-b" in doc.shared_with_groups
    
    def test_can_view_checks_group_membership(self, owner_user):
        """can_view correctly checks if user is in any shared group."""
        doc = Document.upload(
            filename="test.pdf",
            content=b"content",
            content_type="application/pdf",
            uploaded_by=owner_user.kerberos_id
        )
        doc.share_with_group("team-a", owner_user.kerberos_id)
        
        # User in team-a can view
        assert doc.can_view("user01", {"team-a", "team-c"})
        
        # User not in team-a cannot view
        assert not doc.can_view("user02", {"team-b", "team-c"})
        
        # Owner can always view
        assert doc.can_view(owner_user.kerberos_id, set())


class TestDocumentAuthorizationEvents:
    """Test that sharing operations generate correct domain events."""
    
    def test_share_with_group_generates_event(self):
        """Sharing with group generates DocumentSharedWithGroup event."""
        from src.domain.events.document_events import DocumentSharedWithGroup
        
        doc = Document.upload(
            filename="test.pdf",
            content=b"content",
            content_type="application/pdf",
            uploaded_by="owner1"
        )
        doc.clear_events()  # Clear upload events
        
        doc.share_with_group("team-a", "owner1")
        
        events = doc.collect_events()
        assert len(events) == 1
        assert isinstance(events[0], DocumentSharedWithGroup)
        assert events[0].group == "team-a"
        assert events[0].shared_by == "owner1"
    
    def test_make_private_generates_event(self):
        """Making document private generates DocumentMadePrivate event."""
        from src.domain.events.document_events import DocumentMadePrivate
        
        doc = Document.upload(
            filename="test.pdf",
            content=b"content",
            content_type="application/pdf",
            uploaded_by="owner1"
        )
        doc.share_with_group("team-a", "owner1")
        doc.clear_events()  # Clear previous events
        
        doc.make_private("owner1")
        
        events = doc.collect_events()
        assert len(events) == 1
        assert isinstance(events[0], DocumentMadePrivate)
        assert events[0].changed_by == "owner1"
    
    def test_document_uploaded_includes_owner(self):
        """DocumentUploaded event includes owner_kerberos_id."""
        from src.domain.events.document_events import DocumentUploaded
        
        doc = Document.upload(
            filename="test.pdf",
            content=b"content",
            content_type="application/pdf",
            uploaded_by="owner1"
        )
        
        events = doc.collect_events()
        upload_event = next(e for e in events if isinstance(e, DocumentUploaded))
        assert upload_event.owner_kerberos_id == "owner1"


class TestDocumentRepositorySerialization:
    """Test that DocumentRepository correctly serializes access control fields."""
    
    @pytest.mark.asyncio
    async def test_serialize_includes_ownership_fields(self):
        """Serialization includes owner, visibility, and shared groups."""
        from src.infrastructure.repositories.document_repository import DocumentRepository
        from src.infrastructure.persistence.snapshot_store import InMemorySnapshotStore
        
        # Create mock event store
        mock_event_store = AsyncMock()
        snapshot_store = InMemorySnapshotStore()
        
        repo = DocumentRepository(mock_event_store, snapshot_store)
        
        # Create document with ownership
        doc = Document.upload(
            filename="test.pdf",
            content=b"content",
            content_type="application/pdf",
            uploaded_by="owner1"
        )
        doc.share_with_group("team-a", "owner1")
        
        # Serialize
        state = repo._serialize_aggregate(doc)
        
        assert state["owner_kerberos_id"] == "owner1"
        assert state["visibility"] == "group"
        assert "team-a" in state["shared_with_groups"]
    
    @pytest.mark.asyncio
    async def test_deserialize_restores_ownership_fields(self):
        """Deserialization restores owner, visibility, and shared groups."""
        from src.infrastructure.repositories.document_repository import DocumentRepository
        from src.infrastructure.persistence.snapshot_store import InMemorySnapshotStore
        from uuid import UUID
        
        # Create mock event store
        mock_event_store = AsyncMock()
        snapshot_store = InMemorySnapshotStore()
        
        repo = DocumentRepository(mock_event_store, snapshot_store)
        
        # Create state dict
        doc_id = uuid4()
        state = {
            "id": str(doc_id),
            "version": 2,
            "filename": "test.pdf",
            "original_format": "application/pdf",
            "markdown_content": "# Test",
            "sections": [],
            "metadata": {},
            "status": "uploaded",
            "policy_repository_id": None,
            "compliance_score": None,
            "findings": [],
            "current_version": {"major": 1, "minor": 0, "patch": 0},
            "owner_kerberos_id": "owner1",
            "visibility": "group",
            "shared_with_groups": ["team-a", "team-b"],
        }
        
        # Deserialize
        doc = repo._deserialize_aggregate(state)
        
        assert doc.owner_kerberos_id == "owner1"
        assert doc.visibility == "group"
        assert "team-a" in doc.shared_with_groups
        assert "team-b" in doc.shared_with_groups
        assert len(doc.shared_with_groups) == 2
    
    @pytest.mark.asyncio
    async def test_deserialize_handles_old_snapshots_without_ownership(self):
        """Deserialization handles old snapshots missing ownership fields."""
        from src.infrastructure.repositories.document_repository import DocumentRepository
        from src.infrastructure.persistence.snapshot_store import InMemorySnapshotStore
        from uuid import UUID
        
        # Create mock event store
        mock_event_store = AsyncMock()
        snapshot_store = InMemorySnapshotStore()
        
        repo = DocumentRepository(mock_event_store, snapshot_store)
        
        # Create state dict WITHOUT ownership fields (old snapshot)
        doc_id = uuid4()
        state = {
            "id": str(doc_id),
            "version": 1,
            "filename": "old.pdf",
            "original_format": "application/pdf",
            "markdown_content": "# Old",
            "sections": [],
            "metadata": {},
            "status": "uploaded",
            "policy_repository_id": None,
            "compliance_score": None,
            "findings": [],
            "current_version": {"major": 1, "minor": 0, "patch": 0},
            # No owner_kerberos_id, visibility, shared_with_groups
        }
        
        # Deserialize - should not raise error
        doc = repo._deserialize_aggregate(state)
        
        # Should have default values
        assert doc.owner_kerberos_id == "system"
        assert doc.visibility == "private"
        assert len(doc.shared_with_groups) == 0


# Note: API-level integration tests would require FastAPI test client
# and would be in a separate test file (test_api_document_authorization.py)
# These would test:
# - Authentication middleware extracting Kerberos headers
# - get_current_user dependency
# - Authorization checks in each endpoint
# - Share/make-private endpoints
# - Proper 401/403 responses
