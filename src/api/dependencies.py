import logging
from typing import Optional, Callable

import asyncpg
from fastapi import Depends, HTTPException, Request, status

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

    @property
    def audit_logger(self):
        """Get the AuditLogger for recording document access."""
        from src.infrastructure.audit.audit_logger import AuditLogger
        if self._pool:
            return AuditLogger(self._pool)
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


async def get_document_repository():
    """Get DocumentRepository for dependency injection."""
    container = await get_container()
    return container.document_repository


# ============================================================================
# Authentication Dependencies (Phase 13)
# ============================================================================

async def get_current_user(
    request: Request,
    user_repo = Depends(get_user_repository)
):
    """Get current authenticated user from request state.
    
    Extracts Kerberos ID from request.state (set by KerberosAuthMiddleware),
    auto-registers user if first login, and returns User aggregate.
    
    Args:
        request: FastAPI request with state.kerberos_id set by middleware
        user_repo: UserRepository for loading/creating users
        
    Returns:
        User aggregate for authenticated user
        
    Raises:
        HTTPException 401: If no Kerberos ID in request state (not authenticated)
        HTTPException 403: If user account is deactivated
    """
    from src.domain.aggregates.user import User
    
    # Check if Kerberos ID is present (set by middleware)
    kerberos_id = getattr(request.state, "kerberos_id", None)
    if not kerberos_id:
        logger.warning(f"Unauthenticated request to {request.url.path}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. X-User-Kerberos header missing.",
            headers={"WWW-Authenticate": "Kerberos"},
        )
    
    # Get user groups and profile from request state
    user_groups = getattr(request.state, "user_groups", set())
    display_name = getattr(request.state, "display_name", kerberos_id)
    email = getattr(request.state, "email", f"{kerberos_id}@example.com")
    
    # Get or create user (auto-register on first authentication)
    try:
        user = await user_repo.get_or_create_from_auth(
            kerberos_id=kerberos_id,
            groups=user_groups,
            display_name=display_name,
            email=email
        )
    except Exception as e:
        logger.error(f"Failed to get/create user {kerberos_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to load user information"
        )
    
    # Check if user is active
    if not user.is_active:
        logger.warning(f"Inactive user attempted access: {kerberos_id}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated"
        )
    
    logger.debug(
        f"Authenticated user: {user.kerberos_id}, "
        f"groups={user.groups}, roles={user.roles}"
    )
    
    return user


def require_role(role):
    """Dependency factory to require a specific role.
    
    Returns a dependency function that checks if the current user
    has the specified role. Raises 403 if user lacks the role.
    
    Args:
        role: UserRole to require
        
    Returns:
        Dependency function that validates role
        
    Example:
        @router.get("/admin/users")
        async def list_users(user: User = Depends(require_admin)):
            ...
    """
    from src.domain.aggregates.user import User
    
    async def _require_role(user: User = Depends(get_current_user)) -> User:
        if not user.has_role(role):
            logger.warning(
                f"User {user.kerberos_id} lacks required role: {role.value}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{role.value}' required for this operation"
            )
        return user
    
    return _require_role


# Convenience dependencies for common roles
from src.domain.value_objects.user_role import UserRole
require_admin = require_role(UserRole.ADMIN)
require_contributor = require_role(UserRole.CONTRIBUTOR)
require_viewer = require_role(UserRole.VIEWER)
require_auditor = require_role(UserRole.AUDITOR)
