from abc import ABC, abstractmethod
from typing import List, Optional
import asyncpg

from src.domain.events.base import DomainEvent


class UnitOfWork(ABC):
    @abstractmethod
    async def __aenter__(self) -> "UnitOfWork":
        pass

    @abstractmethod
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> bool:
        pass

    @abstractmethod
    async def commit(self) -> None:
        pass

    @abstractmethod
    async def rollback(self) -> None:
        pass

    @abstractmethod
    def register_event(self, event: DomainEvent) -> None:
        pass

    @abstractmethod
    def get_pending_events(self) -> List[DomainEvent]:
        pass


class PostgresUnitOfWork(UnitOfWork):
    def __init__(self, pool: asyncpg.Pool):
        self._pool = pool
        self._connection: Optional[asyncpg.Connection] = None
        self._transaction = None
        self._pending_events: List[DomainEvent] = []
        self._committed = False

    async def __aenter__(self) -> "PostgresUnitOfWork":
        self._connection = await self._pool.acquire()
        self._transaction = self._connection.transaction()
        await self._transaction.start()
        self._pending_events = []
        self._committed = False
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> bool:
        try:
            if exc_type is not None:
                await self.rollback()
            elif not self._committed:
                await self.rollback()
        finally:
            if self._connection:
                await self._pool.release(self._connection)
                self._connection = None
        return False

    async def commit(self) -> None:
        if self._transaction:
            await self._transaction.commit()
            self._committed = True

    async def rollback(self) -> None:
        if self._transaction and not self._committed:
            try:
                await self._transaction.rollback()
            except Exception:
                pass

    def register_event(self, event: DomainEvent) -> None:
        self._pending_events.append(event)

    def get_pending_events(self) -> List[DomainEvent]:
        return self._pending_events.copy()

    @property
    def connection(self) -> Optional[asyncpg.Connection]:
        return self._connection
