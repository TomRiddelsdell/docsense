from abc import ABC, abstractmethod
from typing import List, Callable, Awaitable, Dict, Type, Optional
import logging
import asyncio

from src.domain.events.base import DomainEvent
from src.infrastructure.projections.base import Projection
from src.infrastructure.projections.failure_tracking import ProjectionFailureTracker

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
    """
    Event publisher with built-in projection failure tracking and retry logic.
    
    This implementation follows Event Sourcing best practices:
    - Projection failures are tracked and retried with exponential backoff
    - Successful projections update checkpoints for replay capability
    - Failures don't block event processing or other projections
    - Health metrics provide observability into projection status
    """
    
    def __init__(
        self, 
        projections: List[Projection] = None,
        failure_tracker: Optional[ProjectionFailureTracker] = None,
        max_retries: int = 3,
        retry_delay_seconds: int = 1
    ):
        self._handlers: List[EventHandler] = []
        self._projections: List[Projection] = projections or []
        self._event_type_handlers: Dict[Type[DomainEvent], List[EventHandler]] = {}
        self._failure_tracker = failure_tracker
        self._max_retries = max_retries
        self._retry_delay = retry_delay_seconds

    async def publish(self, event: DomainEvent) -> None:
        event_type = type(event)
        
        # Execute general handlers (non-critical, no retry)
        for handler in self._handlers:
            try:
                await handler(event)
            except Exception as e:
                logger.error(f"Handler failed for event {event.event_type}: {e}", exc_info=True)

        # Execute type-specific handlers (non-critical, no retry)
        if event_type in self._event_type_handlers:
            for handler in self._event_type_handlers[event_type]:
                try:
                    await handler(event)
                except Exception as e:
                    logger.error(f"Typed handler failed for event {event.event_type}: {e}", exc_info=True)

        # Execute projections with retry logic
        for projection in self._projections:
            if projection.can_handle(event):
                await self._execute_projection_with_retry(event, projection)

    async def _execute_projection_with_retry(
        self, 
        event: DomainEvent, 
        projection: Projection
    ) -> None:
        """Execute a projection with automatic retry on failure."""
        projection_name = projection.__class__.__name__
        
        for attempt in range(self._max_retries):
            try:
                await projection.handle(event)
                
                # Record success if failure tracker is available
                if self._failure_tracker:
                    await self._failure_tracker.record_success(event, projection_name)
                
                return  # Success, no need to retry
                
            except Exception as e:
                is_last_attempt = attempt == self._max_retries - 1
                
                if is_last_attempt:
                    # Record failure for background retry worker
                    if self._failure_tracker:
                        await self._failure_tracker.record_failure(event, projection_name, e)
                    
                    logger.critical(
                        f"PROJECTION FAILURE: {projection_name} failed for event {event.event_type} "
                        f"after {self._max_retries} attempts. Error: {str(e)}. "
                        f"Failure tracked for background retry."
                    )
                else:
                    # Retry after delay
                    retry_delay = self._retry_delay * (2 ** attempt)  # Exponential backoff
                    logger.warning(
                        f"Projection {projection_name} failed for event {event.event_type} "
                        f"(attempt {attempt + 1}/{self._max_retries}). "
                        f"Retrying in {retry_delay}s. Error: {str(e)}"
                    )
                    await asyncio.sleep(retry_delay)

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
