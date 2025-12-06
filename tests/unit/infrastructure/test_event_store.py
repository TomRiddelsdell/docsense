import pytest
from uuid import uuid4
from datetime import datetime, timezone

from src.infrastructure.persistence.event_store import (
    InMemoryEventStore,
    ConcurrencyError,
)
from src.domain.events import DocumentUploaded, DocumentConverted


class TestInMemoryEventStore:
    @pytest.fixture
    def store(self):
        return InMemoryEventStore()

    @pytest.fixture
    def sample_events(self):
        aggregate_id = uuid4()
        return aggregate_id, [
            DocumentUploaded(
                event_id=uuid4(),
                aggregate_id=aggregate_id,
                occurred_at=datetime.now(timezone.utc),
                version=1,
                filename="test.pdf",
                original_format="pdf",
                file_size_bytes=1024,
                uploaded_by="user@example.com"
            ),
            DocumentConverted(
                event_id=uuid4(),
                aggregate_id=aggregate_id,
                occurred_at=datetime.now(timezone.utc),
                version=2,
                markdown_content="# Test",
                sections=[],
                metadata={},
                conversion_warnings=[]
            )
        ]

    @pytest.mark.asyncio
    async def test_append_single_event(self, store):
        aggregate_id = uuid4()
        event = DocumentUploaded(
            event_id=uuid4(),
            aggregate_id=aggregate_id,
            occurred_at=datetime.now(timezone.utc),
            version=1,
            filename="test.pdf",
            original_format="pdf",
            file_size_bytes=1024,
            uploaded_by="user@example.com"
        )
        
        await store.append(aggregate_id, [event], expected_version=0)
        
        events = await store.get_events(aggregate_id)
        assert len(events) == 1
        assert events[0].filename == "test.pdf"

    @pytest.mark.asyncio
    async def test_append_multiple_events(self, store, sample_events):
        aggregate_id, events = sample_events
        
        await store.append(aggregate_id, events, expected_version=0)
        
        stored_events = await store.get_events(aggregate_id)
        assert len(stored_events) == 2

    @pytest.mark.asyncio
    async def test_append_raises_concurrency_error_on_version_mismatch(self, store):
        aggregate_id = uuid4()
        event = DocumentUploaded(
            event_id=uuid4(),
            aggregate_id=aggregate_id,
            occurred_at=datetime.now(timezone.utc),
            version=1,
            filename="test.pdf",
            original_format="pdf",
            file_size_bytes=1024,
            uploaded_by="user@example.com"
        )
        
        await store.append(aggregate_id, [event], expected_version=0)
        
        with pytest.raises(ConcurrencyError) as exc_info:
            await store.append(aggregate_id, [event], expected_version=0)
        
        assert exc_info.value.expected_version == 0
        assert exc_info.value.actual_version == 1

    @pytest.mark.asyncio
    async def test_append_empty_list_does_nothing(self, store):
        aggregate_id = uuid4()
        
        await store.append(aggregate_id, [], expected_version=0)
        
        events = await store.get_events(aggregate_id)
        assert len(events) == 0

    @pytest.mark.asyncio
    async def test_get_events_from_version(self, store, sample_events):
        aggregate_id, events = sample_events
        await store.append(aggregate_id, events, expected_version=0)
        
        later_events = await store.get_events(aggregate_id, from_version=1)
        
        assert len(later_events) == 1
        assert isinstance(later_events[0], DocumentConverted)

    @pytest.mark.asyncio
    async def test_get_events_returns_empty_for_unknown_aggregate(self, store):
        events = await store.get_events(uuid4())
        assert events == []

    @pytest.mark.asyncio
    async def test_get_all_events(self, store, sample_events):
        aggregate_id1, events1 = sample_events
        await store.append(aggregate_id1, events1, expected_version=0)
        
        aggregate_id2 = uuid4()
        event2 = DocumentUploaded(
            event_id=uuid4(),
            aggregate_id=aggregate_id2,
            occurred_at=datetime.now(timezone.utc),
            version=1,
            filename="other.pdf",
            original_format="pdf",
            file_size_bytes=2048,
            uploaded_by="other@example.com"
        )
        await store.append(aggregate_id2, [event2], expected_version=0)
        
        all_events = await store.get_all_events()
        assert len(all_events) == 3

    @pytest.mark.asyncio
    async def test_get_all_events_with_pagination(self, store, sample_events):
        aggregate_id, events = sample_events
        await store.append(aggregate_id, events, expected_version=0)
        
        first_batch = await store.get_all_events(from_position=0, batch_size=1)
        assert len(first_batch) == 1
        
        second_batch = await store.get_all_events(from_position=1, batch_size=1)
        assert len(second_batch) == 1

    @pytest.mark.asyncio
    async def test_clear(self, store, sample_events):
        aggregate_id, events = sample_events
        await store.append(aggregate_id, events, expected_version=0)
        
        store.clear()
        
        stored_events = await store.get_events(aggregate_id)
        assert len(stored_events) == 0
        
        all_events = await store.get_all_events()
        assert len(all_events) == 0

    @pytest.mark.asyncio
    async def test_sequential_appends(self, store):
        aggregate_id = uuid4()
        
        event1 = DocumentUploaded(
            event_id=uuid4(),
            aggregate_id=aggregate_id,
            occurred_at=datetime.now(timezone.utc),
            version=1,
            filename="test.pdf",
            original_format="pdf",
            file_size_bytes=1024,
            uploaded_by="user@example.com"
        )
        await store.append(aggregate_id, [event1], expected_version=0)
        
        event2 = DocumentConverted(
            event_id=uuid4(),
            aggregate_id=aggregate_id,
            occurred_at=datetime.now(timezone.utc),
            version=2,
            markdown_content="# Content",
            sections=[],
            metadata={},
            conversion_warnings=[]
        )
        await store.append(aggregate_id, [event2], expected_version=1)
        
        events = await store.get_events(aggregate_id)
        assert len(events) == 2


class TestConcurrencyError:
    def test_error_message_contains_details(self):
        aggregate_id = uuid4()
        error = ConcurrencyError(aggregate_id, expected_version=5, actual_version=7)
        
        assert str(aggregate_id) in str(error)
        assert "5" in str(error)
        assert "7" in str(error)

    def test_error_attributes(self):
        aggregate_id = uuid4()
        error = ConcurrencyError(aggregate_id, expected_version=5, actual_version=7)
        
        assert error.aggregate_id == aggregate_id
        assert error.expected_version == 5
        assert error.actual_version == 7
