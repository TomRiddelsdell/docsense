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


class InvalidDocumentState(DocumentException):
    def __init__(self, document_id: UUID, current_status: str, required_status: str, operation: str):
        self.document_id = document_id
        self.current_status = current_status
        self.required_status = required_status
        self.operation = operation
        super().__init__(
            f"Cannot {operation} document {document_id}: "
            f"current status is {current_status}, requires {required_status}"
        )


class DocumentAlreadyAssigned(DocumentException):
    def __init__(self, document_id: UUID, repository_id: UUID):
        self.document_id = document_id
        self.repository_id = repository_id
        super().__init__(
            f"Document {document_id} is already assigned to repository {repository_id}"
        )
