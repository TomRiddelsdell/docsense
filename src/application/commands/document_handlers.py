from typing import Optional
from uuid import UUID, uuid4

from .base import CommandHandler, CommandResult
from src.domain.commands import UploadDocument, ExportDocument, DeleteDocument
from src.domain.aggregates.document import Document
from src.domain.value_objects import DocumentId
from src.domain.exceptions.document_exceptions import DocumentNotFound, InvalidDocumentFormat
from src.infrastructure.repositories.document_repository import DocumentRepository
from src.infrastructure.converters.converter_factory import ConverterFactory
from src.application.services.event_publisher import EventPublisher


class UploadDocumentHandler(CommandHandler[UploadDocument, DocumentId]):
    def __init__(
        self,
        document_repository: DocumentRepository,
        converter_factory: ConverterFactory,
        event_publisher: EventPublisher
    ):
        self._documents = document_repository
        self._converters = converter_factory
        self._publisher = event_publisher

    async def handle(self, command: UploadDocument) -> DocumentId:
        document_id = DocumentId.generate()

        document = Document.upload(
            document_id=document_id.value,
            filename=command.filename,
            content=command.content,
            original_format=command.content_type,
            uploaded_by=command.uploaded_by
        )

        result = self._converters.convert_from_bytes(
            command.content,
            command.filename
        )

        if result.success:
            document.convert(
                markdown_content=result.markdown_content,
                sections=[s.__dict__ if hasattr(s, '__dict__') else s for s in result.sections],
                metadata=result.metadata.__dict__ if hasattr(result.metadata, '__dict__') else result.metadata,
                conversion_warnings=getattr(result, 'warnings', [])
            )
        else:
            raise InvalidDocumentFormat(
                provided_format=command.content_type,
                supported_formats=["pdf", "docx", "doc", "md", "markdown", "rst"]
            )

        await self._documents.save(document)

        events = document.pending_events
        if events:
            await self._publisher.publish_all(events)

        return document_id


class ExportDocumentHandler(CommandHandler[ExportDocument, str]):
    def __init__(
        self,
        document_repository: DocumentRepository,
        event_publisher: EventPublisher
    ):
        self._documents = document_repository
        self._publisher = event_publisher

    async def handle(self, command: ExportDocument) -> str:
        document = await self._documents.get(command.document_id)
        if document is None:
            raise DocumentNotFound(document_id=command.document_id)

        document.export(
            export_format=command.export_format,
            exported_by=command.exported_by
        )

        await self._documents.save(document)

        events = document.pending_events
        if events:
            await self._publisher.publish_all(events)

        return str(document.current_version)


class DeleteDocumentHandler(CommandHandler[DeleteDocument, bool]):
    def __init__(
        self,
        document_repository: DocumentRepository,
        event_publisher: EventPublisher
    ):
        self._documents = document_repository
        self._publisher = event_publisher

    async def handle(self, command: DeleteDocument) -> bool:
        document = await self._documents.get(command.document_id)
        if document is None:
            raise DocumentNotFound(document_id=command.document_id)

        return True
