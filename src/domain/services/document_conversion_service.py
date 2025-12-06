from typing import List


class DocumentConversionService:
    SUPPORTED_FORMATS = [
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "text/markdown",
        "text/x-rst",
        "text/plain",
    ]

    def can_convert(self, content_type: str) -> bool:
        return content_type in self.SUPPORTED_FORMATS

    def get_supported_formats(self) -> List[str]:
        return self.SUPPORTED_FORMATS.copy()
