from abc import ABC, abstractmethod
from typing import Generic, TypeVar, Optional, Type, List
from uuid import UUID
import asyncio
import logging

from src.domain.aggregates.base import Aggregate
from src.infrastructure.persistence.event_store import EventStore, ConcurrencyError
from src.infrastructure.persistence.snapshot_store import SnapshotStore, Snapshot

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=Aggregate)


class Repository(ABC, Generic[T]):
    def __init__(
        self,
        event_store: EventStore,
        snapshot_store: Optional[SnapshotStore] = None,
        snapshot_threshold: int = 10,
        max_retries: int = 3,
        retry_delay_ms: int = 50
    ):
        self._event_store = event_store
        self._snapshot_store = snapshot_store
        self._snapshot_threshold = snapshot_threshold
        self._max_retries = max_retries
        self._retry_delay_ms = retry_delay_ms

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
        """
        Save aggregate with automatic retry on concurrency conflicts.

        Implements optimistic locking with retry logic to handle transient
        conflicts. Note: For business logic retry (when aggregate state changes),
        callers should implement retry at the command handler level.
        """
        events = aggregate.clear_pending_events()
        if not events:
            return

        expected_version = aggregate.version - len(events)

        # Retry logic for concurrency conflicts with exponential backoff
        last_error = None
        for attempt in range(self._max_retries):
            try:
                await self._event_store.append(
                    aggregate.id,
                    events,
                    expected_version
                )

                # Success - create snapshot if threshold reached
                if self._snapshot_store and aggregate.version >= self._snapshot_threshold:
                    if aggregate.version % self._snapshot_threshold == 0:
                        snapshot = self._create_snapshot(aggregate)
                        await self._snapshot_store.save(snapshot)

                return  # Success, exit retry loop

            except ConcurrencyError as e:
                last_error = e
                if attempt < self._max_retries - 1:
                    # Not the last attempt - wait and retry
                    logger.warning(
                        f"Concurrency conflict on attempt {attempt + 1}/{self._max_retries} "
                        f"for aggregate {aggregate.id}: expected version {expected_version}, "
                        f"got {e.actual_version}. Retrying after delay..."
                    )

                    # Exponential backoff: 50ms, 100ms, 200ms
                    delay = self._retry_delay_ms * (2 ** attempt) / 1000.0
                    await asyncio.sleep(delay)
                else:
                    # Last attempt failed - log and re-raise
                    logger.error(
                        f"Concurrency conflict persisted after {self._max_retries} attempts "
                        f"for aggregate {aggregate.id}. Expected version {expected_version}, "
                        f"actual version {e.actual_version}."
                    )

        # If we get here, all retries failed - re-raise the last error
        if last_error:
            raise last_error

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
