from dataclasses import dataclass
from typing import Optional, List
from uuid import UUID

from .base import QueryHandler
from src.infrastructure.queries.feedback_queries import (
    FeedbackQueries,
    FeedbackView,
)


@dataclass(frozen=True)
class GetFeedbackById:
    feedback_id: UUID


@dataclass(frozen=True)
class GetFeedbackByDocument:
    document_id: UUID
    status: Optional[str] = None


@dataclass(frozen=True)
class GetPendingFeedback:
    document_id: UUID


@dataclass(frozen=True)
class CountFeedbackByDocument:
    document_id: UUID
    status: Optional[str] = None


class GetFeedbackByIdHandler(QueryHandler[GetFeedbackById, Optional[FeedbackView]]):
    def __init__(self, feedback_queries: FeedbackQueries):
        self._queries = feedback_queries

    async def handle(self, query: GetFeedbackById) -> Optional[FeedbackView]:
        return await self._queries.get_by_id(query.feedback_id)


class GetFeedbackByDocumentHandler(QueryHandler[GetFeedbackByDocument, List[FeedbackView]]):
    def __init__(self, feedback_queries: FeedbackQueries):
        self._queries = feedback_queries

    async def handle(self, query: GetFeedbackByDocument) -> List[FeedbackView]:
        return await self._queries.get_by_document(
            document_id=query.document_id,
            status=query.status
        )


class GetPendingFeedbackHandler(QueryHandler[GetPendingFeedback, List[FeedbackView]]):
    def __init__(self, feedback_queries: FeedbackQueries):
        self._queries = feedback_queries

    async def handle(self, query: GetPendingFeedback) -> List[FeedbackView]:
        return await self._queries.get_pending_by_document(query.document_id)


class CountFeedbackByDocumentHandler(QueryHandler[CountFeedbackByDocument, int]):
    def __init__(self, feedback_queries: FeedbackQueries):
        self._queries = feedback_queries

    async def handle(self, query: CountFeedbackByDocument) -> int:
        return await self._queries.count_by_document(
            document_id=query.document_id,
            status=query.status
        )
