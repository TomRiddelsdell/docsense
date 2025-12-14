"""Tests for AuthorizationService."""

import pytest
from uuid import uuid4

from src.domain.aggregates.document import Document
from src.domain.aggregates.user import User
from src.domain.services.authorization_service import AuthorizationService, ROLE_PERMISSIONS
from src.domain.value_objects.permission import Permission
from src.domain.value_objects.user_role import UserRole


class TestRolePermissions:
    """Tests for role-to-permission mappings."""
    
    def test_viewer_has_read_only_permissions(self):
        """Test VIEWER role has read-only permissions."""
        permissions = ROLE_PERMISSIONS[UserRole.VIEWER]
        
        assert Permission.VIEW in permissions
        assert Permission.ANALYZE in permissions
        assert Permission.EXPORT in permissions
        
        # Cannot write or admin
        assert Permission.EDIT not in permissions
        assert Permission.DELETE not in permissions
        assert Permission.SHARE not in permissions
        assert Permission.MANAGE_USERS not in permissions
        assert Permission.VIEW_AUDIT not in permissions
    
    def test_contributor_has_edit_permissions(self):
        """Test CONTRIBUTOR role has edit and share permissions."""
        permissions = ROLE_PERMISSIONS[UserRole.CONTRIBUTOR]
        
        assert Permission.VIEW in permissions
        assert Permission.EDIT in permissions
        assert Permission.SHARE in permissions
        assert Permission.ANALYZE in permissions
        assert Permission.EXPORT in permissions
        
        # Cannot delete or admin
        assert Permission.DELETE not in permissions
        assert Permission.MANAGE_USERS not in permissions
        assert Permission.VIEW_AUDIT not in permissions
    
    def test_admin_has_all_permissions(self):
        """Test ADMIN role has all permissions."""
        permissions = ROLE_PERMISSIONS[UserRole.ADMIN]
        
        assert Permission.VIEW in permissions
        assert Permission.EDIT in permissions
        assert Permission.DELETE in permissions
        assert Permission.SHARE in permissions
        assert Permission.ANALYZE in permissions
        assert Permission.EXPORT in permissions
        assert Permission.VIEW_AUDIT in permissions
        assert Permission.MANAGE_USERS in permissions
    
    def test_auditor_has_audit_permissions(self):
        """Test AUDITOR role has view and audit permissions."""
        permissions = ROLE_PERMISSIONS[UserRole.AUDITOR]
        
        assert Permission.VIEW in permissions
        assert Permission.VIEW_AUDIT in permissions
        
        # Cannot write
        assert Permission.EDIT not in permissions
        assert Permission.DELETE not in permissions
        assert Permission.SHARE not in permissions
        assert Permission.MANAGE_USERS not in permissions


