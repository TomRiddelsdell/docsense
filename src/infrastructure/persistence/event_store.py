from abc import ABC, abstractmethod
from typing import List, Optional
from uuid import UUID
import json

import asyncpg

from src.domain.events import DomainEvent
from src.infrastructure.persistence.event_serializer import EventSerializer
from src.infrastructure.persistence.event_upcaster import UpcasterRegistry, create_upcaster_registry


class ConcurrencyError(Exception):
    def __init__(self, aggregate_id: UUID, expected_version: int, actual_version: int):
        self.aggregate_id = aggregate_id
        self.expected_version = expected_version
        self.actual_version = actual_version
        super().__init__(
            f"Concurrency conflict for aggregate {aggregate_id}: "
            f"expected version {expected_version}, got {actual_version}"
        )


class EventStore(ABC):
    @abstractmethod
    async def append(
        self,
        aggregate_id: UUID,
        events: List[DomainEvent],
        expected_version: int
    ) -> None:
        pass

    @abstractmethod
    async def get_events(
        self,
        aggregate_id: UUID,
        from_version: int = 0
    ) -> List[DomainEvent]:
        pass

    @abstractmethod
    async def get_all_events(
        self,
        from_position: int = 0,
        batch_size: int = 100
    ) -> List[DomainEvent]:
        pass


class PostgresEventStore(EventStore):
    def __init__(
        self, 
        pool: asyncpg.Pool, 
        serializer: Optional[EventSerializer] = None,
        upcaster_registry: Optional[UpcasterRegistry] = None
    ):
        self._pool = pool
        self._serializer = serializer or EventSerializer()
        self._upcaster_registry = upcaster_registry or create_upcaster_registry()

    async def append(
        self,
        aggregate_id: UUID,
        events: List[DomainEvent],
        expected_version: int
    ) -> None:
        if not events:
            return

        async with self._pool.acquire() as conn:
            async with conn.transaction():
                # Lock aggregate rows to prevent concurrent modifications
                # Using FOR UPDATE ensures only one transaction can check/insert at a time
                current = await conn.fetchval(
                    """
                    SELECT COALESCE(MAX(event_version), 0)
                    FROM events
                    WHERE aggregate_id = $1
                    FOR UPDATE
                    """,
                    aggregate_id
                )
                if current != expected_version:
                    raise ConcurrencyError(aggregate_id, expected_version, current)

                for i, event in enumerate(events):
                    version = expected_version + i + 1
                    payload = self._serializer.serialize(event)
                    await conn.execute(
                        """
                        INSERT INTO events 
                        (id, aggregate_id, aggregate_type, event_type, event_version, payload, metadata, created_at)
                        VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                        """,
                        event.event_id,
                        aggregate_id,
                        event.aggregate_type,
                        event.event_type,
                        version,
                        json.dumps(payload),
                        json.dumps({}),
                        event.occurred_at
                    )

    async def get_events(
        self,
        aggregate_id: UUID,
        from_version: int = 0
    ) -> List[DomainEvent]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT event_type, payload, event_version
                FROM events
                WHERE aggregate_id = $1 AND event_version > $2
                ORDER BY event_version ASC
                """,
                aggregate_id,
                from_version
            )

        events = []
        for row in rows:
            payload = json.loads(row["payload"]) if isinstance(row["payload"], str) else row["payload"]
            # Apply upcasting before deserialization
            payload = self._upcaster_registry.upcast(payload)
            event = self._serializer.deserialize(row["event_type"], payload)
            events.append(event)
        return events

    async def get_all_events(
        self,
        from_position: int = 0,
        batch_size: int = 100
    ) -> List[DomainEvent]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT event_type, payload
                FROM events
                ORDER BY created_at ASC, id ASC
                OFFSET $1 LIMIT $2
                """,
                from_position,
                batch_size
            )

        events = []
        for row in rows:
            payload = json.loads(row["payload"]) if isinstance(row["payload"], str) else row["payload"]
            # Apply upcasting before deserialization
            payload = self._upcaster_registry.upcast(payload)
            event = self._serializer.deserialize(row["event_type"], payload)
            events.append(event)
        return events

    async def get_events_count(self, aggregate_id: UUID) -> int:
        async with self._pool.acquire() as conn:
            return await conn.fetchval(
                "SELECT COUNT(*) FROM events WHERE aggregate_id = $1",
                aggregate_id
            )


class InMemoryEventStore(EventStore):
    def __init__(self):
        self._events: dict[UUID, List[DomainEvent]] = {}
        self._all_events: List[DomainEvent] = []

    async def append(
        self,
        aggregate_id: UUID,
        events: List[DomainEvent],
        expected_version: int
    ) -> None:
        if not events:
            return

        current_events = self._events.get(aggregate_id, [])
        current_version = len(current_events)

        if current_version != expected_version:
            raise ConcurrencyError(aggregate_id, expected_version, current_version)

        if aggregate_id not in self._events:
            self._events[aggregate_id] = []

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
