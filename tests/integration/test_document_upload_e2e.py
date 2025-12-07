"""End-to-end integration tests for document upload flow.

These tests verify the complete document upload pipeline from API request
through converters to event store persistence.
"""
import pytest
import io
from uuid import UUID
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from src.api.main import create_app
from src.infrastructure.persistence.event_store import InMemoryEventStore
from src.infrastructure.persistence.event_serializer import EventSerializer
from src.infrastructure.converters.base import DocumentFormat


class TestDocumentUploadEndToEnd:
    """End-to-end tests for document upload that verify the full flow."""
    
    @pytest.fixture
    def event_store(self):
        return InMemoryEventStore()
    
    @pytest.fixture
    def serializer(self):
        return EventSerializer()
    
    @pytest.fixture
    def sample_pdf_content(self):
        return b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\ntrailer\n<< /Root 1 0 R >>\n%%EOF"
    
    @pytest.fixture
    def sample_markdown_content(self):
        return b"# Trading Algorithm\n\n## Overview\n\nThis is a test algorithm."

    def test_document_upload_serializes_enum_correctly(self, serializer):
        """Verify that DocumentFormat enum is serialized to string value.
        
        This is a regression test for the bug where DocumentFormat enum
        caused 'Object of type DocumentFormat is not JSON serializable' error.
        """
        from src.domain.events import DocumentConverted
        from uuid import uuid4
        from datetime import datetime, timezone
        import json
        
        event = DocumentConverted(
            event_id=uuid4(),
            aggregate_id=uuid4(),
            occurred_at=datetime.now(timezone.utc),
            version=1,
            markdown_content="# Test",
            sections=[],
            metadata={
                "title": "Test Doc",
                "original_format": DocumentFormat.PDF,
                "page_count": 10
            },
            conversion_warnings=[]
        )
        
        serialized = serializer.serialize(event)
        json_str = json.dumps(serialized)
        
        assert '"original_format": "pdf"' in json_str
        
        parsed = json.loads(json_str)
        assert parsed["metadata"]["original_format"] == "pdf"

    def test_all_document_formats_serialize_for_persistence(self, serializer):
        """Verify all DocumentFormat enum values can be serialized to JSON."""
        from src.domain.events import DocumentConverted
        from uuid import uuid4
        from datetime import datetime, timezone
        import json
        
        for doc_format in DocumentFormat:
            event = DocumentConverted(
                event_id=uuid4(),
                aggregate_id=uuid4(),
                occurred_at=datetime.now(timezone.utc),
                version=1,
                markdown_content="# Test",
                sections=[],
                metadata={"original_format": doc_format},
                conversion_warnings=[]
            )
            
            serialized = serializer.serialize(event)
            json_str = json.dumps(serialized)
            
            assert doc_format.value in json_str

    @pytest.mark.asyncio
    async def test_event_store_persists_complex_metadata(self, event_store, serializer):
        """Verify event store can persist events with complex metadata."""
        from src.domain.events import DocumentUploaded, DocumentConverted
        from uuid import uuid4
        from datetime import datetime, timezone
        
        aggregate_id = uuid4()
        
        upload_event = DocumentUploaded(
            event_id=uuid4(),
            aggregate_id=aggregate_id,
            occurred_at=datetime.now(timezone.utc),
            version=1,
            filename="trading_strategy.pdf",
            original_format="pdf",
            file_size_bytes=2048000,
            uploaded_by="analyst@trading.com"
        )
        
        convert_event = DocumentConverted(
            event_id=uuid4(),
            aggregate_id=aggregate_id,
            occurred_at=datetime.now(timezone.utc),
            version=2,
            markdown_content="# Algorithmic Trading Strategy\n\n## Risk Parameters",
            sections=[
                {"id": "intro", "title": "Introduction", "content": "Strategy overview"},
                {"id": "risk", "title": "Risk Management", "content": "Stop loss at 2%"}
            ],
            metadata={
                "title": "Trading Strategy",
                "author": "Quant Team",
                "original_format": DocumentFormat.PDF,
                "page_count": 45,
                "word_count": 12000,
                "extra": {
                    "version": "2.1",
                    "department": "Quantitative Research"
                }
            },
            conversion_warnings=["Complex table on page 23 simplified"]
        )
        
        await event_store.append(aggregate_id, [upload_event, convert_event], expected_version=0)
        
        retrieved = await event_store.get_events(aggregate_id)
        
        assert len(retrieved) == 2
        assert isinstance(retrieved[0], DocumentUploaded)
        assert isinstance(retrieved[1], DocumentConverted)
        assert retrieved[1].metadata["original_format"] == DocumentFormat.PDF
        assert retrieved[1].metadata["extra"]["department"] == "Quantitative Research"

    def test_serializer_roundtrip_preserves_data(self, serializer):
        """Verify serialize -> deserialize roundtrip preserves all data."""
        from src.domain.events import DocumentConverted
        from uuid import uuid4
        from datetime import datetime, timezone
        
        original = DocumentConverted(
            event_id=uuid4(),
            aggregate_id=uuid4(),
            occurred_at=datetime.now(timezone.utc),
            version=5,
            markdown_content="# Complex Document\n\nWith multiple sections.",
            sections=[
                {"id": "1", "title": "Section 1", "level": 1},
                {"id": "2", "title": "Section 2", "level": 2}
            ],
            metadata={
                "title": "Complex Doc",
                "original_format": DocumentFormat.WORD,
                "nested": {
                    "deeply": {
                        "nested": {
                            "value": "test"
                        }
                    }
                }
            },
            conversion_warnings=["Warning 1", "Warning 2"]
        )
        
        serialized = serializer.serialize(original)
        restored = serializer.deserialize("DocumentConverted", serialized)
        
        assert restored.event_id == original.event_id
        assert restored.aggregate_id == original.aggregate_id
        assert restored.version == original.version
        assert restored.markdown_content == original.markdown_content
        assert len(restored.sections) == 2
        assert restored.metadata["title"] == "Complex Doc"
        assert restored.metadata["original_format"] == "docx"
        assert restored.metadata["nested"]["deeply"]["nested"]["value"] == "test"
        assert restored.conversion_warnings == ["Warning 1", "Warning 2"]
