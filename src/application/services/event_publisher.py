from abc import ABC, abstractmethod
from typing import List, Callable, Awaitable, Dict, Type
import logging

from src.domain.events.base import DomainEvent
from src.infrastructure.projections.base import Projection

logger = logging.getLogger(__name__)

EventHandler = Callable[[DomainEvent], Awaitable[None]]


class EventPublisher(ABC):
    @abstractmethod
    async def publish(self, event: DomainEvent) -> None:
        pass

    @abstractmethod
    async def publish_all(self, events: List[DomainEvent]) -> None:
        pass

    @abstractmethod
    def subscribe(self, handler: EventHandler) -> None:
        pass


class InMemoryEventPublisher(EventPublisher):
    def __init__(self):
        self._handlers: List[EventHandler] = []
        self._projections: List[Projection] = []
        self._event_type_handlers: Dict[Type[DomainEvent], List[EventHandler]] = {}

    async def publish(self, event: DomainEvent) -> None:
        event_type = type(event)
        projection_errors = []

        # Call general handlers
        for handler in self._handlers:
            try:
                await handler(event)
            except Exception as e:
                logger.error(f"Handler failed for event {event.event_type}: {e}", exc_info=True)

        # Call type-specific handlers
        if event_type in self._event_type_handlers:
            for handler in self._event_type_handlers[event_type]:
                try:
                    await handler(event)
                except Exception as e:
                    logger.error(f"Typed handler failed for event {event.event_type}: {e}", exc_info=True)

        # Call projections - collect errors but continue
        for projection in self._projections:
            if projection.can_handle(event):
                try:
                    await projection.handle(event)
                except Exception as e:
                    error_msg = f"Projection {projection.__class__.__name__} failed for event {event.event_type}: {e}"
                    logger.error(error_msg, exc_info=True)
                    projection_errors.append((projection.__class__.__name__, str(e)))

        # If any projections failed, log critical warning about data inconsistency
        if projection_errors:
            logger.critical(
                f"PROJECTION FAILURE: {len(projection_errors)} projection(s) failed for event {event.event_type}. "
                f"Read models may be inconsistent with event store. "
                f"Failed projections: {', '.join([name for name, _ in projection_errors])}"
            )

    async def publish_all(self, events: List[DomainEvent]) -> None:
        for event in events:
            await self.publish(event)

    def subscribe(self, handler: EventHandler) -> None:
        self._handlers.append(handler)

    def subscribe_to_event(
        self,
        event_type: Type[DomainEvent],
        handler: EventHandler
    ) -> None:
        """Subscribe a handler to a specific event type."""
        if event_type not in self._event_type_handlers:
            self._event_type_handlers[event_type] = []
        self._event_type_handlers[event_type].append(handler)

    def register_projection(self, projection: Projection) -> None:
        self._projections.append(projection)


class ProjectionEventPublisher(EventPublisher):
    def __init__(self, projections: List[Projection] = None):
        self._handlers: List[EventHandler] = []
        self._projections: List[Projection] = projections or []
        self._event_type_handlers: Dict[Type[DomainEvent], List[EventHandler]] = {}

    async def publish(self, event: DomainEvent) -> None:
        event_type = type(event)
        projection_errors = []

        for handler in self._handlers:
            try:
                await handler(event)
            except Exception as e:
                logger.error(f"Handler failed for event {event.event_type}: {e}", exc_info=True)

        if event_type in self._event_type_handlers:
            for handler in self._event_type_handlers[event_type]:
                try:
                    await handler(event)
                except Exception as e:
                    logger.error(f"Typed handler failed for event {event.event_type}: {e}", exc_info=True)

        for projection in self._projections:
            if projection.can_handle(event):
                try:
                    await projection.handle(event)
                except Exception as e:
                    error_msg = f"Projection {projection.__class__.__name__} failed for event {event.event_type}: {e}"
                    logger.error(error_msg, exc_info=True)
                    projection_errors.append((projection.__class__.__name__, str(e)))

        # If any projections failed, log critical warning about data inconsistency
        if projection_errors:
            logger.critical(
                f"PROJECTION FAILURE: {len(projection_errors)} projection(s) failed for event {event.event_type}. "
                f"Read models may be inconsistent with event store. "
                f"Failed projections: {', '.join([name for name, _ in projection_errors])}"
            )

    async def publish_all(self, events: List[DomainEvent]) -> None:
        for event in events:
            await self.publish(event)

    def subscribe(self, handler: EventHandler) -> None:
        self._handlers.append(handler)

    def subscribe_to_event(
        self,
        event_type: Type[DomainEvent],
        handler: EventHandler
    ) -> None:
        if event_type not in self._event_type_handlers:
            self._event_type_handlers[event_type] = []
        self._event_type_handlers[event_type].append(handler)

    def register_projection(self, projection: Projection) -> None:
        self._projections.append(projection)
