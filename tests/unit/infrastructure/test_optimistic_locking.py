"""
Tests for optimistic locking and concurrency control.

Tests that concurrent modifications to the same aggregate are handled correctly
using optimistic locking with SELECT FOR UPDATE and automatic retry logic.
"""
import pytest
import asyncio
from uuid import uuid4
from unittest.mock import patch, MagicMock, AsyncMock

from src.infrastructure.persistence.event_store import (
    InMemoryEventStore,
    PostgresEventStore,
    ConcurrencyError
)
from src.infrastructure.persistence.snapshot_store import InMemorySnapshotStore
from src.infrastructure.repositories.document_repository import DocumentRepository
from src.domain.aggregates.document import Document


class TestOptimisticLockingInMemory:
    """Test optimistic locking with in-memory event store."""

    @pytest.mark.asyncio
    async def test_concurrent_append_raises_concurrency_error(self):
        """Test that concurrent appends to same aggregate raise ConcurrencyError."""
        event_store = InMemoryEventStore()
        repo = DocumentRepository(event_store, InMemorySnapshotStore())

        # Create and save initial document
        doc_id = uuid4()
        document = Document.upload(
            document_id=doc_id,
            filename="test.pdf",
            content=b"test",
            original_format="pdf",
            uploaded_by="user"
        )
        await repo.save(document)

        # Load document twice (simulating two concurrent requests)
        doc1 = await repo.get(doc_id)
        doc2 = await repo.get(doc_id)

        # Both documents are at version 1
        assert doc1.version == 1
        assert doc2.version == 1

        # First modification succeeds
        doc1.convert("# Test 1", [], {})
        await repo.save(doc1)

        # Second modification should fail with ConcurrencyError
        doc2.convert("# Test 2", [], {})
        with pytest.raises(ConcurrencyError) as exc_info:
            await repo.save(doc2)

        assert exc_info.value.aggregate_id == doc_id
        assert exc_info.value.expected_version == 1
        assert exc_info.value.actual_version == 2

    @pytest.mark.asyncio
    async def test_retry_logic_on_concurrency_conflict(self):
        """Test that repository retries on concurrency conflicts."""
        event_store = InMemoryEventStore()
        repo = DocumentRepository(
            event_store,
            InMemorySnapshotStore(),
            max_retries=3,
            retry_delay_ms=10
        )

        doc_id = uuid4()
        document = Document.upload(
            document_id=doc_id,
            filename="test.pdf",
            content=b"test",
            original_format="pdf",
            uploaded_by="user"
        )
        await repo.save(document)

        # Mock the event store to fail twice, then succeed
        original_append = event_store.append
        call_count = 0

        async def mock_append(aggregate_id, events, expected_version):
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                # First two attempts fail
                raise ConcurrencyError(aggregate_id, expected_version, expected_version + 1)
            # Third attempt succeeds
            return await original_append(aggregate_id, events, expected_version)

        event_store.append = mock_append

        # Load and modify document
        doc = await repo.get(doc_id)
        doc.convert("# Test", [], {})

        # Should succeed after retries
        await repo.save(doc)

        # Verify it was called 3 times
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_retry_exhaustion_raises_error(self):
        """Test that error is raised when all retries are exhausted."""
        event_store = InMemoryEventStore()
        repo = DocumentRepository(
            event_store,
            InMemorySnapshotStore(),
            max_retries=3,
            retry_delay_ms=10
        )

        doc_id = uuid4()
        document = Document.upload(
            document_id=doc_id,
            filename="test.pdf",
            content=b"test",
            original_format="pdf",
            uploaded_by="user"
        )
        await repo.save(document)

        # Mock the event store to always fail
        async def mock_append(aggregate_id, events, expected_version):
            raise ConcurrencyError(aggregate_id, expected_version, expected_version + 1)

        event_store.append = mock_append

        # Load and modify document
        doc = await repo.get(doc_id)
        doc.convert("# Test", [], {})

        # Should fail after max retries
        with pytest.raises(ConcurrencyError):
            await repo.save(doc)

    @pytest.mark.asyncio
    async def test_exponential_backoff(self):
        """Test that retry delays increase exponentially."""
        event_store = InMemoryEventStore()
        repo = DocumentRepository(
            event_store,
            InMemorySnapshotStore(),
            max_retries=4,
            retry_delay_ms=50  # Base delay
        )

        doc_id = uuid4()
        document = Document.upload(
            document_id=doc_id,
            filename="test.pdf",
            content=b"test",
            original_format="pdf",
            uploaded_by="user"
        )
        await repo.save(document)

        # Track sleep calls
        sleep_delays = []
        original_sleep = asyncio.sleep

        async def mock_sleep(delay):
            sleep_delays.append(delay)
            # Don't actually sleep in tests
            await original_sleep(0)

        # Mock the event store to fail 3 times
        call_count = 0

        async def mock_append(aggregate_id, events, expected_version):
            nonlocal call_count
            call_count += 1
            if call_count <= 3:
                raise ConcurrencyError(aggregate_id, expected_version, expected_version + 1)
            return None

        event_store.append = mock_append

        # Load and modify document
        doc = await repo.get(doc_id)
        doc.convert("# Test", [], {})

        # Patch asyncio.sleep
        with patch('asyncio.sleep', side_effect=mock_sleep):
            await repo.save(doc)

        # Verify exponential backoff: 50ms * 2^0 = 0.05s, 50ms * 2^1 = 0.1s, 50ms * 2^2 = 0.2s
        assert len(sleep_delays) == 3
        assert sleep_delays[0] == 0.05  # 50ms * 2^0 / 1000
        assert sleep_delays[1] == 0.1   # 50ms * 2^1 / 1000
        assert sleep_delays[2] == 0.2   # 50ms * 2^2 / 1000

    @pytest.mark.asyncio
    async def test_no_retry_when_no_events(self):
        """Test that save with no pending events doesn't attempt retries."""
        event_store = InMemoryEventStore()
        repo = DocumentRepository(event_store, InMemorySnapshotStore())

        doc_id = uuid4()
        document = Document.upload(
            document_id=doc_id,
            filename="test.pdf",
            content=b"test",
            original_format="pdf",
            uploaded_by="user"
        )
        await repo.save(document)

        # Load document without modifications
        doc = await repo.get(doc_id)

        # Mock append to track calls
        original_append = event_store.append
        append_called = False

        async def mock_append(*args, **kwargs):
            nonlocal append_called
            append_called = True
            return await original_append(*args, **kwargs)

        event_store.append = mock_append

        # Save without modifications
        await repo.save(doc)

        # append should not have been called
        assert not append_called


