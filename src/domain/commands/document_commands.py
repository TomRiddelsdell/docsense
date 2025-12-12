from dataclasses import dataclass, field
from typing import Optional
from uuid import UUID

from .base import Command


@dataclass(frozen=True)
class UploadDocument(Command):
    filename: str = ""
    content: bytes = field(default=b"")
    content_type: str = ""
    uploaded_by: str = ""
    policy_repository_id: Optional[UUID] = None


@dataclass(frozen=True)
class ExportDocument(Command):
    document_id: UUID = field(default=None)
    export_format: str = ""
    exported_by: str = ""
    version: Optional[str] = None


@dataclass(frozen=True)
class DeleteDocument(Command):
    document_id: UUID = field(default=None)
    deleted_by: str = ""
    reason: str = ""


@dataclass(frozen=True)
class CurateSemanticIR(Command):
    """Command to trigger AI curation of semantic IR."""
    document_id: UUID = field(default=None)
    provider_type: str = "claude"
