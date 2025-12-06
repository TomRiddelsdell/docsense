from dataclasses import dataclass
from typing import Optional, List
from uuid import UUID

from .base import QueryHandler, PaginationParams
from src.infrastructure.queries.document_queries import (
    DocumentQueries,
    DocumentView,
    DocumentDetailView,
)


@dataclass(frozen=True)
class GetDocumentById:
    document_id: UUID


@dataclass(frozen=True)
class ListDocuments:
    status: Optional[str] = None
    policy_repository_id: Optional[UUID] = None
    pagination: PaginationParams = None

    def __post_init__(self):
        object.__setattr__(self, 'pagination', self.pagination or PaginationParams())


@dataclass(frozen=True)
class CountDocuments:
    status: Optional[str] = None
    policy_repository_id: Optional[UUID] = None


class GetDocumentByIdHandler(QueryHandler[GetDocumentById, Optional[DocumentDetailView]]):
    def __init__(self, document_queries: DocumentQueries):
        self._queries = document_queries

    async def handle(self, query: GetDocumentById) -> Optional[DocumentDetailView]:
        return await self._queries.get_by_id(query.document_id)


class ListDocumentsHandler(QueryHandler[ListDocuments, List[DocumentView]]):
    def __init__(self, document_queries: DocumentQueries):
        self._queries = document_queries

    async def handle(self, query: ListDocuments) -> List[DocumentView]:
        return await self._queries.list_all(
            status=query.status,
            policy_repository_id=query.policy_repository_id,
            limit=query.pagination.limit,
            offset=query.pagination.offset
        )


class CountDocumentsHandler(QueryHandler[CountDocuments, int]):
    def __init__(self, document_queries: DocumentQueries):
        self._queries = document_queries

    async def handle(self, query: CountDocuments) -> int:
        return await self._queries.count(
            status=query.status,
            policy_repository_id=query.policy_repository_id
        )
