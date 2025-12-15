"""DocumentGroup aggregate for multi-document analysis.

This module implements the DocumentGroup aggregate root which manages
collections of related documents (e.g., main methodology + appendices).
Groups enable comprehensive self-containment validation by analyzing
all related documents together.

Reference: ADR-010 Document Group for Multi-Document Analysis
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from src.domain.aggregates.base import Aggregate
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


class DocumentGroup(Aggregate):
    """Aggregate root for document groups.
    
    A DocumentGroup represents a collection of related documents that should
    be analyzed together. Common use cases:
    - Main methodology document + appendices
    - Strategy document + governance framework + data agreements
    - Index calculation document + corporate actions manual
    
    The group maintains:
    - List of member documents
    - Primary document designation (main methodology)
    - Completeness status (based on cross-reference validation)
    - Analysis results
    
    Business Rules:
    - Groups must have a name and owner
    - At least one document required before analysis
    - Primary document must be a group member
    - Cannot add same document twice
    - Cannot remove primary document without setting new primary first
    """
    
    def __init__(self, group_id: UUID):
        """Initialize a new DocumentGroup aggregate.
        
        Args:
            group_id: Unique identifier for the group
        """
        super().__init__(group_id)
        self._init_state()
    
    def _init_state(self) -> None:
        """Initialize aggregate state."""
        self._name: str = ""
        self._description: str = ""
        self._owner_kerberos_id: str = ""
        self._primary_document_id: Optional[UUID] = None
        self._member_document_ids: List[UUID] = []
        self._status: GroupStatus = GroupStatus.PENDING
        self._created_at: Optional[datetime] = None
        self._updated_at: Optional[datetime] = None
        self._last_analysis_id: Optional[UUID] = None
    
    # =========================================================================
    # Properties
    # =========================================================================
    
    @property
    def name(self) -> str:
        """Get group name."""
        return self._name
    
    @property
    def description(self) -> str:
        """Get group description."""
        return self._description
    
    @property
    def owner_kerberos_id(self) -> str:
        """Get owner's Kerberos ID."""
        return self._owner_kerberos_id
    
    @property
    def primary_document_id(self) -> Optional[UUID]:
        """Get primary document ID."""
        return self._primary_document_id
    
    @property
    def member_document_ids(self) -> List[UUID]:
        """Get list of member document IDs."""
        return self._member_document_ids.copy()
    
    @property
    def status(self) -> GroupStatus:
        """Get group completeness status."""
        return self._status
    
    @property
    def created_at(self) -> Optional[datetime]:
        """Get creation timestamp."""
        return self._created_at
    
    @property
    def updated_at(self) -> Optional[datetime]:
        """Get last update timestamp."""
        return self._updated_at
    
    @property
    def member_count(self) -> int:
        """Get count of documents in the group."""
        return len(self._member_document_ids)
    
    @property
    def has_primary(self) -> bool:
        """Check if a primary document is set."""
        return self._primary_document_id is not None
    
    # =========================================================================
    # Factory Methods
    # =========================================================================
    
    @classmethod
    def create(
        cls,
        group_id: UUID,
        name: str,
        description: str,
        owner_kerberos_id: str,
    ) -> "DocumentGroup":
        """Create a new document group.
        
        Args:
            group_id: Unique identifier for the group
            name: Human-readable group name
            description: Optional description of the group's purpose
            owner_kerberos_id: Kerberos ID of the creating user
            
        Returns:
            New DocumentGroup instance
            
        Raises:
            DomainError: If name is empty or owner is invalid
        """
        if not name or not name.strip():
            raise InvalidGroupOperation("Group name cannot be empty")
        
        if len(name) > 255:
            raise InvalidGroupOperation("Group name cannot exceed 255 characters")
        
        if not owner_kerberos_id or len(owner_kerberos_id) != 6:
            raise InvalidGroupOperation("Owner Kerberos ID must be exactly 6 characters")
        
        group = cls(group_id)
        group._apply_event(
            DocumentGroupCreated(
                aggregate_id=group_id,
                name=name.strip(),
                description=description.strip() if description else "",
                owner_kerberos_id=owner_kerberos_id,
            )
        )
        return group
    
    # =========================================================================
    # Commands
    # =========================================================================
    
    def add_document(self, document_id: UUID) -> None:
        """Add a document to the group.
        
        Args:
            document_id: UUID of document to add
            
        Raises:
            DomainError: If document is already in the group
        """
        if document_id in self._member_document_ids:
            raise InvalidGroupOperation(
                f"Document {document_id} is already in group {self.id}"
            )
        
        self._apply_event(
            DocumentAddedToGroup(
                aggregate_id=self.id,
                document_id=document_id,
            )
        )
    
    def remove_document(self, document_id: UUID) -> None:
        """Remove a document from the group.
        
        Args:
            document_id: UUID of document to remove
            
        Raises:
            DomainError: If document is not in the group or is the primary
        """
        if document_id not in self._member_document_ids:
            raise InvalidGroupOperation(
                f"Document {document_id} is not in group {self.id}"
            )
        
        if document_id == self._primary_document_id:
            raise InvalidGroupOperation(
                "Cannot remove primary document. "
                "Set a new primary document first."
            )
        
        self._apply_event(
            DocumentRemovedFromGroup(
                aggregate_id=self.id,
                document_id=document_id,
            )
        )
    
    def set_primary_document(self, document_id: UUID) -> None:
        """Designate a document as the primary (main methodology).
        
        Args:
            document_id: UUID of document to make primary
            
        Raises:
            DomainError: If document is not in the group
        """
        if document_id not in self._member_document_ids:
            raise InvalidGroupOperation(
                f"Document {document_id} is not in group {self.id}. "
                "Add it to the group first."
            )
        
        if document_id == self._primary_document_id:
            # Already primary, no-op
            return
        
        self._apply_event(
            PrimaryDocumentSet(
                aggregate_id=self.id,
                document_id=document_id,
                previous_primary_id=self._primary_document_id,
            )
        )
    
    def start_analysis(
        self,
        analysis_id: UUID,
        initiated_by: str,
    ) -> None:
        """Start a combined analysis of all documents in the group.
        
        Args:
            analysis_id: Unique identifier for this analysis
            initiated_by: Kerberos ID of user starting the analysis
            
        Raises:
            DomainError: If group has no documents
        """
        if not self._member_document_ids:
            raise InvalidGroupOperation(
                f"Cannot analyze empty group {self.id}. "
                "Add at least one document first."
            )
        
        self._apply_event(
            GroupAnalysisStarted(
                aggregate_id=self.id,
                analysis_id=analysis_id,
                initiated_by=initiated_by,
                document_count=len(self._member_document_ids),
            )
        )
    
    def complete_analysis(
        self,
        analysis_id: UUID,
        is_complete: bool,
        internal_references_count: int,
        external_references: List[str],
        completeness_score: float,
    ) -> None:
        """Record the completion of a group analysis.
        
        Args:
            analysis_id: ID of the completed analysis
            is_complete: Whether all references are resolved within group
            internal_references_count: Number of valid cross-references
            external_references: List of unresolved external references
            completeness_score: 0.0-1.0 completeness score
            
        Raises:
            DomainError: If analysis_id doesn't match the pending analysis
        """
        if self._last_analysis_id != analysis_id:
            raise InvalidGroupOperation(
                f"Analysis {analysis_id} not in progress for group {self.id}"
            )
        
        if not 0.0 <= completeness_score <= 1.0:
            raise InvalidGroupOperation("Completeness score must be between 0.0 and 1.0")
        
        self._apply_event(
            GroupAnalysisCompleted(
                aggregate_id=self.id,
                analysis_id=analysis_id,
                is_complete=is_complete,
                internal_references_count=internal_references_count,
                external_references=external_references,
                completeness_score=completeness_score,
            )
        )
        
        # Update status based on analysis
        new_status = GroupStatus.from_analysis(bool(external_references))
        if new_status != self._status:
            self._update_status(
                new_status,
                f"Analysis completed: {len(external_references)} external references"
            )
    
    def _update_status(self, new_status: GroupStatus, reason: str) -> None:
        """Update group status.
        
        Args:
            new_status: New status to set
            reason: Human-readable reason for change
        """
        old_status = self._status
        
        self._apply_event(
            GroupCompletenessChanged(
                aggregate_id=self.id,
                old_status=old_status.value,
                new_status=new_status.value,
                reason=reason,
            )
        )
    
    def delete(self, deleted_by: str, reason: str = "") -> None:
        """Delete the document group.
        
        Note: This does NOT delete the member documents, only the grouping.
        
        Args:
            deleted_by: Kerberos ID of user deleting the group
            reason: Optional reason for deletion
        """
        self._apply_event(
            DocumentGroupDeleted(
                aggregate_id=self.id,
                deleted_by=deleted_by,
                reason=reason,
            )
        )
    
    # =========================================================================
    # Event Handlers
    # =========================================================================
    
    def _apply_document_group_created(self, event: DocumentGroupCreated) -> None:
        """Apply DocumentGroupCreated event."""
        self._name = event.name
        self._description = event.description
        self._owner_kerberos_id = event.owner_kerberos_id
        self._status = GroupStatus.PENDING
        self._created_at = event.occurred_at
        self._updated_at = event.occurred_at
    
    def _apply_document_added_to_group(self, event: DocumentAddedToGroup) -> None:
        """Apply DocumentAddedToGroup event."""
        self._member_document_ids.append(event.document_id)
        self._updated_at = event.occurred_at
    
    def _apply_document_removed_from_group(
        self,
        event: DocumentRemovedFromGroup
    ) -> None:
        """Apply DocumentRemovedFromGroup event."""
        self._member_document_ids.remove(event.document_id)
        self._updated_at = event.occurred_at
    
    def _apply_primary_document_set(self, event: PrimaryDocumentSet) -> None:
        """Apply PrimaryDocumentSet event."""
        self._primary_document_id = event.document_id
        self._updated_at = event.occurred_at
    
    def _apply_group_analysis_started(self, event: GroupAnalysisStarted) -> None:
        """Apply GroupAnalysisStarted event."""
        self._last_analysis_id = event.analysis_id
        self._updated_at = event.occurred_at
    
    def _apply_group_analysis_completed(
        self,
        event: GroupAnalysisCompleted
    ) -> None:
        """Apply GroupAnalysisCompleted event."""
        self._updated_at = event.occurred_at
    
    def _apply_group_completeness_changed(
        self,
        event: GroupCompletenessChanged
    ) -> None:
        """Apply GroupCompletenessChanged event."""
        self._status = GroupStatus(event.new_status)
        self._updated_at = event.occurred_at
    
    def _apply_document_group_deleted(self, event: DocumentGroupDeleted) -> None:
        """Apply DocumentGroupDeleted event."""
        # Mark as deleted (actual deletion handled by repository)
        self._updated_at = event.occurred_at
    
    def _when(self, event) -> None:
        """Route events to appropriate handlers.
        
        This method is required by the Aggregate base class and dispatches
        events to their specific handler methods.
        """
        handler_name = f"_apply_{self._to_snake_case(event.event_type)}"
        handler = getattr(self, handler_name, None)
        
        if handler:
            handler(event)
        else:
            raise NotImplementedError(
                f"No handler found for event type: {event.event_type}"
            )
    
    @staticmethod
    def _to_snake_case(text: str) -> str:
        """Convert CamelCase to snake_case."""
        import re
        return re.sub(r'(?<!^)(?=[A-Z])', '_', text).lower()