class TestOptimisticLockingConcurrency:
    """Test concurrent access scenarios."""

    @pytest.mark.asyncio
    async def test_sequential_modifications_succeed(self):
        """Test that sequential (non-concurrent) modifications work correctly."""
        event_store = InMemoryEventStore()
        repo = DocumentRepository(event_store, InMemorySnapshotStore())

        doc_id = uuid4()
        document = Document.upload(
            document_id=doc_id,
            filename="test.pdf",
            content=b"test",
            original_format="pdf",
            uploaded_by="user"
        )
        await repo.save(document)

        # First modification
        doc1 = await repo.get(doc_id)
        doc1.convert("# Test 1", [], {})
        await repo.save(doc1)

        # Second modification (loading latest version)
        doc2 = await repo.get(doc_id)
        doc2.start_analysis(uuid4(), "gemini", "user")
        await repo.save(doc2)

        # Third modification (loading latest version)
        doc3 = await repo.get(doc_id)
        doc3.complete_analysis(0, 100.0, [], 100)
        await repo.save(doc3)

        # Final document should have all changes
        final = await repo.get(doc_id)
        assert final.version == 4  # Upload + Convert + StartAnalysis + CompleteAnalysis
        assert final.markdown_content == "# Test 1"
        assert final.compliance_score == 100.0

    @pytest.mark.asyncio
    async def test_concurrent_modifications_one_fails(self):
        """Test that when two requests modify concurrently, one fails."""
        event_store = InMemoryEventStore()
        repo = DocumentRepository(event_store, InMemorySnapshotStore(), max_retries=1)

        doc_id = uuid4()
        document = Document.upload(
            document_id=doc_id,
            filename="test.pdf",
            content=b"test",
            original_format="pdf",
            uploaded_by="user"
        )
        await repo.save(document)

        # Simulate two concurrent requests loading the same version
        doc1 = await repo.get(doc_id)
        doc2 = await repo.get(doc_id)

        # Both modify
        doc1.convert("# Version 1", [], {})
        doc2.convert("# Version 2", [], {})

        # First save succeeds
        await repo.save(doc1)

        # Second save fails
        with pytest.raises(ConcurrencyError):
            await repo.save(doc2)

        # Verify only first modification persisted
        final = await repo.get(doc_id)
        assert final.markdown_content == "# Version 1"

    @pytest.mark.asyncio
    async def test_high_concurrency_simulation(self):
        """Test handling of many concurrent modification attempts."""
        event_store = InMemoryEventStore()
        repo = DocumentRepository(
            event_store,
            InMemorySnapshotStore(),
            max_retries=1  # Low retry to make conflicts more visible
        )

        doc_id = uuid4()
        document = Document.upload(
            document_id=doc_id,
            filename="test.pdf",
            content=b"test",
            original_format="pdf",
            uploaded_by="user"
        )
        document.convert("# Test", [], {})
        document.start_analysis(uuid4(), "gemini", "user")
        document.complete_analysis(0, 100.0, [], 100)
        await repo.save(document)

        # Simulate 10 concurrent export requests on same document version
        # Load all at the same time to create conflict
        docs = []
        for i in range(10):
            doc = await repo.get(doc_id)
            docs.append(doc)

        # All docs are at same version
        assert all(doc.version == 4 for doc in docs)

        successes = 0
        failures = 0

        async def export_document(doc, user_num):
            nonlocal successes, failures
            try:
                doc.export("pdf", f"user-{user_num}")
                await repo.save(doc)
                successes += 1
            except ConcurrencyError:
                failures += 1

        # Try to save all concurrently
        tasks = [export_document(docs[i], i) for i in range(10)]
        await asyncio.gather(*tasks, return_exceptions=True)

        # Exactly one should succeed (first one wins)
        assert successes == 1

        # All others should fail due to concurrency
        assert failures == 9

        # Total should be 10
        assert successes + failures == 10


