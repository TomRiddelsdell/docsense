from typing import List, Dict, Any, Optional
from uuid import UUID

from .base import Aggregate
from src.domain.events.base import DomainEvent
from src.domain.events.document_events import (
    DocumentUploaded,
    DocumentConverted,
    DocumentExported,
    SemanticIRCurationStarted,
    SemanticIRCurated,
    SemanticIRCurationFailed,
)
from src.domain.events.analysis_events import (
    AnalysisStarted,
    AnalysisCompleted,
    AnalysisFailed,
    AnalysisReset,
)
from src.domain.value_objects import DocumentStatus, VersionNumber
from src.domain.exceptions.document_exceptions import InvalidDocumentState
from src.domain.exceptions.analysis_exceptions import AnalysisInProgress, AnalysisNotStarted


class Document(Aggregate):
    def __init__(self, document_id: UUID):
        super().__init__(document_id)
        self._init_state()

    def _init_state(self) -> None:
        self._filename: str = ""
        self._original_format: str = ""
        self._markdown_content: str = ""
        self._sections: List[Dict[str, Any]] = []
        self._metadata: Dict[str, Any] = {}
        self._current_version: VersionNumber = VersionNumber(1, 0, 0)
        self._status: DocumentStatus = DocumentStatus.DRAFT
        self._policy_repository_id: Optional[UUID] = None
        self._compliance_score: Optional[float] = None
        self._findings: List[Dict[str, Any]] = []
        # NEW: Access control fields
        self._owner_kerberos_id: str = ""
        self._visibility: str = "private"  # Will use DocumentVisibility enum
        self._shared_with_groups: set = set()

    @property
    def filename(self) -> str:
        return self._filename

    @property
    def original_format(self) -> str:
        return self._original_format

    @property
    def markdown_content(self) -> str:
        return self._markdown_content

    @property
    def sections(self) -> List[Dict[str, Any]]:
        return self._sections.copy()

    @property
    def status(self) -> DocumentStatus:
        return self._status

    @property
    def compliance_score(self) -> Optional[float]:
        return self._compliance_score

    @property
    def current_version(self) -> VersionNumber:
        return self._current_version

    @property
    def owner_kerberos_id(self) -> str:
        """Get the document owner's Kerberos ID."""
        return self._owner_kerberos_id
    
    @property
    def visibility(self) -> str:
        """Get the document visibility level."""
        return self._visibility
    
    @property
    def shared_with_groups(self) -> set:
        """Get the groups this document is shared with."""
        return self._shared_with_groups.copy()

    @classmethod
    def upload(
        cls,
        document_id: UUID,
        filename: str,
        content: bytes,
        original_format: str,
        uploaded_by: str,
    ) -> "Document":
        document = cls(document_id)
        document._apply_event(
            DocumentUploaded(
                aggregate_id=document_id,
                filename=filename,
                original_format=original_format,
                file_size_bytes=len(content),
                uploaded_by=uploaded_by,
                owner_kerberos_id=uploaded_by,  # NEW: Set owner
            )
        )
        return document

    def convert(
        self,
        markdown_content: str,
        sections: List[Dict[str, Any]],
        metadata: Dict[str, Any],
        conversion_warnings: List[str] = None,
    ) -> None:
        if self._status != DocumentStatus.UPLOADED:
            raise InvalidDocumentState(
                document_id=self._id,
                current_status=self._status.value,
                required_status=DocumentStatus.UPLOADED.value,
                operation="convert"
            )
        self._apply_event(
            DocumentConverted(
                aggregate_id=self._id,
                markdown_content=markdown_content,
                sections=sections,
                metadata=metadata,
                conversion_warnings=conversion_warnings or [],
            )
        )

    def start_analysis(
        self,
        policy_repository_id: UUID,
        ai_model: str,
        initiated_by: str,
    ) -> None:
        if self._status == DocumentStatus.ANALYZING:
            raise AnalysisInProgress(document_id=self._id)
        if self._status not in (DocumentStatus.CONVERTED, DocumentStatus.ANALYZED, DocumentStatus.EXPORTED, DocumentStatus.FAILED):
            raise InvalidDocumentState(
                document_id=self._id,
                current_status=self._status.value,
                required_status=f"{DocumentStatus.CONVERTED.value}, {DocumentStatus.ANALYZED.value}, {DocumentStatus.EXPORTED.value}, or {DocumentStatus.FAILED.value}",
                operation="start_analysis"
            )
        self._apply_event(
            AnalysisStarted(
                aggregate_id=self._id,
                policy_repository_id=policy_repository_id,
                ai_model=ai_model,
                initiated_by=initiated_by,
            )
        )

    def complete_analysis(
        self,
        findings_count: int,
        compliance_score: float,
        findings: List[Dict[str, Any]],
        processing_time_ms: int,
    ) -> None:
        if self._status != DocumentStatus.ANALYZING:
            raise AnalysisNotStarted(document_id=self._id)
        self._apply_event(
            AnalysisCompleted(
                aggregate_id=self._id,
                findings_count=findings_count,
                compliance_score=compliance_score,
                findings=findings,
                processing_time_ms=processing_time_ms,
            )
        )

    def fail_analysis(
        self,
        reason: str,
        error_code: str = "",
        retryable: bool = True,
    ) -> None:
        if self._status != DocumentStatus.ANALYZING:
            raise AnalysisNotStarted(document_id=self._id)
        self._apply_event(
            AnalysisFailed(
                aggregate_id=self._id,
                error_message=reason,
                error_code=error_code,
                retryable=retryable,
            )
        )

    def reset_for_retry(
        self,
        reset_by: str = "system",
    ) -> None:
        if self._status not in (DocumentStatus.ANALYZING, DocumentStatus.FAILED):
            raise InvalidDocumentState(
                document_id=self._id,
                current_status=self._status.value,
                required_status=f"{DocumentStatus.ANALYZING.value} or {DocumentStatus.FAILED.value}",
                operation="reset_for_retry"
            )
        self._apply_event(
            AnalysisReset(
                aggregate_id=self._id,
                reset_by=reset_by,
                previous_status=self._status.value,
            )
        )

    def start_ir_curation(
        self,
        provider_type: str = "claude",
    ) -> None:
        """Start AI curation of semantic IR."""
        if self._status != DocumentStatus.CONVERTED:
            raise InvalidDocumentState(
                document_id=self._id,
                current_status=self._status.value,
                required_status=DocumentStatus.CONVERTED.value,
                operation="start_ir_curation"
            )
        self._apply_event(
            SemanticIRCurationStarted(
                aggregate_id=self._id,
                provider_type=provider_type,
            )
        )

    def complete_ir_curation(
        self,
        definitions_added: int,
        definitions_removed: int,
        validation_issues_found: int,
        curation_metadata: Dict[str, Any],
    ) -> None:
        """Complete AI curation of semantic IR."""
        self._apply_event(
            SemanticIRCurated(
                aggregate_id=self._id,
                definitions_added=definitions_added,
                definitions_removed=definitions_removed,
                validation_issues_found=validation_issues_found,
                curation_metadata=curation_metadata,
            )
        )

    def fail_ir_curation(
        self,
        error_message: str,
    ) -> None:
        """Mark AI curation as failed."""
        self._apply_event(
            SemanticIRCurationFailed(
                aggregate_id=self._id,
                error_message=error_message,
            )
        )

    def export(
        self,
        export_format: str,
        exported_by: str,
    ) -> None:
        if self._status not in (DocumentStatus.ANALYZED, DocumentStatus.EXPORTED):
            raise InvalidDocumentState(
                document_id=self._id,
                current_status=self._status.value,
                required_status=f"{DocumentStatus.ANALYZED.value} or {DocumentStatus.EXPORTED.value}",
                operation="export"
            )
        self._apply_event(
            DocumentExported(
                aggregate_id=self._id,
                export_format=export_format,
                exported_by=exported_by,
                version_number=str(self._current_version),
            )
        )
    
    def share_with_group(self, group: str, shared_by: str) -> None:
        """Share document with a group.
        
        Automatically changes visibility to GROUP if currently PRIVATE.
        
        Args:
            group: Group name to share with
            shared_by: Kerberos ID of user sharing the document
        """
        from src.domain.events.document_events import DocumentSharedWithGroup
        
        if group not in self._shared_with_groups:
            self._apply_event(
                DocumentSharedWithGroup(
                    aggregate_id=self._id,
                    group=group,
                    shared_by=shared_by,
                )
            )
    
    def make_private(self, changed_by: str) -> None:
        """Remove all group sharing and set visibility to private.
        
        Args:
            changed_by: Kerberos ID of user making the document private
        """
        from src.domain.events.document_events import DocumentMadePrivate
        
        if self._visibility != "private" or self._shared_with_groups:
            self._apply_event(
                DocumentMadePrivate(
                    aggregate_id=self._id,
                    changed_by=changed_by,
                )
            )
    
    def can_view(self, user_kerberos_id: str, user_groups: set) -> bool:
        """Check if a user can view this document.
        
        Args:
            user_kerberos_id: User's Kerberos ID
            user_groups: Set of groups the user belongs to
            
        Returns:
            True if user can view the document
        """
        # Owner can always view
        if self._owner_kerberos_id == user_kerberos_id:
            return True
        
        # Check visibility level
        if self._visibility == "private":
            return False
        elif self._visibility == "group":
            # User must be in at least one shared group
            return bool(self._shared_with_groups & user_groups)
        elif self._visibility == "organization":
            # All authenticated users can view (future)
            return True
        elif self._visibility == "public":
            # Anonymous access (future)
            return True
        
        return False

    def _when(self, event: DomainEvent) -> None:
        from src.domain.events.document_events import DocumentSharedWithGroup, DocumentMadePrivate
        
        if isinstance(event, DocumentUploaded):
            self._filename = event.filename
            self._original_format = event.original_format
            self._status = DocumentStatus.UPLOADED
            self._owner_kerberos_id = event.owner_kerberos_id  # NEW
        elif isinstance(event, DocumentConverted):
            self._markdown_content = event.markdown_content
            self._sections = event.sections
            self._metadata = event.metadata
            self._status = DocumentStatus.CONVERTED
        elif isinstance(event, DocumentSharedWithGroup):
            self._shared_with_groups.add(event.group)
            self._visibility = "group"  # Automatically change to GROUP
        elif isinstance(event, DocumentMadePrivate):
            self._shared_with_groups.clear()
            self._visibility = "private"
        elif isinstance(event, AnalysisStarted):
            self._policy_repository_id = event.policy_repository_id
            self._status = DocumentStatus.ANALYZING
        elif isinstance(event, AnalysisCompleted):
            self._compliance_score = event.compliance_score
            self._findings = event.findings
            self._status = DocumentStatus.ANALYZED
        elif isinstance(event, AnalysisFailed):
            self._status = DocumentStatus.FAILED
        elif isinstance(event, AnalysisReset):
            self._status = DocumentStatus.CONVERTED
        elif isinstance(event, DocumentExported):
            self._status = DocumentStatus.EXPORTED
            self._current_version = self._current_version.increment_patch()
        elif isinstance(event, SemanticIRCurationStarted):
            # Curation happens in background, status remains CONVERTED
            pass
        elif isinstance(event, SemanticIRCurated):
            # Curation complete, status remains CONVERTED
            pass
        elif isinstance(event, SemanticIRCurationFailed):
            # Curation failed, status remains CONVERTED
            pass
