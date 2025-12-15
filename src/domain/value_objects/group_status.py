"""Document Group Status value object."""

from enum import Enum


class GroupStatus(str, Enum):
    """Status of a document group's completeness.
    
    Tracks whether all references within the group are resolved.
    """
    
    PENDING = "pending"
    """Group created but not yet analyzed."""
    
    COMPLETE = "complete"
    """All internal references resolve, no external dependencies."""
    
    INCOMPLETE = "incomplete"
    """Contains unresolved references to external documents."""
    
    def __str__(self) -> str:
        return self.value
    
    @classmethod
    def from_analysis(cls, has_external_references: bool) -> "GroupStatus":
        """Determine status from analysis results.
        
        Args:
            has_external_references: Whether analysis found external refs
            
        Returns:
            COMPLETE if no external refs, INCOMPLETE otherwise
        """
        return cls.INCOMPLETE if has_external_references else cls.COMPLETE