class TestPostgresEventStoreForUpdate:
    """Test PostgreSQL-specific FOR UPDATE locking."""

    @pytest.mark.asyncio
    async def test_for_update_in_query(self):
        """Test that FOR UPDATE is used in the version check query."""
        from unittest.mock import MagicMock

        # Create mock connection
        mock_conn = AsyncMock()
        mock_conn.fetchval = AsyncMock(return_value=0)  # Return version 0
        mock_conn.execute = AsyncMock()

        # Mock transaction context manager
        mock_transaction = MagicMock()
        mock_transaction.__aenter__ = AsyncMock(return_value=None)
        mock_transaction.__aexit__ = AsyncMock(return_value=None)
        mock_conn.transaction = MagicMock(return_value=mock_transaction)

        # Mock pool.acquire() context manager
        mock_acquire = MagicMock()
        mock_acquire.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_acquire.__aexit__ = AsyncMock(return_value=None)

        # Create mock pool
        mock_pool = MagicMock()
        mock_pool.acquire = MagicMock(return_value=mock_acquire)

        # Create event store
        event_store = PostgresEventStore(mock_pool)

        # Create document and events
        doc_id = uuid4()
        document = Document.upload(
            document_id=doc_id,
            filename="test.pdf",
            content=b"test",
            original_format="pdf",
            uploaded_by="user"
        )

        # Append events
        await event_store.append(doc_id, document._pending_events, 0)

        # Verify fetchval was called with FOR UPDATE query
        calls = mock_conn.fetchval.call_args_list
        assert len(calls) >= 1

        # Check that the query contains FOR UPDATE
        query = calls[0][0][0]
        assert "FOR UPDATE" in query
        assert "aggregate_id" in query

    @pytest.mark.asyncio
    async def test_concurrency_error_includes_version_info(self):
        """Test that ConcurrencyError includes expected and actual versions."""
        event_store = InMemoryEventStore()
        doc_id = uuid4()

        # Save initial event
        document = Document.upload(
            document_id=doc_id,
            filename="test.pdf",
            content=b"test",
            original_format="pdf",
            uploaded_by="user"
        )
        await event_store.append(doc_id, document._pending_events, 0)

        # Try to append with wrong version
        document2 = Document.upload(
            document_id=doc_id,
            filename="test2.pdf",
            content=b"test2",
            original_format="pdf",
            uploaded_by="user2"
        )

        with pytest.raises(ConcurrencyError) as exc_info:
            await event_store.append(doc_id, document2._pending_events, 0)

        error = exc_info.value
        assert error.aggregate_id == doc_id
        assert error.expected_version == 0
        assert error.actual_version == 1
        assert "expected version 0" in str(error)
        assert "got 1" in str(error)


class TestVersionProgression:
    """Test that event versions progress correctly."""

    @pytest.mark.asyncio
    async def test_version_increments_correctly(self):
        """Test that event versions increment sequentially."""
        event_store = InMemoryEventStore()
        repo = DocumentRepository(event_store, InMemorySnapshotStore())

        doc_id = uuid4()
        document = Document.upload(
            document_id=doc_id,
            filename="test.pdf",
            content=b"test",
            original_format="pdf",
            uploaded_by="user"
        )
        await repo.save(document)
        assert document.version == 1

        doc = await repo.get(doc_id)
        doc.convert("# Test", [], {})
        await repo.save(doc)
        assert doc.version == 2

        doc = await repo.get(doc_id)
        doc.start_analysis(uuid4(), "gemini", "user")
        await repo.save(doc)
        assert doc.version == 3

        doc = await repo.get(doc_id)
        doc.complete_analysis(0, 100.0, [], 100)
        await repo.save(doc)
        assert doc.version == 4

        # Verify events have correct versions
        events = await event_store.get_events(doc_id, 0)
        assert len(events) == 4
        # Note: events don't have a version attribute, but they're ordered correctly

    @pytest.mark.asyncio
    async def test_multiple_events_in_single_save(self):
        """Test that multiple events in a single save get sequential versions."""
        event_store = InMemoryEventStore()
        repo = DocumentRepository(event_store, InMemorySnapshotStore())

        doc_id = uuid4()
        document = Document.upload(
            document_id=doc_id,
            filename="test.pdf",
            content=b"test",
            original_format="pdf",
            uploaded_by="user"
        )
        # Add multiple operations before saving
        document.convert("# Test", [], {})

        # Save should append both events with versions 1 and 2
        await repo.save(document)

        assert document.version == 2

        # Verify both events are stored
        events = await event_store.get_events(doc_id, 0)
        assert len(events) == 2