class TestAuthorizationService:
    """Tests for AuthorizationService permission checks."""
    
    @pytest.fixture
    def auth_service(self):
        """Create AuthorizationService instance."""
        return AuthorizationService()
    
    @pytest.fixture
    def viewer_user(self):
        """Create a user with VIEWER role."""
        user = User.register(
            kerberos_id="vuser1",
            groups={"equity-trading"},
            display_name="Viewer User",
            email="viewer@example.com",
        )
        user.grant_role(UserRole.VIEWER)
        return user
    
    @pytest.fixture
    def contributor_user(self):
        """Create a user with CONTRIBUTOR role."""
        user = User.register(
            kerberos_id="cuser1",
            groups={"equity-trading"},
            display_name="Contributor User",
            email="contrib@example.com",
        )
        user.grant_role(UserRole.CONTRIBUTOR)
        return user
    
    @pytest.fixture
    def admin_user(self):
        """Create a user with ADMIN role."""
        user = User.register(
            kerberos_id="admin1",
            groups={"admin-group"},
            display_name="Admin User",
            email="admin@example.com",
        )
        user.grant_role(UserRole.ADMIN)
        return user
    
    @pytest.fixture
    def document_owner(self):
        """Create a document owner with CONTRIBUTOR role."""
        user = User.register(
            kerberos_id="owner1",
            groups={"equity-trading", "risk-mgmt"},
            display_name="Owner User",
            email="owner@example.com",
        )
        user.grant_role(UserRole.CONTRIBUTOR)
        return user
    
    @pytest.fixture
    def private_document(self, document_owner):
        """Create a private document."""
        return Document.upload(
            document_id=uuid4(),
            filename="private_algo.pdf",
            content=b"private content",
            original_format="application/pdf",
            uploaded_by=document_owner.kerberos_id,
        )
    
    @pytest.fixture
    def shared_document(self, document_owner):
        """Create a document shared with equity-trading group."""
        doc = Document.upload(
            document_id=uuid4(),
            filename="shared_algo.pdf",
            content=b"shared content",
            original_format="application/pdf",
            uploaded_by=document_owner.kerberos_id,
        )
        doc.share_with_group("equity-trading", document_owner.kerberos_id)
        return doc
    
    def test_get_user_permissions_viewer(self, auth_service, viewer_user):
        """Test getting permissions for VIEWER role."""
        permissions = auth_service.get_user_permissions(viewer_user)
        
        assert Permission.VIEW in permissions
        assert Permission.ANALYZE in permissions
        assert Permission.EXPORT in permissions
        assert Permission.EDIT not in permissions
    
    def test_get_user_permissions_contributor(self, auth_service, contributor_user):
        """Test getting permissions for CONTRIBUTOR role."""
        permissions = auth_service.get_user_permissions(contributor_user)
        
        assert Permission.VIEW in permissions
        assert Permission.EDIT in permissions
        assert Permission.SHARE in permissions
        assert Permission.DELETE not in permissions
    
    def test_get_user_permissions_admin_gets_all(self, auth_service, admin_user):
        """Test ADMIN gets all permissions."""
        permissions = auth_service.get_user_permissions(admin_user)
        
        # Should have all permissions
        assert len(permissions) == len(Permission)
        for perm in Permission:
            assert perm in permissions
    
    def test_has_permission_viewer_has_view(self, auth_service, viewer_user):
        """Test VIEWER has VIEW permission."""
        assert auth_service.has_permission(viewer_user, Permission.VIEW) is True
    
    def test_has_permission_viewer_no_edit(self, auth_service, viewer_user):
        """Test VIEWER does not have EDIT permission."""
        assert auth_service.has_permission(viewer_user, Permission.EDIT) is False
    
    def test_has_permission_admin_has_all(self, auth_service, admin_user):
        """Test ADMIN has all permissions."""
        for perm in Permission:
            assert auth_service.has_permission(admin_user, perm) is True
    
    def test_can_view_document_owner_can_view(
        self, auth_service, document_owner, private_document
    ):
        """Test document owner can view their own document."""
        assert auth_service.can_view_document(document_owner, private_document) is True
    
    def test_can_view_document_group_member_shared(
        self, auth_service, viewer_user, shared_document
    ):
        """Test group member can view shared document."""
        # viewer_user is in equity-trading group
        assert auth_service.can_view_document(viewer_user, shared_document) is True
    
    def test_can_view_document_non_member_private(
        self, auth_service, viewer_user, private_document
    ):
        """Test non-member cannot view private document."""
        # viewer_user is not the owner
        assert auth_service.can_view_document(viewer_user, private_document) is False
    
    def test_can_view_document_admin_can_view_all(
        self, auth_service, admin_user, private_document
    ):
        """Test ADMIN can view any document."""
        assert auth_service.can_view_document(admin_user, private_document) is True
    
    def test_can_edit_document_owner_can_edit(
        self, auth_service, document_owner, private_document
    ):
        """Test document owner can edit their own document."""
        assert auth_service.can_edit_document(document_owner, private_document) is True
    
    def test_can_edit_document_non_owner_cannot_edit(
        self, auth_service, contributor_user, private_document
    ):
        """Test non-owner cannot edit document."""
        # contributor_user has EDIT permission but is not owner
        assert auth_service.can_edit_document(contributor_user, private_document) is False
    
    def test_can_edit_document_viewer_cannot_edit(
        self, auth_service, viewer_user, private_document
    ):
        """Test VIEWER cannot edit (lacks EDIT permission)."""
        assert auth_service.can_edit_document(viewer_user, private_document) is False
    
    def test_can_edit_document_admin_can_edit_all(
        self, auth_service, admin_user, private_document
    ):
        """Test ADMIN can edit any document."""
        assert auth_service.can_edit_document(admin_user, private_document) is True
    
    def test_can_share_document_owner_can_share(
        self, auth_service, document_owner, private_document
    ):
        """Test document owner can share their own document."""
        assert auth_service.can_share_document(document_owner, private_document) is True
    
    def test_can_share_document_non_owner_cannot_share(
        self, auth_service, contributor_user, private_document
    ):
        """Test non-owner cannot share document."""
        # contributor_user has SHARE permission but is not owner
        assert auth_service.can_share_document(contributor_user, private_document) is False
    
    def test_can_share_document_viewer_cannot_share(
        self, auth_service, viewer_user, shared_document
    ):
        """Test VIEWER cannot share (lacks SHARE permission)."""
        assert auth_service.can_share_document(viewer_user, shared_document) is False
    
    def test_can_share_document_admin_can_share_all(
        self, auth_service, admin_user, private_document
    ):
        """Test ADMIN can share any document."""
        assert auth_service.can_share_document(admin_user, private_document) is True
    
    def test_can_delete_document_owner_with_delete_permission(
        self, auth_service, document_owner, private_document
    ):
        """Test document owner cannot delete (CONTRIBUTOR lacks DELETE)."""
        # CONTRIBUTOR role doesn't have DELETE permission
        assert auth_service.can_delete_document(document_owner, private_document) is False
    
    def test_can_delete_document_admin_can_delete_all(
        self, auth_service, admin_user, private_document
    ):
        """Test ADMIN can delete any document."""
        assert auth_service.can_delete_document(admin_user, private_document) is True
    
    def test_can_delete_document_non_owner_cannot_delete(
        self, auth_service, admin_user, private_document
    ):
        """Test that only ADMIN role has DELETE permission."""
        # Create user with all roles except ADMIN
        user = User.register(
            kerberos_id="duser1",
            groups=set(),
            display_name="Deleter",
            email="deleter@example.com",
        )
        user.grant_role(UserRole.CONTRIBUTOR)
        
        assert auth_service.can_delete_document(user, private_document) is False


class TestPermissionValueObject:
    """Tests for Permission enum."""
    
    def test_permission_values(self):
        """Test Permission enum has expected values."""
        assert Permission.VIEW.value == "view"
        assert Permission.EDIT.value == "edit"
        assert Permission.DELETE.value == "delete"
        assert Permission.SHARE.value == "share"
        assert Permission.ANALYZE.value == "analyze"
        assert Permission.EXPORT.value == "export"
        assert Permission.VIEW_AUDIT.value == "view_audit"
        assert Permission.MANAGE_USERS.value == "manage_users"
    
    def test_from_string_valid(self):
        """Test from_string converts valid strings."""
        assert Permission.from_string("view") == Permission.VIEW
        assert Permission.from_string("EDIT") == Permission.EDIT
        assert Permission.from_string("Delete") == Permission.DELETE
    
    def test_from_string_invalid(self):
        """Test from_string raises ValueError for invalid strings."""
        with pytest.raises(ValueError, match="Invalid permission 'invalid'"):
            Permission.from_string("invalid")
