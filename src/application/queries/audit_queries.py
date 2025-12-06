from dataclasses import dataclass
from typing import Optional, List
from uuid import UUID

from .base import QueryHandler, PaginationParams
from src.infrastructure.queries.audit_queries import (
    AuditQueries,
    AuditLogView,
)


@dataclass(frozen=True)
class GetAuditLogById:
    audit_id: UUID


@dataclass(frozen=True)
class GetAuditLogByDocument:
    document_id: UUID
    pagination: PaginationParams = None

    def __post_init__(self):
        object.__setattr__(self, 'pagination', self.pagination or PaginationParams(limit=100))


@dataclass(frozen=True)
class GetAuditLogByUser:
    user_id: str
    pagination: PaginationParams = None

    def __post_init__(self):
        object.__setattr__(self, 'pagination', self.pagination or PaginationParams(limit=100))


@dataclass(frozen=True)
class GetRecentAuditLogs:
    event_type: Optional[str] = None
    pagination: PaginationParams = None

    def __post_init__(self):
        object.__setattr__(self, 'pagination', self.pagination or PaginationParams())


@dataclass(frozen=True)
class CountAuditLogsByDocument:
    document_id: UUID


class GetAuditLogByIdHandler(QueryHandler[GetAuditLogById, Optional[AuditLogView]]):
    def __init__(self, audit_queries: AuditQueries):
        self._queries = audit_queries

    async def handle(self, query: GetAuditLogById) -> Optional[AuditLogView]:
        return await self._queries.get_by_id(query.audit_id)


class GetAuditLogByDocumentHandler(QueryHandler[GetAuditLogByDocument, List[AuditLogView]]):
    def __init__(self, audit_queries: AuditQueries):
        self._queries = audit_queries

    async def handle(self, query: GetAuditLogByDocument) -> List[AuditLogView]:
        return await self._queries.get_by_document(
            document_id=query.document_id,
            limit=query.pagination.limit,
            offset=query.pagination.offset
        )


class GetAuditLogByUserHandler(QueryHandler[GetAuditLogByUser, List[AuditLogView]]):
    def __init__(self, audit_queries: AuditQueries):
        self._queries = audit_queries

    async def handle(self, query: GetAuditLogByUser) -> List[AuditLogView]:
        return await self._queries.get_by_user(
            user_id=query.user_id,
            limit=query.pagination.limit,
            offset=query.pagination.offset
        )


class GetRecentAuditLogsHandler(QueryHandler[GetRecentAuditLogs, List[AuditLogView]]):
    def __init__(self, audit_queries: AuditQueries):
        self._queries = audit_queries

    async def handle(self, query: GetRecentAuditLogs) -> List[AuditLogView]:
        return await self._queries.get_recent(
            limit=query.pagination.limit,
            offset=query.pagination.offset,
            event_type=query.event_type
        )


class CountAuditLogsByDocumentHandler(QueryHandler[CountAuditLogsByDocument, int]):
    def __init__(self, audit_queries: AuditQueries):
        self._queries = audit_queries

    async def handle(self, query: CountAuditLogsByDocument) -> int:
        return await self._queries.count_by_document(query.document_id)
