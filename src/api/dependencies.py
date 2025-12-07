import os
import logging
from dataclasses import dataclass
from functools import lru_cache
from typing import Optional

import asyncpg

logger = logging.getLogger(__name__)

from src.infrastructure.persistence.event_store import PostgresEventStore
from src.infrastructure.persistence.snapshot_store import InMemorySnapshotStore
from src.infrastructure.repositories.document_repository import DocumentRepository
from src.infrastructure.repositories.feedback_repository import FeedbackSessionRepository
from src.infrastructure.repositories.policy_repository import PolicyRepositoryRepository
from src.infrastructure.queries.document_queries import DocumentQueries
from src.infrastructure.queries.feedback_queries import FeedbackQueries
from src.infrastructure.queries.policy_queries import PolicyQueries
from src.infrastructure.queries.audit_queries import AuditQueries
from src.infrastructure.converters.converter_factory import ConverterFactory
from src.infrastructure.projections.document_projector import DocumentProjection
from src.application.services.event_publisher import InMemoryEventPublisher
from src.application.commands.document_handlers import (
    UploadDocumentHandler,
    ExportDocumentHandler,
    DeleteDocumentHandler,
)
from src.application.commands.analysis_handlers import (
    StartAnalysisHandler,
    CancelAnalysisHandler,
)
from src.application.commands.feedback_handlers import (
    AcceptChangeHandler,
    RejectChangeHandler,
    ModifyChangeHandler,
)
from src.application.commands.policy_handlers import (
    CreatePolicyRepositoryHandler,
    AddPolicyHandler,
    AssignDocumentToPolicyHandler,
)
from src.application.queries.document_queries import (
    GetDocumentByIdHandler,
    ListDocumentsHandler,
    CountDocumentsHandler,
)
from src.application.queries.feedback_queries import (
    GetFeedbackByDocumentHandler,
    GetFeedbackByIdHandler,
    CountFeedbackByDocumentHandler,
)
from src.application.queries.policy_queries import (
    GetPolicyRepositoryByIdHandler,
    ListPolicyRepositoriesHandler,
    GetPoliciesByRepositoryHandler,
)
from src.application.queries.audit_queries import (
    GetRecentAuditLogsHandler,
    GetAuditLogByDocumentHandler,
)


@dataclass
class Settings:
    database_url: str
    pool_min_size: int = 5
    pool_max_size: int = 20


@lru_cache
def get_settings() -> Settings:
    database_url = os.environ.get("DATABASE_URL", "")
    return Settings(database_url=database_url)


class Container:
    _instance: Optional["Container"] = None
    _pool: Optional[asyncpg.Pool] = None

    def __init__(self, settings: Settings):
        self._settings = settings
        self._event_store: Optional[PostgresEventStore] = None
        self._snapshot_store: Optional[InMemorySnapshotStore] = None
        self._event_publisher: Optional[InMemoryEventPublisher] = None
        self._converter_factory: Optional[ConverterFactory] = None

    @classmethod
    async def get_instance(cls) -> "Container":
        if cls._instance is None:
            settings = get_settings()
            cls._instance = cls(settings)
            await cls._instance._initialize()
        return cls._instance

    async def _initialize(self) -> None:
        if self._pool is None and self._settings.database_url:
            self._pool = await asyncpg.create_pool(
                self._settings.database_url,
                min_size=self._settings.pool_min_size,
                max_size=self._settings.pool_max_size,
            )
            self._register_projections()

    def _register_projections(self) -> None:
        if self._pool:
            logger.info("Registering projections with event publisher")
            document_projection = DocumentProjection(self._pool)
            self.event_publisher.register_projection(document_projection)
            logger.info(f"Registered DocumentProjection, event_publisher now has {len(self.event_publisher._projections)} projections")

    async def close(self) -> None:
        if self._pool:
            await self._pool.close()
            self._pool = None

    @property
    def pool(self) -> Optional[asyncpg.Pool]:
        return self._pool

    @property
    def event_store(self) -> PostgresEventStore:
        if self._event_store is None and self._pool:
            self._event_store = PostgresEventStore(self._pool)
        return self._event_store

    @property
    def snapshot_store(self) -> InMemorySnapshotStore:
        if self._snapshot_store is None:
            self._snapshot_store = InMemorySnapshotStore()
        return self._snapshot_store

    @property
    def event_publisher(self) -> InMemoryEventPublisher:
        if self._event_publisher is None:
            self._event_publisher = InMemoryEventPublisher()
        return self._event_publisher

    @property
    def converter_factory(self) -> ConverterFactory:
        if self._converter_factory is None:
            self._converter_factory = ConverterFactory()
        return self._converter_factory

    @property
    def document_repository(self) -> DocumentRepository:
        return DocumentRepository(self.event_store, self.snapshot_store)

    @property
    def feedback_repository(self) -> FeedbackSessionRepository:
        return FeedbackSessionRepository(self.event_store, self.snapshot_store)

    @property
    def policy_repository(self) -> PolicyRepositoryRepository:
        return PolicyRepositoryRepository(self.event_store, self.snapshot_store)

    @property
    def document_queries(self) -> Optional[DocumentQueries]:
        if self._pool:
            return DocumentQueries(self._pool)
        return None

    @property
    def feedback_queries(self) -> Optional[FeedbackQueries]:
        if self._pool:
            return FeedbackQueries(self._pool)
        return None

    @property
    def policy_queries(self) -> Optional[PolicyQueries]:
        if self._pool:
            return PolicyQueries(self._pool)
        return None

    @property
    def audit_queries(self) -> Optional[AuditQueries]:
        if self._pool:
            return AuditQueries(self._pool)
        return None


