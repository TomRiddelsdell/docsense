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
        """
        Serialize complete aggregate state for snapshot.

        Captures ALL fields to ensure snapshot fully represents aggregate state,
        avoiding data loss when restoring from snapshots instead of replaying events.
        """
        return {
            "id": str(aggregate.id),
            "version": aggregate.version,
            "filename": aggregate.filename,
            "original_format": aggregate.original_format,
            "markdown_content": aggregate.markdown_content,
            "sections": aggregate.sections,
            "metadata": aggregate._metadata,  # Document metadata from conversion
            "status": aggregate.status.value,
            "policy_repository_id": str(aggregate._policy_repository_id) if aggregate._policy_repository_id else None,
            "compliance_score": aggregate.compliance_score,
            "findings": aggregate._findings,  # Analysis findings
            "current_version": {
                "major": aggregate.current_version.major,
                "minor": aggregate.current_version.minor,
                "patch": aggregate.current_version.patch,
            },
            # Access control fields (Phase 13)
            "owner_kerberos_id": aggregate._owner_kerberos_id,
            "visibility": aggregate._visibility,
            "shared_with_groups": list(aggregate._shared_with_groups),  # Convert set to list for JSON
        }

    def _deserialize_aggregate(self, state: dict) -> Document:
        """
        Deserialize complete aggregate state from snapshot.

        Restores ALL fields from snapshot to match exact state when snapshot was taken,
        ensuring data integrity when loading from snapshots instead of replaying events.
        """
        document = Document.__new__(Document)
        document._id = UUID(state["id"])
        document._version = state["version"]
        document._pending_events = []
        document._filename = state["filename"]
        document._original_format = state["original_format"]
        document._markdown_content = state["markdown_content"]
        document._sections = state["sections"]
        document._metadata = state.get("metadata", {})  # Restore metadata or empty dict if old snapshot
        document._status = DocumentStatus(state["status"])

        # Restore policy repository ID (may be None)
        policy_id_str = state.get("policy_repository_id")
        document._policy_repository_id = UUID(policy_id_str) if policy_id_str else None

        document._compliance_score = state.get("compliance_score")
        document._findings = state.get("findings", [])  # Restore findings or empty list if old snapshot

        version_data = state["current_version"]
        document._current_version = VersionNumber(
            version_data["major"],
            version_data["minor"],
            version_data["patch"]
        )
        
        # Restore access control fields (Phase 13) - default for old snapshots
        document._owner_kerberos_id = state.get("owner_kerberos_id", "system")
        document._visibility = state.get("visibility", "private")
        document._shared_with_groups = set(state.get("shared_with_groups", []))  # Convert list to set
        
        return document
