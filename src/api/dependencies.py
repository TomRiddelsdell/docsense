import logging
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
from src.infrastructure.projections.policy_projector import PolicyProjection
from src.infrastructure.projections.failure_tracking import ProjectionFailureTracker
from src.application.services.event_publisher import InMemoryEventPublisher, ProjectionEventPublisher
from src.application.event_handlers.semantic_curation_handler import SemanticCurationEventHandler
from src.infrastructure.persistence.postgres_connection import PostgresConnection
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
from .config import get_settings, Settings


class Container:
    _instance: Optional["Container"] = None
    _pool: Optional[asyncpg.Pool] = None

    def __init__(self, settings: Settings):
        self._settings = settings
        self._event_store: Optional[PostgresEventStore] = None
        self._snapshot_store: Optional[InMemorySnapshotStore] = None
        self._event_publisher: Optional[InMemoryEventPublisher] = None
        self._failure_tracker: Optional[ProjectionFailureTracker] = None
        self._converter_factory: Optional[ConverterFactory] = None

    @classmethod
    async def get_instance(cls) -> "Container":
        if cls._instance is None:
            settings = get_settings()
            cls._instance = cls(settings)
            await cls._instance._initialize()
        return cls._instance

    async def _initialize(self) -> None:
        if self._pool is None and self._settings.DATABASE_URL:
            self._pool = await asyncpg.create_pool(
                self._settings.DATABASE_URL,
                min_size=self._settings.DB_POOL_MIN_SIZE,
                max_size=self._settings.DB_POOL_MAX_SIZE,
            )
            self._register_projections()

    def _register_projections(self) -> None:
        if self._pool:
            logger.info("Registering projections and event handlers with event publisher")

            # Register projections
            document_projection = DocumentProjection(self._pool)
            self.event_publisher.register_projection(document_projection)
            policy_projection = PolicyProjection(self._pool)
            self.event_publisher.register_projection(policy_projection)

            # Register event handlers
            db_connection = PostgresConnection(self._pool)
            semantic_curation_handler = SemanticCurationEventHandler(
                document_repository=self.document_repository,
                event_publisher=self.event_publisher,
                db_connection=db_connection,
                enabled=True,
            )

            # Subscribe to DocumentConverted events
            from src.domain.events.document_events import DocumentConverted
            self.event_publisher.subscribe_to_event(DocumentConverted, semantic_curation_handler.handle)

            logger.info(
                f"Registered {len(self.event_publisher._projections)} projections and "
                f"{len(self.event_publisher._handlers)} event handlers"
            )

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
    def failure_tracker(self) -> Optional[ProjectionFailureTracker]:
        if self._failure_tracker is None and self._pool:
            self._failure_tracker = ProjectionFailureTracker(self._pool)
        return self._failure_tracker

    @property
    def event_publisher(self) -> InMemoryEventPublisher:
        if self._event_publisher is None:
            # Use ProjectionEventPublisher with failure tracking if pool is available
            if self._pool and self.failure_tracker:
                self._event_publisher = ProjectionEventPublisher(
                    projections=[],  # Will be registered in _register_projections
                    failure_tracker=self.failure_tracker,
                    max_retries=3,
                    retry_delay_seconds=1
                )
            else:
                # Fallback to InMemoryEventPublisher for testing without DB
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
    def user_repository(self):
        from src.infrastructure.repositories.user_repository import UserRepository
        return UserRepository(self.event_store, self.snapshot_store)

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
    from src.infrastructure.ai.provider_factory import ProviderFactory
    return StartAnalysisHandler(
        document_repository=container.document_repository,
        policy_repository=container.policy_repository,
        event_publisher=container.event_publisher,
        provider_factory=ProviderFactory(),
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


async def get_user_repository():
    """Get UserRepository for dependency injection."""
    container = await get_container()
    return container.user_repository


async def get_authorization_service():
    """Get AuthorizationService for dependency injection."""
    from src.domain.services.authorization_service import AuthorizationService
    return AuthorizationService()
