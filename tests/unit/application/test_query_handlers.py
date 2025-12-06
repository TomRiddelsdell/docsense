import pytest
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional
from uuid import uuid4, UUID

from src.application.queries import (
    QueryDispatcher,
    QueryHandlerNotFound,
    PaginationParams,
    GetDocumentById,
    ListDocuments,
    CountDocuments,
    GetDocumentByIdHandler,
    ListDocumentsHandler,
    CountDocumentsHandler,
    GetFeedbackById,
    GetFeedbackByDocument,
    GetPendingFeedback,
    CountFeedbackByDocument,
    GetFeedbackByIdHandler,
    GetFeedbackByDocumentHandler,
    GetPendingFeedbackHandler,
    CountFeedbackByDocumentHandler,
    GetPolicyRepositoryById,
    ListPolicyRepositories,
    GetPoliciesByRepository,
    CountPolicyRepositories,
    GetPolicyRepositoryByIdHandler,
    ListPolicyRepositoriesHandler,
    GetPoliciesByRepositoryHandler,
    CountPolicyRepositoriesHandler,
    GetAuditLogById,
    GetAuditLogByDocument,
    GetRecentAuditLogs,
    CountAuditLogsByDocument,
    GetAuditLogByIdHandler,
    GetAuditLogByDocumentHandler,
    GetRecentAuditLogsHandler,
    CountAuditLogsByDocumentHandler,
)
from src.infrastructure.queries.document_queries import DocumentView, DocumentDetailView
from src.infrastructure.queries.feedback_queries import FeedbackView
from src.infrastructure.queries.policy_queries import PolicyRepositoryView, PolicyView
from src.infrastructure.queries.audit_queries import AuditLogView


