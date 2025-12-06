from abc import ABC, abstractmethod
from typing import Generic, TypeVar, Optional, Type, List
from uuid import UUID

from src.domain.aggregates.base import Aggregate
from src.infrastructure.persistence.event_store import EventStore
from src.infrastructure.persistence.snapshot_store import SnapshotStore, Snapshot

T = TypeVar("T", bound=Aggregate)


class Repository(ABC, Generic[T]):
    def __init__(
        self,
        event_store: EventStore,
        snapshot_store: Optional[SnapshotStore] = None,
        snapshot_threshold: int = 10
    ):
        self._event_store = event_store
        self._snapshot_store = snapshot_store
        self._snapshot_threshold = snapshot_threshold

    @abstractmethod
    def _aggregate_type(self) -> Type[T]:
        pass

    @abstractmethod
    def _aggregate_type_name(self) -> str:
        pass

    async def get(self, aggregate_id: UUID) -> Optional[T]:
        from_version = 0
        aggregate = None

        if self._snapshot_store:
            snapshot = await self._snapshot_store.get(aggregate_id)
            if snapshot:
                from_version = snapshot.version
                aggregate = self._restore_from_snapshot(snapshot)

        events = await self._event_store.get_events(aggregate_id, from_version)

        if not events and aggregate is None:
            return None

        if aggregate is None:
            aggregate = self._aggregate_type().reconstitute(events)
        else:
            for event in events:
                aggregate._apply_event(event, is_new=False)

        return aggregate

    async def save(self, aggregate: T) -> None:
        events = aggregate.clear_pending_events()
        if not events:
            return

        expected_version = aggregate.version - len(events)
        await self._event_store.append(
            aggregate.id,
            events,
            expected_version
        )

        if self._snapshot_store and aggregate.version >= self._snapshot_threshold:
            if aggregate.version % self._snapshot_threshold == 0:
                snapshot = self._create_snapshot(aggregate)
                await self._snapshot_store.save(snapshot)

    async def exists(self, aggregate_id: UUID) -> bool:
        events = await self._event_store.get_events(aggregate_id, 0)
        return len(events) > 0

    def _create_snapshot(self, aggregate: T) -> Snapshot:
        state = self._serialize_aggregate(aggregate)
        return Snapshot(
            aggregate_id=aggregate.id,
            aggregate_type=self._aggregate_type_name(),
            version=aggregate.version,
            state=state
        )

    def _restore_from_snapshot(self, snapshot: Snapshot) -> T:
        aggregate = self._deserialize_aggregate(snapshot.state)
        return aggregate

    @abstractmethod
    def _serialize_aggregate(self, aggregate: T) -> dict:
        pass

    @abstractmethod
    def _deserialize_aggregate(self, state: dict) -> T:
        pass
