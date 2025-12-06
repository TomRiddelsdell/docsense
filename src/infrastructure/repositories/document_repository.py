from typing import Type, Optional
from uuid import UUID

from src.domain.aggregates.document import Document
from src.domain.value_objects import DocumentStatus, VersionNumber
from src.infrastructure.repositories.base import Repository


class DocumentRepository(Repository[Document]):
    def _aggregate_type(self) -> Type[Document]:
        return Document

    def _aggregate_type_name(self) -> str:
        return "Document"

    def _serialize_aggregate(self, aggregate: Document) -> dict:
        return {
            "id": str(aggregate.id),
            "version": aggregate.version,
            "filename": aggregate.filename,
            "original_format": aggregate.original_format,
            "markdown_content": aggregate.markdown_content,
            "sections": aggregate.sections,
            "status": aggregate.status.value,
            "compliance_score": aggregate.compliance_score,
            "current_version": {
                "major": aggregate.current_version.major,
                "minor": aggregate.current_version.minor,
                "patch": aggregate.current_version.patch,
            }
        }

    def _deserialize_aggregate(self, state: dict) -> Document:
        document = Document.__new__(Document)
        document._id = UUID(state["id"])
        document._version = state["version"]
        document._pending_events = []
        document._filename = state["filename"]
        document._original_format = state["original_format"]
        document._markdown_content = state["markdown_content"]
        document._sections = state["sections"]
        document._metadata = {}
        document._status = DocumentStatus(state["status"])
        document._compliance_score = state.get("compliance_score")
        document._findings = []
        document._policy_repository_id = None
        version_data = state["current_version"]
        document._current_version = VersionNumber(
            version_data["major"],
            version_data["minor"],
            version_data["patch"]
        )
        return document
