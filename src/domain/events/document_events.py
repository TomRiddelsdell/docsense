from dataclasses import dataclass, field
from typing import List, Dict, Any
from uuid import UUID

from .base import DomainEvent


@dataclass(frozen=True)
class DocumentUploaded(DomainEvent):
    filename: str = ""
    original_format: str = ""
    file_size_bytes: int = 0
    uploaded_by: str = ""
    owner_kerberos_id: str = ""  # NEW: Document owner
    aggregate_type: str = field(default="Document")


@dataclass(frozen=True)
class DocumentConverted(DomainEvent):
    markdown_content: str = ""
    sections: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    conversion_warnings: List[str] = field(default_factory=list)
    aggregate_type: str = field(default="Document")


@dataclass(frozen=True)
class DocumentExported(DomainEvent):
    export_format: str = ""
    exported_by: str = ""
    version_number: str = ""
    aggregate_type: str = field(default="Document")


@dataclass(frozen=True)
class SemanticIRCurationStarted(DomainEvent):
    """Emitted when AI curation of semantic IR begins."""
    provider_type: str = "claude"
    aggregate_type: str = field(default="Document")


@dataclass(frozen=True)
class SemanticIRCurated(DomainEvent):
    """Emitted when AI curation of semantic IR completes successfully."""
    definitions_added: int = 0
    definitions_removed: int = 0
    validation_issues_found: int = 0
    curation_metadata: Dict[str, Any] = field(default_factory=dict)
    aggregate_type: str = field(default="Document")


@dataclass(frozen=True)
class SemanticIRCurationFailed(DomainEvent):
    """Emitted when AI curation fails."""
    error_message: str = ""
    aggregate_type: str = field(default="Document")


@dataclass(frozen=True)
class DocumentSharedWithGroup(DomainEvent):
    """Emitted when a document is shared with a group.
    
    Sharing with a group automatically changes visibility to GROUP.
    """
    group: str = ""
    shared_by: str = ""
    aggregate_type: str = field(default="Document")


@dataclass(frozen=True)
class DocumentMadePrivate(DomainEvent):
    """Emitted when a document visibility is changed to private.
    
    This removes all group sharing.
    """
    changed_by: str = ""
    aggregate_type: str = field(default="Document")
