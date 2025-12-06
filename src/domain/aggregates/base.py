from abc import ABC, abstractmethod
from typing import List, TypeVar
from uuid import UUID

from src.domain.events.base import DomainEvent

T = TypeVar("T", bound="Aggregate")


class Aggregate(ABC):
    def __init__(self, aggregate_id: UUID):
        self._id = aggregate_id
        self._version = 0
        self._pending_events: List[DomainEvent] = []

    @property
    def id(self) -> UUID:
        return self._id

    @property
    def version(self) -> int:
        return self._version

    @property
    def pending_events(self) -> List[DomainEvent]:
        return self._pending_events.copy()

    def clear_pending_events(self) -> List[DomainEvent]:
        events = self._pending_events.copy()
        self._pending_events.clear()
        return events

    def _apply_event(self, event: DomainEvent, is_new: bool = True) -> None:
        self._when(event)
        self._version += 1
        if is_new:
            self._pending_events.append(event)

    @abstractmethod
    def _when(self, event: DomainEvent) -> None:
        pass

    def _init_state(self) -> None:
        """Initialize aggregate-specific state. Override in subclasses."""
        pass

    @classmethod
    def reconstitute(cls: type[T], events: List[DomainEvent]) -> T:
        if not events:
            raise ValueError("Cannot reconstitute from empty events")

        aggregate = cls.__new__(cls)
        aggregate._id = events[0].aggregate_id
        aggregate._version = 0
        aggregate._pending_events = []
        aggregate._init_state()

        for event in events:
            aggregate._apply_event(event, is_new=False)

        return aggregate
