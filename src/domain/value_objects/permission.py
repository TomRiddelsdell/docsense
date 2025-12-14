"""Permission value object for authorization."""

from enum import Enum


class Permission(str, Enum):
    """Permissions for authorization checks.
    
    Defines granular permissions that can be assigned to roles.
    Used by AuthorizationService to check user access rights.
    """
    
    VIEW = "view"
    """Permission to view documents and their content."""
    
    EDIT = "edit"
    """Permission to edit/update documents."""
    
    DELETE = "delete"
    """Permission to delete documents."""
    
    SHARE = "share"
    """Permission to share documents with groups."""
    
    ANALYZE = "analyze"
    """Permission to request AI analysis of documents."""
    
    EXPORT = "export"
    """Permission to export documents to various formats."""
    
    VIEW_AUDIT = "view_audit"
    """Permission to view audit logs."""
    
    MANAGE_USERS = "manage_users"
    """Permission to manage users and assign roles."""
    
    @classmethod
    def from_string(cls, value: str) -> "Permission":
        """Convert string to Permission enum.
        
        Args:
            value: String representation of permission
            
        Returns:
            Permission enum value
            
        Raises:
            ValueError: If permission string is invalid
        """
        normalized = value.lower().strip()
        try:
            return cls(normalized)
        except ValueError:
            valid_permissions = ", ".join([p.value for p in cls])
            raise ValueError(
                f"Invalid permission '{value}'. Valid permissions: {valid_permissions}"
            )
