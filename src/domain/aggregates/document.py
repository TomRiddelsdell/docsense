from typing import List, Dict, Any, Optional
from uuid import UUID

from .base import Aggregate
from src.domain.events.base import DomainEvent
from src.domain.events.document_events import (
    DocumentUploaded,
    DocumentConverted,
    DocumentExported,
)
from src.domain.events.analysis_events import (
    AnalysisStarted,
    AnalysisCompleted,
    AnalysisFailed,
)
from src.domain.value_objects import DocumentStatus, VersionNumber


class Document(Aggregate):
    def __init__(self, document_id: UUID):
        super().__init__(document_id)
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
        self._apply_event(
            AnalysisCompleted(
                aggregate_id=self._id,
                findings_count=findings_count,
                compliance_score=compliance_score,
                findings=findings,
                processing_time_ms=processing_time_ms,
            )
        )

    def export(
        self,
        export_format: str,
        exported_by: str,
    ) -> None:
        self._apply_event(
            DocumentExported(
                aggregate_id=self._id,
                export_format=export_format,
                exported_by=exported_by,
                version_number=str(self._current_version),
            )
        )

    def _when(self, event: DomainEvent) -> None:
        if isinstance(event, DocumentUploaded):
            self._filename = event.filename
            self._original_format = event.original_format
            self._status = DocumentStatus.UPLOADED
        elif isinstance(event, DocumentConverted):
            self._markdown_content = event.markdown_content
            self._sections = event.sections
            self._metadata = event.metadata
            self._status = DocumentStatus.CONVERTED
        elif isinstance(event, AnalysisStarted):
            self._policy_repository_id = event.policy_repository_id
            self._status = DocumentStatus.ANALYZING
        elif isinstance(event, AnalysisCompleted):
            self._compliance_score = event.compliance_score
            self._findings = event.findings
            self._status = DocumentStatus.ANALYZED
        elif isinstance(event, DocumentExported):
            self._status = DocumentStatus.EXPORTED
            self._current_version = self._current_version.increment_patch()
