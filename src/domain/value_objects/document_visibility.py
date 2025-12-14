"""Document visibility enumeration."""

from enum import Enum


class DocumentVisibility(Enum):
    """Document visibility levels for access control.
    
    Visibility levels:
    - PRIVATE: Only the document owner can view (default)
    - GROUP: Owner and members of shared groups can view
    - ORGANIZATION: All authenticated users can view (future)
    - PUBLIC: Anonymous access allowed (future)
    """
    
    PRIVATE = "private"
    GROUP = "group"
    ORGANIZATION = "organization"
    PUBLIC = "public"
    
    def __str__(self) -> str:
        return self.value
    
    @classmethod
    def from_string(cls, visibility_str: str) -> "DocumentVisibility":
        """Convert string to DocumentVisibility enum.
        
        Args:
            visibility_str: Visibility level as string
            
        Returns:
            DocumentVisibility enum value
            
        Raises:
            ValueError: If visibility_str is not a valid visibility level
        """
        try:
            return cls(visibility_str.lower())
        except ValueError:
            valid_levels = ", ".join([v.value for v in cls])
            raise ValueError(
                f"Invalid visibility '{visibility_str}'. Must be one of: {valid_levels}"
            )