async def get_container() -> Container:
    return await Container.get_instance()


async def get_upload_document_handler() -> UploadDocumentHandler:
    container = await get_container()
    return UploadDocumentHandler(
        document_repository=container.document_repository,
        converter_factory=container.converter_factory,
        event_publisher=container.event_publisher,
    )


async def get_export_document_handler() -> ExportDocumentHandler:
    container = await get_container()
    return ExportDocumentHandler(
        document_repository=container.document_repository,
        event_publisher=container.event_publisher,
    )


async def get_delete_document_handler() -> DeleteDocumentHandler:
    container = await get_container()
    return DeleteDocumentHandler(
        document_repository=container.document_repository,
        event_publisher=container.event_publisher,
    )


async def get_start_analysis_handler() -> StartAnalysisHandler:
    container = await get_container()
    return StartAnalysisHandler(
        document_repository=container.document_repository,
        policy_repository=container.policy_repository,
        event_publisher=container.event_publisher,
    )


async def get_cancel_analysis_handler() -> CancelAnalysisHandler:
    container = await get_container()
    return CancelAnalysisHandler(
        document_repository=container.document_repository,
        event_publisher=container.event_publisher,
    )


async def get_accept_change_handler() -> AcceptChangeHandler:
    container = await get_container()
    return AcceptChangeHandler(
        feedback_repository=container.feedback_repository,
        event_publisher=container.event_publisher,
    )


async def get_reject_change_handler() -> RejectChangeHandler:
    container = await get_container()
    return RejectChangeHandler(
        feedback_repository=container.feedback_repository,
        event_publisher=container.event_publisher,
    )


async def get_modify_change_handler() -> ModifyChangeHandler:
    container = await get_container()
    return ModifyChangeHandler(
        feedback_repository=container.feedback_repository,
        event_publisher=container.event_publisher,
    )


async def get_create_policy_repository_handler() -> CreatePolicyRepositoryHandler:
    container = await get_container()
    return CreatePolicyRepositoryHandler(
        policy_repository=container.policy_repository,
        event_publisher=container.event_publisher,
    )


async def get_add_policy_handler() -> AddPolicyHandler:
    container = await get_container()
    return AddPolicyHandler(
        policy_repository=container.policy_repository,
        event_publisher=container.event_publisher,
    )


async def get_assign_document_handler() -> AssignDocumentToPolicyHandler:
    container = await get_container()
    return AssignDocumentToPolicyHandler(
        policy_repository=container.policy_repository,
        document_repository=container.document_repository,
        event_publisher=container.event_publisher,
    )


async def get_document_by_id_handler() -> GetDocumentByIdHandler:
    container = await get_container()
    return GetDocumentByIdHandler(document_queries=container.document_queries)


async def get_list_documents_handler() -> ListDocumentsHandler:
    container = await get_container()
    return ListDocumentsHandler(document_queries=container.document_queries)


async def get_count_documents_handler() -> CountDocumentsHandler:
    container = await get_container()
    return CountDocumentsHandler(document_queries=container.document_queries)


async def get_feedback_by_document_handler() -> GetFeedbackByDocumentHandler:
    container = await get_container()
    return GetFeedbackByDocumentHandler(feedback_queries=container.feedback_queries)


async def get_feedback_by_id_handler() -> GetFeedbackByIdHandler:
    container = await get_container()
    return GetFeedbackByIdHandler(feedback_queries=container.feedback_queries)


async def get_count_feedback_handler() -> CountFeedbackByDocumentHandler:
    container = await get_container()
    return CountFeedbackByDocumentHandler(feedback_queries=container.feedback_queries)


async def get_policy_repository_handler() -> GetPolicyRepositoryByIdHandler:
    container = await get_container()
    return GetPolicyRepositoryByIdHandler(policy_queries=container.policy_queries)


async def get_list_policy_repositories_handler() -> ListPolicyRepositoriesHandler:
    container = await get_container()
    return ListPolicyRepositoriesHandler(policy_queries=container.policy_queries)


async def get_policies_handler() -> GetPoliciesByRepositoryHandler:
    container = await get_container()
    return GetPoliciesByRepositoryHandler(policy_queries=container.policy_queries)


async def get_audit_trail_handler() -> GetRecentAuditLogsHandler:
    container = await get_container()
    return GetRecentAuditLogsHandler(audit_queries=container.audit_queries)


async def get_document_audit_handler() -> GetAuditLogByDocumentHandler:
    container = await get_container()
    return GetAuditLogByDocumentHandler(audit_queries=container.audit_queries)
