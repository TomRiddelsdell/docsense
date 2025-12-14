"""User role enumeration for RBAC."""

from enum import Enum


class UserRole(Enum):
    """User roles for Role-Based Access Control.
    
    Roles define what permissions a user has in the system:
    - VIEWER: Can view assigned documents
    - CONTRIBUTOR: Can upload and edit own documents
    - ADMIN: Can manage all documents and users
    - AUDITOR: Read-only access to audit logs
    """
    
    VIEWER = "viewer"
    CONTRIBUTOR = "contributor"
    ADMIN = "admin"
    AUDITOR = "auditor"
    
    def __str__(self) -> str:
        return self.value
    
    @classmethod
    def from_string(cls, role_str: str) -> "UserRole":
        """Convert string to UserRole enum.
        
        Args:
            role_str: Role name as string
            
        Returns:
            UserRole enum value
            
        Raises:
            ValueError: If role_str is not a valid role
        """
        try:
            return cls(role_str.lower())
        except ValueError:
            valid_roles = ", ".join([r.value for r in cls])
            raise ValueError(
                f"Invalid role '{role_str}'. Must be one of: {valid_roles}"
            )
