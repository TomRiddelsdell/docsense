import logging
from typing import Optional
from uuid import UUID, uuid4

from .base import CommandHandler, CommandResult
from src.domain.commands import UploadDocument, ExportDocument, DeleteDocument, CurateSemanticIR

logger = logging.getLogger(__name__)
from src.domain.aggregates.document import Document
from src.domain.value_objects import DocumentId
from src.domain.exceptions.document_exceptions import DocumentNotFound, InvalidDocumentFormat
from src.infrastructure.repositories.document_repository import DocumentRepository
from src.infrastructure.converters.converter_factory import ConverterFactory
from src.application.services.event_publisher import EventPublisher
from src.infrastructure.semantic import IRBuilder

# Import metrics (will be None if not in API context)
try:
    from src.api.metrics import (
        documents_uploaded_total,
        documents_converted_total
    )
    METRICS_AVAILABLE = True
except ImportError:
    METRICS_AVAILABLE = False
    logger.debug("Metrics not available - running outside API context")


class UploadDocumentHandler(CommandHandler[UploadDocument, DocumentId]):
    def __init__(
        self,
        document_repository: DocumentRepository,
        converter_factory: ConverterFactory,
        event_publisher: EventPublisher,
        ir_builder: Optional[IRBuilder] = None
    ):
        self._documents = document_repository
        self._converters = converter_factory
        self._publisher = event_publisher
        self._ir_builder = ir_builder or IRBuilder()

    async def handle(self, command: UploadDocument) -> DocumentId:
        try:
            document_id = DocumentId.generate()
            logger.info(f"Starting document upload: {command.filename}")

            document = Document.upload(
                document_id=document_id.value,
                filename=command.filename,
                content=command.content,
                original_format=command.content_type,
                uploaded_by=command.uploaded_by
            )
            logger.info(f"Document aggregate created: {document_id}")

            result = self._converters.convert_from_bytes(
                command.content,
                command.filename
            )
            logger.info(f"Conversion result: success={result.success}, errors={result.errors}")

            if result.success:
                # Track successful conversion
                if METRICS_AVAILABLE:
                    documents_converted_total.labels(status="success").inc()

                # Generate semantic IR from conversion result
                try:
                    logger.info("Generating semantic IR...")
                    semantic_ir = self._ir_builder.build(result, str(document_id.value))
                    result.semantic_ir = semantic_ir
                    logger.info(f"Semantic IR generated: {semantic_ir.get_statistics()}")
                except Exception as e:
                    logger.warning(f"Failed to generate semantic IR: {e}", exc_info=True)
                    # Continue without semantic IR

                document.convert(
                    markdown_content=result.markdown_content,
                    sections=[s.__dict__ if hasattr(s, '__dict__') else s for s in result.sections],
                    metadata=result.metadata.__dict__ if hasattr(result.metadata, '__dict__') else result.metadata,
                    conversion_warnings=getattr(result, 'warnings', [])
                )
                logger.info("Document conversion applied")
            else:
                # Track failed conversion
                if METRICS_AVAILABLE:
                    documents_converted_total.labels(status="failed").inc()

                logger.error(f"Conversion failed: {result.errors}")
                raise InvalidDocumentFormat(
                    provided_format=command.content_type,
                    supported_formats=["pdf", "docx", "doc", "md", "markdown", "rst"]
                )

            events = document.pending_events
            logger.info(f"Captured {len(events)} pending events before save")

            logger.info("Saving document to repository...")
            await self._documents.save(document)
            logger.info("Document saved successfully")

            if events:
                logger.info(f"Publishing {len(events)} events")
                await self._publisher.publish_all(events)
                logger.info("Events published successfully")

            # Track successful upload
            if METRICS_AVAILABLE:
                documents_uploaded_total.labels(status="success").inc()

            return document_id
        except Exception as e:
            # Track failed upload
            if METRICS_AVAILABLE:
                documents_uploaded_total.labels(status="failed").inc()

            logger.exception(f"Error uploading document: {e}")
            raise


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

        events = list(document.pending_events)
        await self._documents.save(document)

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


class CurateSemanticIRHandler(CommandHandler[CurateSemanticIR, bool]):
    """Handler for AI curation of semantic IR."""

    def __init__(
        self,
        document_repository: DocumentRepository,
        event_publisher: EventPublisher,
    ):
        self._documents = document_repository
        self._publisher = event_publisher

    async def handle(self, command: CurateSemanticIR) -> bool:
        """
        Handle semantic IR curation command.

        Note: This handler only emits the start event. The actual curation
        happens in an event listener that reacts to DocumentConverted events.
        """
        logger.info(f"Handling CurateSemanticIR command for document {command.document_id}")

        # Load document
        document = await self._documents.get(command.document_id)
        if document is None:
            raise DocumentNotFound(document_id=command.document_id)

        # Start curation (emit event)
        document.start_ir_curation(provider_type=command.provider_type)

        # Save and publish events
        events = list(document.pending_events)
        await self._documents.save(document)

        if events:
            logger.info(f"Publishing {len(events)} curation events")
            await self._publisher.publish_all(events)

        return True
