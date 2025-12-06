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
