from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable, Any, Awaitable, Union
from uuid import UUID

from src.domain.aggregates.document import Document
from src.domain.aggregates.feedback_session import FeedbackSession
from src.domain.aggregates.policy_repository import PolicyRepository
from src.domain.events.base import DomainEvent


class MockEventStore:
    def __init__(self):
        self._events: Dict[UUID, List[DomainEvent]] = {}
        self._all_events: List[DomainEvent] = []

    async def append(
        self,
        aggregate_id: UUID,
        events: List[DomainEvent],
        expected_version: int
    ) -> None:
        if aggregate_id not in self._events:
            self._events[aggregate_id] = []
        current_version = len(self._events[aggregate_id])
        if current_version != expected_version:
            raise Exception(f"Concurrency error: expected {expected_version}, got {current_version}")
        self._events[aggregate_id].extend(events)
        self._all_events.extend(events)

    async def get_events(
        self,
        aggregate_id: UUID,
        from_version: int = 0
    ) -> List[DomainEvent]:
        events = self._events.get(aggregate_id, [])
        return events[from_version:]

    async def get_all_events(
        self,
        from_position: int = 0,
        batch_size: int = 100
    ) -> List[DomainEvent]:
        return self._all_events[from_position:from_position + batch_size]

    def clear(self) -> None:
        self._events.clear()
        self._all_events.clear()


class MockSnapshotStore:
    def __init__(self):
        self._snapshots: Dict[UUID, Any] = {}

    async def get(self, aggregate_id: UUID) -> Optional[Any]:
        return self._snapshots.get(aggregate_id)

    async def save(self, snapshot: Any) -> None:
        self._snapshots[snapshot.aggregate_id] = snapshot

    def clear(self) -> None:
        self._snapshots.clear()


class MockDocumentRepository:
    def __init__(self):
        self._documents: Dict[UUID, Document] = {}
        self._save_calls: List[Document] = []

    async def get(self, aggregate_id: UUID) -> Optional[Document]:
        return self._documents.get(aggregate_id)

    async def save(self, aggregate: Document) -> None:
        self._documents[aggregate.id] = aggregate
        self._save_calls.append(aggregate)

    async def exists(self, aggregate_id: UUID) -> bool:
        return aggregate_id in self._documents

    def add(self, document: Document) -> None:
        self._documents[document.id] = document

    def clear(self) -> None:
        self._documents.clear()
        self._save_calls.clear()


class MockFeedbackRepository:
    def __init__(self):
        self._sessions: Dict[UUID, FeedbackSession] = {}
        self._save_calls: List[FeedbackSession] = []

    async def get(self, aggregate_id: UUID) -> Optional[FeedbackSession]:
        return self._sessions.get(aggregate_id)

    async def save(self, aggregate: FeedbackSession) -> None:
        self._sessions[aggregate.id] = aggregate
        self._save_calls.append(aggregate)

    async def exists(self, aggregate_id: UUID) -> bool:
        return aggregate_id in self._sessions

    def add(self, session: FeedbackSession) -> None:
        self._sessions[session.id] = session

    def clear(self) -> None:
        self._sessions.clear()
        self._save_calls.clear()


class MockPolicyRepository:
    def __init__(self):
        self._repositories: Dict[UUID, PolicyRepository] = {}
        self._save_calls: List[PolicyRepository] = []

    async def get(self, aggregate_id: UUID) -> Optional[PolicyRepository]:
        return self._repositories.get(aggregate_id)

    async def save(self, aggregate: PolicyRepository) -> None:
        self._repositories[aggregate.id] = aggregate
        self._save_calls.append(aggregate)

    async def exists(self, aggregate_id: UUID) -> bool:
        return aggregate_id in self._repositories

    def add(self, repo: PolicyRepository) -> None:
        self._repositories[repo.id] = repo

    def clear(self) -> None:
        self._repositories.clear()
        self._save_calls.clear()


class MockEventPublisher:
    def __init__(self):
        self._published_events: List[DomainEvent] = []
        self._handlers: List[Callable[[DomainEvent], Union[None, Awaitable[None]]]] = []

    async def publish(self, event: DomainEvent) -> None:
        self._published_events.append(event)
        for handler in self._handlers:
            result = handler(event)
            if result is not None:
                await result

    async def publish_all(self, events: List[DomainEvent]) -> None:
        for event in events:
            await self.publish(event)

    def subscribe(self, handler: Callable[[DomainEvent], Union[None, Awaitable[None]]]) -> None:
        self._handlers.append(handler)

    @property
    def published_events(self) -> List[DomainEvent]:
        return self._published_events.copy()

    def clear(self) -> None:
        self._published_events.clear()


class MockConverterFactory:
    def __init__(self, success: bool = True, markdown: str = "", sections: Optional[List[dict]] = None):
        self._success = success
        self._markdown = markdown
        self._sections = sections if sections is not None else []
        self._convert_calls: List[tuple] = []

    def get_converter(self, file_path):
        return MockConverter(self._success, self._markdown, self._sections)

    def get_converter_for_extension(self, extension: str):
        return MockConverter(self._success, self._markdown, self._sections)

    def convert_from_bytes(self, content: bytes, filename: str):
        self._convert_calls.append((content, filename))
        return MockConversionResult(
            success=self._success,
            markdown_content=self._markdown,
            sections=self._sections,
            metadata={"original_format": "pdf"},
            errors=[] if self._success else ["Conversion failed"]
        )


class MockConverter:
    def __init__(self, success: bool = True, markdown: str = "", sections: Optional[List[dict]] = None):
        self._success = success
        self._markdown = markdown
        self._sections = sections if sections is not None else []

    def convert_from_bytes(self, content: bytes, filename: str):
        return MockConversionResult(
            success=self._success,
            markdown_content=self._markdown,
            sections=self._sections,
            metadata={"original_format": "pdf"},
            errors=[] if self._success else ["Conversion failed"]
        )


@dataclass
class MockConversionResult:
    success: bool
    markdown_content: str
    sections: List[dict]
    metadata: dict
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class MockUnitOfWork:
    def __init__(self):
        self._committed = False
        self._rolled_back = False
        self._events_to_publish: List[DomainEvent] = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            await self.rollback()
        return False

    async def commit(self) -> None:
        self._committed = True

    async def rollback(self) -> None:
        self._rolled_back = True

    def register_event(self, event: DomainEvent) -> None:
        self._events_to_publish.append(event)

    @property
    def committed(self) -> bool:
        return self._committed

    @property
    def rolled_back(self) -> bool:
        return self._rolled_back
