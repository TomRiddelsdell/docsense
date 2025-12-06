from typing import List
from uuid import UUID


class DocumentException(Exception):
    pass


class DocumentNotFound(DocumentException):
    def __init__(self, document_id: UUID):
        self.document_id = document_id
        super().__init__(f"Document not found: {document_id}")


class InvalidDocumentFormat(DocumentException):
    def __init__(self, provided_format: str, supported_formats: List[str]):
        self.provided_format = provided_format
        self.supported_formats = supported_formats
        super().__init__(
            f"Invalid document format: {provided_format}. "
            f"Supported formats: {', '.join(supported_formats)}"
        )


class DocumentAlreadyExists(DocumentException):
    def __init__(self, document_id: UUID):
        self.document_id = document_id
        super().__init__(f"Document already exists: {document_id}")
