from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TypeVar, Generic, Optional, List

TQuery = TypeVar('TQuery')
TResult = TypeVar('TResult')


@dataclass(frozen=True)
class PaginationParams:
    limit: int = 50
    offset: int = 0


class QueryHandler(ABC, Generic[TQuery, TResult]):
    @abstractmethod
    async def handle(self, query: TQuery) -> TResult:
        pass


class QueryDispatcher:
    def __init__(self):
        self._handlers: dict = {}

    def register(self, query_type: type, handler: QueryHandler) -> None:
        self._handlers[query_type] = handler

    async def dispatch(self, query) -> any:
        query_type = type(query)
        handler = self._handlers.get(query_type)
        if handler is None:
            raise QueryHandlerNotFound(query_type=query_type)
        return await handler.handle(query)


class QueryHandlerNotFound(Exception):
    def __init__(self, query_type: type):
        self.query_type = query_type
        super().__init__(f"No handler registered for query type: {query_type.__name__}")
