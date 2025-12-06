import pytest
from uuid import uuid4

from src.application.commands.document_handlers import (
    UploadDocumentHandler,
    ExportDocumentHandler,
    DeleteDocumentHandler,
)
from src.domain.commands import UploadDocument, ExportDocument, DeleteDocument
from src.domain.aggregates.document import Document
from src.domain.value_objects import DocumentId, DocumentStatus
from src.domain.exceptions.document_exceptions import DocumentNotFound, InvalidDocumentFormat
from tests.fixtures.mocks import (
    MockDocumentRepository,
    MockEventPublisher,
    MockConverterFactory,
)


class TestUploadDocumentHandler:
    @pytest.fixture
    def mock_repository(self):
        return MockDocumentRepository()

    @pytest.fixture
    def mock_publisher(self):
        return MockEventPublisher()

    @pytest.fixture
    def mock_converter(self):
        return MockConverterFactory(
            success=True,
            markdown="# Test Document\n\nContent here.",
            sections=[{"heading": "Test", "content": "Content", "level": 1}]
        )

    @pytest.fixture
    def handler(self, mock_repository, mock_converter, mock_publisher):
        return UploadDocumentHandler(
            document_repository=mock_repository,
            converter_factory=mock_converter,
            event_publisher=mock_publisher
        )

    @pytest.mark.asyncio
    async def test_upload_document_success(self, handler, mock_repository, mock_publisher):
        command = UploadDocument(
            filename="test.pdf",
            content=b"PDF content here",
            content_type="application/pdf",
            uploaded_by="user@example.com"
        )

        result = await handler.handle(command)

        assert isinstance(result, DocumentId)
        assert len(mock_repository._save_calls) == 1
        saved_doc = mock_repository._save_calls[0]
        assert saved_doc.filename == "test.pdf"
        assert saved_doc.status == DocumentStatus.CONVERTED

    @pytest.mark.asyncio
    async def test_upload_document_publishes_events(self, handler, mock_publisher):
        command = UploadDocument(
            filename="test.pdf",
            content=b"PDF content here",
            content_type="application/pdf",
            uploaded_by="user@example.com"
        )

        await handler.handle(command)

        assert len(mock_publisher.published_events) >= 1

    @pytest.mark.asyncio
    async def test_upload_document_conversion_failure(self, mock_repository, mock_publisher):
        failing_converter = MockConverterFactory(success=False)
        handler = UploadDocumentHandler(
            document_repository=mock_repository,
            converter_factory=failing_converter,
            event_publisher=mock_publisher
        )

        command = UploadDocument(
            filename="test.xyz",
            content=b"Unknown content",
            content_type="application/unknown",
            uploaded_by="user@example.com"
        )

        with pytest.raises(InvalidDocumentFormat):
            await handler.handle(command)

    @pytest.mark.asyncio
    async def test_upload_document_with_policy_repository(self, handler, mock_repository):
        policy_id = uuid4()
        command = UploadDocument(
            filename="test.pdf",
            content=b"PDF content here",
            content_type="application/pdf",
            uploaded_by="user@example.com",
            policy_repository_id=policy_id
        )

        result = await handler.handle(command)

        assert isinstance(result, DocumentId)


class TestExportDocumentHandler:
    @pytest.fixture
    def mock_repository(self):
        return MockDocumentRepository()

    @pytest.fixture
    def mock_publisher(self):
        return MockEventPublisher()

    @pytest.fixture
    def handler(self, mock_repository, mock_publisher):
        return ExportDocumentHandler(
            document_repository=mock_repository,
            event_publisher=mock_publisher
        )

    @pytest.fixture
    def analyzed_document(self):
        doc_id = uuid4()
        doc = Document.upload(
            document_id=doc_id,
            filename="test.pdf",
            content=b"content",
            original_format="pdf",
            uploaded_by="user@example.com"
        )
        doc.convert(
            markdown_content="# Test",
            sections=[],
            metadata={}
        )
        doc.start_analysis(
            policy_repository_id=uuid4(),
            ai_model="gemini",
            initiated_by="user@example.com"
        )
        doc.complete_analysis(
            findings_count=0,
            compliance_score=1.0,
            findings=[],
            processing_time_ms=100
        )
        doc.clear_pending_events()
        return doc

    @pytest.mark.asyncio
    async def test_export_document_success(self, handler, mock_repository, analyzed_document):
        mock_repository.add(analyzed_document)

        command = ExportDocument(
            document_id=analyzed_document.id,
            export_format="markdown",
            exported_by="user@example.com"
        )

        version = await handler.handle(command)

        assert version is not None
        assert len(mock_repository._save_calls) == 1

    @pytest.mark.asyncio
    async def test_export_document_not_found(self, handler):
        command = ExportDocument(
            document_id=uuid4(),
            export_format="markdown",
            exported_by="user@example.com"
        )

        with pytest.raises(DocumentNotFound):
            await handler.handle(command)

    @pytest.mark.asyncio
    async def test_export_document_publishes_events(self, handler, mock_repository, mock_publisher, analyzed_document):
        mock_repository.add(analyzed_document)

        command = ExportDocument(
            document_id=analyzed_document.id,
            export_format="markdown",
            exported_by="user@example.com"
        )

        await handler.handle(command)

        assert len(mock_publisher.published_events) >= 1


class TestDeleteDocumentHandler:
    @pytest.fixture
    def mock_repository(self):
        return MockDocumentRepository()

    @pytest.fixture
    def mock_publisher(self):
        return MockEventPublisher()

    @pytest.fixture
    def handler(self, mock_repository, mock_publisher):
        return DeleteDocumentHandler(
            document_repository=mock_repository,
            event_publisher=mock_publisher
        )

    @pytest.fixture
    def existing_document(self):
        doc_id = uuid4()
        doc = Document.upload(
            document_id=doc_id,
            filename="test.pdf",
            content=b"content",
            original_format="pdf",
            uploaded_by="user@example.com"
        )
        doc.clear_pending_events()
        return doc

    @pytest.mark.asyncio
    async def test_delete_document_success(self, handler, mock_repository, existing_document):
        mock_repository.add(existing_document)

        command = DeleteDocument(
            document_id=existing_document.id,
            deleted_by="user@example.com",
            reason="No longer needed"
        )

        result = await handler.handle(command)

        assert result is True

    @pytest.mark.asyncio
    async def test_delete_document_not_found(self, handler):
        command = DeleteDocument(
            document_id=uuid4(),
            deleted_by="user@example.com",
            reason="Cleanup"
        )

        with pytest.raises(DocumentNotFound):
            await handler.handle(command)