class MockDocumentQueries:
    def __init__(self):
        self._documents: dict = {}
        self._document_list: List[DocumentView] = []

    def add_document(self, doc: DocumentDetailView):
        self._documents[doc.id] = doc
        self._document_list.append(DocumentView(
            id=doc.id,
            title=doc.title,
            description=doc.description,
            status=doc.status,
            version=doc.version,
            original_format=doc.original_format,
            original_filename=None,
            policy_repository_id=doc.policy_repository_id,
            compliance_status=doc.compliance_status,
            created_at=doc.created_at,
            updated_at=doc.updated_at,
        ))

    async def get_by_id(self, document_id: UUID) -> Optional[DocumentDetailView]:
        return self._documents.get(document_id)

    async def list_all(
        self,
        status: Optional[str] = None,
        policy_repository_id: Optional[UUID] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[DocumentView]:
        result = self._document_list
        if status:
            result = [d for d in result if d.status == status]
        if policy_repository_id:
            result = [d for d in result if d.policy_repository_id == policy_repository_id]
        return result[offset:offset + limit]

    async def count(
        self,
        status: Optional[str] = None,
        policy_repository_id: Optional[UUID] = None
    ) -> int:
        result = self._document_list
        if status:
            result = [d for d in result if d.status == status]
        if policy_repository_id:
            result = [d for d in result if d.policy_repository_id == policy_repository_id]
        return len(result)


class MockFeedbackQueries:
    def __init__(self):
        self._feedbacks: dict = {}
        self._by_document: dict = {}

    def add_feedback(self, feedback: FeedbackView):
        self._feedbacks[feedback.id] = feedback
        if feedback.document_id not in self._by_document:
            self._by_document[feedback.document_id] = []
        self._by_document[feedback.document_id].append(feedback)

    async def get_by_id(self, feedback_id: UUID) -> Optional[FeedbackView]:
        return self._feedbacks.get(feedback_id)

    async def get_by_document(
        self,
        document_id: UUID,
        status: Optional[str] = None
    ) -> List[FeedbackView]:
        result = self._by_document.get(document_id, [])
        if status:
            result = [f for f in result if f.status == status]
        return result

    async def get_pending_by_document(self, document_id: UUID) -> List[FeedbackView]:
        return await self.get_by_document(document_id, status="pending")

    async def count_by_document(
        self,
        document_id: UUID,
        status: Optional[str] = None
    ) -> int:
        return len(await self.get_by_document(document_id, status))


class MockPolicyQueries:
    def __init__(self):
        self._repositories: dict = {}
        self._policies: dict = {}

    def add_repository(self, repo: PolicyRepositoryView):
        self._repositories[repo.id] = repo

    def add_policy(self, policy: PolicyView):
        self._policies[policy.id] = policy

    async def get_repository_by_id(self, repository_id: UUID) -> Optional[PolicyRepositoryView]:
        return self._repositories.get(repository_id)

    async def list_repositories(
        self,
        limit: int = 50,
        offset: int = 0
    ) -> List[PolicyRepositoryView]:
        repos = list(self._repositories.values())
        return repos[offset:offset + limit]

    async def get_policies_by_repository(
        self,
        repository_id: UUID,
        requirement_type: Optional[str] = None
    ) -> List[PolicyView]:
        result = [p for p in self._policies.values() if p.repository_id == repository_id]
        if requirement_type:
            result = [p for p in result if p.requirement_type == requirement_type]
        return result

    async def count_repositories(self) -> int:
        return len(self._repositories)


class MockAuditQueries:
    def __init__(self):
        self._logs: dict = {}
        self._by_document: dict = {}

    def add_log(self, log: AuditLogView):
        self._logs[log.id] = log
        if log.document_id:
            if log.document_id not in self._by_document:
                self._by_document[log.document_id] = []
            self._by_document[log.document_id].append(log)

    async def get_by_id(self, audit_id: UUID) -> Optional[AuditLogView]:
        return self._logs.get(audit_id)

    async def get_by_document(
        self,
        document_id: UUID,
        limit: int = 100,
        offset: int = 0
    ) -> List[AuditLogView]:
        logs = self._by_document.get(document_id, [])
        return logs[offset:offset + limit]

    async def get_recent(
        self,
        limit: int = 50,
        offset: int = 0,
        event_type: Optional[str] = None
    ) -> List[AuditLogView]:
        result = list(self._logs.values())
        if event_type:
            result = [l for l in result if l.event_type == event_type]
        return result[offset:offset + limit]

    async def count_by_document(self, document_id: UUID) -> int:
        return len(self._by_document.get(document_id, []))


class TestQueryDispatcher:
    @pytest.mark.asyncio
    async def test_dispatch_registered_handler(self):
        dispatcher = QueryDispatcher()
        mock_queries = MockDocumentQueries()
        handler = GetDocumentByIdHandler(mock_queries)
        dispatcher.register(GetDocumentById, handler)

        query = GetDocumentById(document_id=uuid4())
        result = await dispatcher.dispatch(query)

        assert result is None

    @pytest.mark.asyncio
    async def test_dispatch_unregistered_handler_raises(self):
        dispatcher = QueryDispatcher()

        query = GetDocumentById(document_id=uuid4())

        with pytest.raises(QueryHandlerNotFound):
            await dispatcher.dispatch(query)


class TestDocumentQueryHandlers:
    @pytest.fixture
    def mock_queries(self):
        return MockDocumentQueries()

    @pytest.fixture
    def sample_document(self):
        now = datetime.utcnow()
        return DocumentDetailView(
            id=uuid4(),
            title="Test Document",
            description="Test description",
            status="converted",
            version=1,
            original_format="pdf",
            markdown_content="# Test",
            sections=[],
            metadata={},
            policy_repository_id=None,
            compliance_status=None,
            created_at=now,
            updated_at=now
        )

    @pytest.mark.asyncio
    async def test_get_document_by_id_success(self, mock_queries, sample_document):
        mock_queries.add_document(sample_document)
        handler = GetDocumentByIdHandler(mock_queries)

        query = GetDocumentById(document_id=sample_document.id)
        result = await handler.handle(query)

        assert result is not None
        assert result.id == sample_document.id
        assert result.title == "Test Document"

    @pytest.mark.asyncio
    async def test_get_document_by_id_not_found(self, mock_queries):
        handler = GetDocumentByIdHandler(mock_queries)

        query = GetDocumentById(document_id=uuid4())
        result = await handler.handle(query)

        assert result is None

    @pytest.mark.asyncio
    async def test_list_documents(self, mock_queries, sample_document):
        mock_queries.add_document(sample_document)
        handler = ListDocumentsHandler(mock_queries)

        query = ListDocuments()
        result = await handler.handle(query)

        assert len(result) == 1
        assert result[0].id == sample_document.id

    @pytest.mark.asyncio
    async def test_count_documents(self, mock_queries, sample_document):
        mock_queries.add_document(sample_document)
        handler = CountDocumentsHandler(mock_queries)

        query = CountDocuments()
        result = await handler.handle(query)

        assert result == 1


class TestFeedbackQueryHandlers:
    @pytest.fixture
    def mock_queries(self):
        return MockFeedbackQueries()

    @pytest.fixture
    def sample_feedback(self):
        now = datetime.utcnow()
        return FeedbackView(
            id=uuid4(),
            document_id=uuid4(),
            section_id="section-1",
            status="pending",
            category="compliance",
            severity="high",
            original_text="Original text",
            suggestion="Suggested change",
            explanation="Why this matters",
            confidence_score=0.9,
            policy_reference="POL-001",
            rejection_reason=None,
            processed_at=None,
            created_at=now
        )

    @pytest.mark.asyncio
    async def test_get_feedback_by_id_success(self, mock_queries, sample_feedback):
        mock_queries.add_feedback(sample_feedback)
        handler = GetFeedbackByIdHandler(mock_queries)

        query = GetFeedbackById(feedback_id=sample_feedback.id)
        result = await handler.handle(query)

        assert result is not None
        assert result.id == sample_feedback.id

    @pytest.mark.asyncio
    async def test_get_feedback_by_document(self, mock_queries, sample_feedback):
        mock_queries.add_feedback(sample_feedback)
        handler = GetFeedbackByDocumentHandler(mock_queries)

        query = GetFeedbackByDocument(document_id=sample_feedback.document_id)
        result = await handler.handle(query)

        assert len(result) == 1
        assert result[0].id == sample_feedback.id

    @pytest.mark.asyncio
    async def test_get_pending_feedback(self, mock_queries, sample_feedback):
        mock_queries.add_feedback(sample_feedback)
        handler = GetPendingFeedbackHandler(mock_queries)

        query = GetPendingFeedback(document_id=sample_feedback.document_id)
        result = await handler.handle(query)

        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_count_feedback_by_document(self, mock_queries, sample_feedback):
        mock_queries.add_feedback(sample_feedback)
        handler = CountFeedbackByDocumentHandler(mock_queries)

        query = CountFeedbackByDocument(document_id=sample_feedback.document_id)
        result = await handler.handle(query)

        assert result == 1


class TestPolicyQueryHandlers:
    @pytest.fixture
    def mock_queries(self):
        return MockPolicyQueries()

    @pytest.fixture
    def sample_repository(self):
        now = datetime.utcnow()
        return PolicyRepositoryView(
            id=uuid4(),
            name="SEC Compliance",
            description="SEC regulatory policies",
            policy_count=5,
            document_count=10,
            created_at=now,
            updated_at=now
        )

    @pytest.fixture
    def sample_policy(self, sample_repository):
        now = datetime.utcnow()
        return PolicyView(
            id=uuid4(),
            repository_id=sample_repository.id,
            name="Risk Disclosure",
            description="Mandatory risk disclosure",
            requirement_type="MUST",
            created_at=now,
            updated_at=now
        )

    @pytest.mark.asyncio
    async def test_get_policy_repository_by_id(self, mock_queries, sample_repository):
        mock_queries.add_repository(sample_repository)
        handler = GetPolicyRepositoryByIdHandler(mock_queries)

        query = GetPolicyRepositoryById(repository_id=sample_repository.id)
        result = await handler.handle(query)

        assert result is not None
        assert result.name == "SEC Compliance"

    @pytest.mark.asyncio
    async def test_list_policy_repositories(self, mock_queries, sample_repository):
        mock_queries.add_repository(sample_repository)
        handler = ListPolicyRepositoriesHandler(mock_queries)

        query = ListPolicyRepositories()
        result = await handler.handle(query)

        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_get_policies_by_repository(self, mock_queries, sample_repository, sample_policy):
        mock_queries.add_repository(sample_repository)
        mock_queries.add_policy(sample_policy)
        handler = GetPoliciesByRepositoryHandler(mock_queries)

        query = GetPoliciesByRepository(repository_id=sample_repository.id)
        result = await handler.handle(query)

        assert len(result) == 1
        assert result[0].name == "Risk Disclosure"

    @pytest.mark.asyncio
    async def test_count_policy_repositories(self, mock_queries, sample_repository):
        mock_queries.add_repository(sample_repository)
        handler = CountPolicyRepositoriesHandler(mock_queries)

        query = CountPolicyRepositories()
        result = await handler.handle(query)

        assert result == 1


class TestAuditQueryHandlers:
    @pytest.fixture
    def mock_queries(self):
        return MockAuditQueries()

    @pytest.fixture
    def sample_audit_log(self):
        now = datetime.utcnow()
        return AuditLogView(
            id=uuid4(),
            event_type="DocumentUploaded",
            aggregate_id=uuid4(),
            aggregate_type="Document",
            document_id=uuid4(),
            user_id="user@example.com",
            details={"filename": "test.pdf"},
            timestamp=now
        )

    @pytest.mark.asyncio
    async def test_get_audit_log_by_id(self, mock_queries, sample_audit_log):
        mock_queries.add_log(sample_audit_log)
        handler = GetAuditLogByIdHandler(mock_queries)

        query = GetAuditLogById(audit_id=sample_audit_log.id)
        result = await handler.handle(query)

        assert result is not None
        assert result.event_type == "DocumentUploaded"

    @pytest.mark.asyncio
    async def test_get_audit_log_by_document(self, mock_queries, sample_audit_log):
        mock_queries.add_log(sample_audit_log)
        handler = GetAuditLogByDocumentHandler(mock_queries)

        query = GetAuditLogByDocument(document_id=sample_audit_log.document_id)
        result = await handler.handle(query)

        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_get_recent_audit_logs(self, mock_queries, sample_audit_log):
        mock_queries.add_log(sample_audit_log)
        handler = GetRecentAuditLogsHandler(mock_queries)

        query = GetRecentAuditLogs()
        result = await handler.handle(query)

        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_count_audit_logs_by_document(self, mock_queries, sample_audit_log):
        mock_queries.add_log(sample_audit_log)
        handler = CountAuditLogsByDocumentHandler(mock_queries)

        query = CountAuditLogsByDocument(document_id=sample_audit_log.document_id)
        result = await handler.handle(query)

        assert result == 1
