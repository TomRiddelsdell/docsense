import pytest
from uuid import uuid4
from datetime import datetime, timezone

from src.application.services.unit_of_work import UnitOfWork
from src.application.services.event_publisher import (
    InMemoryEventPublisher,
    ProjectionEventPublisher,
)
from src.domain.events.base import DomainEvent
from src.domain.events.document_events import DocumentUploaded
from tests.fixtures.mocks import MockUnitOfWork


class TestMockUnitOfWork:
    def test_commit_marks_committed(self):
        uow = MockUnitOfWork()
        assert not uow.committed

    @pytest.mark.asyncio
    async def test_commit_sets_committed_flag(self):
        uow = MockUnitOfWork()
        await uow.commit()
        assert uow.committed

    @pytest.mark.asyncio
    async def test_rollback_sets_rolled_back_flag(self):
        uow = MockUnitOfWork()
        await uow.rollback()
        assert uow.rolled_back

    @pytest.mark.asyncio
    async def test_context_manager_entry(self):
        uow = MockUnitOfWork()
        async with uow as context:
            assert context is uow

    @pytest.mark.asyncio
    async def test_context_manager_rollback_on_exception(self):
        uow = MockUnitOfWork()
        try:
            async with uow:
                raise ValueError("Test error")
        except ValueError:
            pass
        assert uow.rolled_back

    def test_register_event(self):
        uow = MockUnitOfWork()
        event = DocumentUploaded(
            aggregate_id=uuid4(),
            filename="test.pdf",
            original_format="pdf",
            file_size_bytes=1000,
            uploaded_by="user@example.com"
        )
        uow.register_event(event)
        assert len(uow._events_to_publish) == 1
        assert uow._events_to_publish[0] == event


class TestInMemoryEventPublisher:
    @pytest.mark.asyncio
    async def test_publish_single_event(self):
        publisher = InMemoryEventPublisher()
        published = []

        async def handler(event):
            published.append(event)

        publisher.subscribe(handler)

        event = DocumentUploaded(
            aggregate_id=uuid4(),
            filename="test.pdf",
            original_format="pdf",
            file_size_bytes=1000,
            uploaded_by="user@example.com"
        )
        await publisher.publish(event)

        assert len(published) == 1
        assert published[0] == event

    @pytest.mark.asyncio
    async def test_publish_multiple_events(self):
        publisher = InMemoryEventPublisher()
        published = []

        async def handler(event):
            published.append(event)

        publisher.subscribe(handler)

        events = [
            DocumentUploaded(
                aggregate_id=uuid4(),
                filename="test1.pdf",
                original_format="pdf",
                file_size_bytes=1000,
                uploaded_by="user@example.com"
            ),
            DocumentUploaded(
                aggregate_id=uuid4(),
                filename="test2.pdf",
                original_format="pdf",
                file_size_bytes=2000,
                uploaded_by="user@example.com"
            )
        ]
        await publisher.publish_all(events)

        assert len(published) == 2

    @pytest.mark.asyncio
    async def test_multiple_handlers(self):
        publisher = InMemoryEventPublisher()
        results1 = []
        results2 = []

        async def handler1(event):
            results1.append(event)

        async def handler2(event):
            results2.append(event)

        publisher.subscribe(handler1)
        publisher.subscribe(handler2)

        event = DocumentUploaded(
            aggregate_id=uuid4(),
            filename="test.pdf",
            original_format="pdf",
            file_size_bytes=1000,
            uploaded_by="user@example.com"
        )
        await publisher.publish(event)

        assert len(results1) == 1
        assert len(results2) == 1

    @pytest.mark.asyncio
    async def test_handler_error_does_not_stop_other_handlers(self):
        publisher = InMemoryEventPublisher()
        results = []

        async def failing_handler(event):
            raise Exception("Handler failed")

        async def working_handler(event):
            results.append(event)

        publisher.subscribe(failing_handler)
        publisher.subscribe(working_handler)

        event = DocumentUploaded(
            aggregate_id=uuid4(),
            filename="test.pdf",
            original_format="pdf",
            file_size_bytes=1000,
            uploaded_by="user@example.com"
        )
        await publisher.publish(event)

        assert len(results) == 1


class TestProjectionEventPublisher:
    @pytest.mark.asyncio
    async def test_publish_with_no_projections(self):
        publisher = ProjectionEventPublisher()
        event = DocumentUploaded(
            aggregate_id=uuid4(),
            filename="test.pdf",
            original_format="pdf",
            file_size_bytes=1000,
            uploaded_by="user@example.com"
        )
        await publisher.publish(event)

    @pytest.mark.asyncio
    async def test_subscribe_to_specific_event_type(self):
        publisher = ProjectionEventPublisher()
        results = []

        async def handler(event):
            results.append(event)

        publisher.subscribe_to_event(DocumentUploaded, handler)

        event = DocumentUploaded(
            aggregate_id=uuid4(),
            filename="test.pdf",
            original_format="pdf",
            file_size_bytes=1000,
            uploaded_by="user@example.com"
        )
        await publisher.publish(event)

        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_typed_handler_only_receives_matching_events(self):
        publisher = ProjectionEventPublisher()
        results = []

        async def handler(event):
            results.append(event)

        publisher.subscribe_to_event(DocumentUploaded, handler)

        from src.domain.events.document_events import DocumentConverted
        different_event = DocumentConverted(
            aggregate_id=uuid4(),
            markdown_content="# Test",
            sections=[],
            metadata={},
            conversion_warnings=[]
        )
        await publisher.publish(different_event)

        assert len(results) == 0
