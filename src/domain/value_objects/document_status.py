from enum import Enum


class DocumentStatus(Enum):
    DRAFT = "DRAFT"
    UPLOADED = "UPLOADED"
    CONVERTED = "CONVERTED"
    ANALYZING = "ANALYZING"
    ANALYZED = "ANALYZED"
    EXPORTED = "EXPORTED"
    FAILED = "FAILED"

    def can_analyze(self) -> bool:
        return self in (DocumentStatus.CONVERTED, DocumentStatus.ANALYZED, DocumentStatus.FAILED)
