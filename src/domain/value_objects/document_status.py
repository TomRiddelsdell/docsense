from enum import Enum


class DocumentStatus(Enum):
    DRAFT = "DRAFT"
    UPLOADED = "UPLOADED"
    CONVERTED = "CONVERTED"
    ANALYZING = "ANALYZING"
    ANALYZED = "ANALYZED"
    EXPORTED = "EXPORTED"

    def can_analyze(self) -> bool:
        return self in (DocumentStatus.CONVERTED, DocumentStatus.ANALYZED)
