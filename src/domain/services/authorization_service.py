"""Authorization service for policy-based access control."""

from typing import Set

from src.domain.aggregates.document import Document
from src.domain.aggregates.user import User
from src.domain.value_objects.permission import Permission
from src.domain.value_objects.user_role import UserRole


# Role-to-permission mappings
ROLE_PERMISSIONS: dict[UserRole, Set[Permission]] = {
    UserRole.VIEWER: {
        Permission.VIEW,
        Permission.ANALYZE,
        Permission.EXPORT,
    },
    UserRole.CONTRIBUTOR: {
        Permission.VIEW,
        Permission.EDIT,
        Permission.SHARE,
        Permission.ANALYZE,
        Permission.EXPORT,
    },
    UserRole.ADMIN: {
        Permission.VIEW,
        Permission.EDIT,
        Permission.DELETE,
        Permission.SHARE,
        Permission.ANALYZE,
        Permission.EXPORT,
        Permission.VIEW_AUDIT,
        Permission.MANAGE_USERS,
    },
    UserRole.AUDITOR: {
        Permission.VIEW,
        Permission.VIEW_AUDIT,
    },
}


class AuthorizationService:
    """Service for checking user permissions and document access.
    
    Implements Role-Based Access Control (RBAC) with document-level
    ownership rules. See ADR-021 for authorization architecture.
    
    Key Rules:
    - ADMIN role grants all permissions
    - Document owners have special privileges (view, edit, share, delete)
    - Group members can view shared documents
    - Permission checks combine role-based and document-level rules
    """
    
    def get_user_permissions(self, user: User) -> Set[Permission]:
        """Get all permissions for a user based on their roles.
        
        ADMIN role grants all permissions automatically.
        Multiple roles are combined (union of permissions).
        
        Args:
            user: User aggregate with roles
            
        Returns:
            Set of all permissions the user has
        """
        if user.has_role(UserRole.ADMIN):
            # Admin gets all permissions
            return set(Permission)
        
        permissions: Set[Permission] = set()
        for role in user.roles:
            permissions.update(ROLE_PERMISSIONS.get(role, set()))
        
        return permissions
    
    def has_permission(self, user: User, permission: Permission) -> bool:
        """Check if user has a specific permission.
        
        Args:
            user: User aggregate
            permission: Permission to check
            
        Returns:
            True if user has the permission, False otherwise
        """
        if user.has_role(UserRole.ADMIN):
            return True
        
        user_permissions = self.get_user_permissions(user)
        return permission in user_permissions
    
    def can_view_document(self, user: User, document: Document) -> bool:
        """Check if user can view a document.
        
        Rules:
        - Must have VIEW permission (role-based)
        - AND (is owner OR is group member OR is admin)
        
        Args:
            user: User aggregate
            document: Document aggregate
            
        Returns:
            True if user can view the document
        """
        # Check role-based permission first
        if not self.has_permission(user, Permission.VIEW):
            return False
        
        # Admin can view all documents
        if user.has_role(UserRole.ADMIN):
            return True
        
        # Check document-level access
        return document.can_view(user.kerberos_id, user.groups)
    
    def can_edit_document(self, user: User, document: Document) -> bool:
        """Check if user can edit a document.
        
        Rules:
        - Must have EDIT permission (role-based)
        - AND (is owner OR is admin)
        
        Args:
            user: User aggregate
            document: Document aggregate
            
        Returns:
            True if user can edit the document
        """
        # Check role-based permission first
        if not self.has_permission(user, Permission.EDIT):
            return False
        
        # Admin can edit all documents
        if user.has_role(UserRole.ADMIN):
            return True
        
        # Only owner can edit (non-admins)
        return document.owner_kerberos_id == user.kerberos_id
    
    def can_share_document(self, user: User, document: Document) -> bool:
        """Check if user can share a document.
        
        Rules:
        - Must have SHARE permission (role-based)
        - AND (is owner OR is admin)
        
        Note: Users can only share with their own groups (enforced elsewhere)
        
        Args:
            user: User aggregate
            document: Document aggregate
            
        Returns:
            True if user can share the document
        """
        # Check role-based permission first
        if not self.has_permission(user, Permission.SHARE):
            return False
        
        # Admin can share all documents
        if user.has_role(UserRole.ADMIN):
            return True
        
        # Only owner can share (non-admins)
        return document.owner_kerberos_id == user.kerberos_id
    
    def can_delete_document(self, user: User, document: Document) -> bool:
        """Check if user can delete a document.
        
        Rules:
        - Must have DELETE permission (role-based)
        - AND (is owner OR is admin)
        
        Args:
            user: User aggregate
            document: Document aggregate
            
        Returns:
            True if user can delete the document
        """
        # Check role-based permission first
        if not self.has_permission(user, Permission.DELETE):
            return False
        
        # Admin can delete all documents
        if user.has_role(UserRole.ADMIN):
            return True
        
        # Only owner can delete (non-admins)
        return document.owner_kerberos_id == user.kerberos_id
