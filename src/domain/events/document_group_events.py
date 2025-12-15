"""Domain events for DocumentGroup aggregate."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List
from uuid import UUID, uuid4


@dataclass(frozen=True)
class DocumentGroupEvent:
    """Base class for DocumentGroup events."""
    
    event_id: UUID = field(default_factory=uuid4)
    occurred_at: datetime = field(default_factory=lambda: datetime.utcnow())
    aggregate_id: UUID = field(default_factory=uuid4)
    aggregate_type: str = field(default="DocumentGroup")
    version: int = field(default=1)
    
    @property
    def event_type(self) -> str:
        """Get the event type name."""
        return self.__class__.__name__


@dataclass(frozen=True)
class DocumentGroupCreated(DocumentGroupEvent):
    """Event: Document group was created.
    
    Records the initial creation of a document group by a user.
    """
    
    name: str = ""
    description: str = ""
    owner_kerberos_id: str = ""


@dataclass(frozen=True)
class DocumentAddedToGroup(DocumentGroupEvent):
    """Event: Document was added to the group.
    
    Records a document being assigned to the group for combined analysis.
    """
    
    document_id: UUID = field(default_factory=uuid4)


@dataclass(frozen=True)
class DocumentRemovedFromGroup(DocumentGroupEvent):
    """Event: Document was removed from the group.
    
    Records a document being unassigned from the group.
    """
    
    document_id: UUID = field(default_factory=uuid4)


@dataclass(frozen=True)
class PrimaryDocumentSet(DocumentGroupEvent):
    """Event: Primary document was designated.
    
    Marks one document as the main methodology within the group.
    """
    
    document_id: UUID = field(default_factory=uuid4)
    previous_primary_id: UUID | None = None


@dataclass(frozen=True)
class GroupAnalysisStarted(DocumentGroupEvent):
    """Event: Group analysis was initiated.
    
    Records the start of combined analysis for all documents in the group.
    """
    
    analysis_id: UUID = field(default_factory=uuid4)
    initiated_by: str = ""
    document_count: int = 0


@dataclass(frozen=True)
class GroupAnalysisCompleted(DocumentGroupEvent):
    """Event: Group analysis finished.
    
    Records the completion of analysis with results about cross-references.
    """
    
    analysis_id: UUID = field(default_factory=uuid4)
    is_complete: bool = False
    internal_references_count: int = 0
    external_references: List[str] = field(default_factory=list)
    completeness_score: float = 0.0


@dataclass(frozen=True)
class GroupCompletenessChanged(DocumentGroupEvent):
    """Event: Group completeness status changed.
    
    Records a change in the group's completeness status based on validation.
    """
    
    old_status: str = ""
    new_status: str = ""
    reason: str = ""


@dataclass(frozen=True)
class DocumentGroupDeleted(DocumentGroupEvent):
    """Event: Document group was deleted.
    
    Records deletion of the group (documents remain unchanged).
    """
    
    deleted_by: str = ""
    reason: str = ""
