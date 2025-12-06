import pytest
from uuid import uuid4

from src.application.commands.policy_handlers import (
    CreatePolicyRepositoryHandler,
    AddPolicyHandler,
    AssignDocumentToPolicyHandler,
)
from src.domain.commands import (
    CreatePolicyRepository,
    AddPolicy,
    AssignDocumentToPolicy,
)
from src.domain.aggregates.document import Document
from src.domain.aggregates.policy_repository import PolicyRepository
from src.domain.exceptions.policy_exceptions import (
    PolicyRepositoryNotFound,
    PolicyAlreadyExists,
)
from src.domain.exceptions.document_exceptions import DocumentNotFound
from tests.fixtures.mocks import (
    MockDocumentRepository,
    MockPolicyRepository,
    MockEventPublisher,
)


class TestCreatePolicyRepositoryHandler:
    @pytest.fixture
    def mock_policy_repo(self):
        return MockPolicyRepository()

    @pytest.fixture
    def mock_publisher(self):
        return MockEventPublisher()

    @pytest.fixture
    def handler(self, mock_policy_repo, mock_publisher):
        return CreatePolicyRepositoryHandler(
            policy_repository=mock_policy_repo,
            event_publisher=mock_publisher
        )

    @pytest.mark.asyncio
    async def test_create_policy_repository_success(
        self, handler, mock_policy_repo
    ):
        command = CreatePolicyRepository(
            name="SEC Compliance",
            description="SEC regulatory compliance policies",
            created_by="admin@example.com"
        )

        result = await handler.handle(command)

        assert result is not None
        assert len(mock_policy_repo._save_calls) == 1
        saved_repo = mock_policy_repo._save_calls[0]
        assert saved_repo.name == "SEC Compliance"
        assert saved_repo.description == "SEC regulatory compliance policies"


class TestAddPolicyHandler:
    @pytest.fixture
    def mock_policy_repo(self):
        return MockPolicyRepository()

    @pytest.fixture
    def mock_publisher(self):
        return MockEventPublisher()

    @pytest.fixture
    def handler(self, mock_policy_repo, mock_publisher):
        return AddPolicyHandler(
            policy_repository=mock_policy_repo,
            event_publisher=mock_publisher
        )

    @pytest.fixture
    def existing_policy_repository(self):
        repo_id = uuid4()
        repo = PolicyRepository.create(
            repository_id=repo_id,
            name="Test Policies",
            description="Test policy repository",
            created_by="admin@example.com"
        )
        repo.clear_pending_events()
        return repo

    @pytest.mark.asyncio
    async def test_add_policy_success(
        self, handler, mock_policy_repo, existing_policy_repository
    ):
        mock_policy_repo.add(existing_policy_repository)

        command = AddPolicy(
            repository_id=existing_policy_repository.id,
            policy_name="Risk Disclosure",
            policy_content="All trading algorithms must include risk disclosure",
            requirement_type="MUST",
            added_by="admin@example.com"
        )

        result = await handler.handle(command)

        assert result is not None
        assert len(mock_policy_repo._save_calls) == 1

    @pytest.mark.asyncio
    async def test_add_policy_repository_not_found(self, handler):
        command = AddPolicy(
            repository_id=uuid4(),
            policy_name="Risk Disclosure",
            policy_content="Content",
            requirement_type="MUST",
            added_by="admin@example.com"
        )

        with pytest.raises(PolicyRepositoryNotFound):
            await handler.handle(command)

    @pytest.mark.asyncio
    async def test_add_duplicate_policy_name_fails(
        self, handler, mock_policy_repo, existing_policy_repository
    ):
        existing_policy_repository.add_policy(
            policy_id=uuid4(),
            policy_name="Risk Disclosure",
            policy_content="Original content",
            requirement_type="MUST",
            added_by="admin@example.com"
        )
        existing_policy_repository.clear_pending_events()
        mock_policy_repo.add(existing_policy_repository)

        command = AddPolicy(
            repository_id=existing_policy_repository.id,
            policy_name="Risk Disclosure",
            policy_content="Different content",
            requirement_type="SHOULD",
            added_by="admin@example.com"
        )

        with pytest.raises(PolicyAlreadyExists):
            await handler.handle(command)


class TestAssignDocumentToPolicyHandler:
    @pytest.fixture
    def mock_policy_repo(self):
        return MockPolicyRepository()

    @pytest.fixture
    def mock_doc_repo(self):
        return MockDocumentRepository()

    @pytest.fixture
    def mock_publisher(self):
        return MockEventPublisher()

    @pytest.fixture
    def handler(self, mock_policy_repo, mock_doc_repo, mock_publisher):
        return AssignDocumentToPolicyHandler(
            policy_repository=mock_policy_repo,
            document_repository=mock_doc_repo,
            event_publisher=mock_publisher
        )

    @pytest.fixture
    def existing_policy_repository(self):
        repo_id = uuid4()
        repo = PolicyRepository.create(
            repository_id=repo_id,
            name="Test Policies",
            description="Test policy repository",
            created_by="admin@example.com"
        )
        repo.clear_pending_events()
        return repo

    @pytest.fixture
    def existing_document(self):
        doc_id = uuid4()
        doc = Document.upload(
            document_id=doc_id,
            filename="trading_algo.pdf",
            content=b"content",
            original_format="pdf",
            uploaded_by="user@example.com"
        )
        doc.clear_pending_events()
        return doc

    @pytest.mark.asyncio
    async def test_assign_document_success(
        self, handler, mock_policy_repo, mock_doc_repo,
        existing_policy_repository, existing_document
    ):
        mock_policy_repo.add(existing_policy_repository)
        mock_doc_repo.add(existing_document)

        command = AssignDocumentToPolicy(
            repository_id=existing_policy_repository.id,
            document_id=existing_document.id,
            assigned_by="admin@example.com"
        )

        result = await handler.handle(command)

        assert result is True
        assert len(mock_policy_repo._save_calls) == 1

    @pytest.mark.asyncio
    async def test_assign_document_repository_not_found(
        self, handler, mock_doc_repo, existing_document
    ):
        mock_doc_repo.add(existing_document)

        command = AssignDocumentToPolicy(
            repository_id=uuid4(),
            document_id=existing_document.id,
            assigned_by="admin@example.com"
        )

        with pytest.raises(PolicyRepositoryNotFound):
            await handler.handle(command)

    @pytest.mark.asyncio
    async def test_assign_document_not_found(
        self, handler, mock_policy_repo, existing_policy_repository
    ):
        mock_policy_repo.add(existing_policy_repository)

        command = AssignDocumentToPolicy(
            repository_id=existing_policy_repository.id,
            document_id=uuid4(),
            assigned_by="admin@example.com"
        )

        with pytest.raises(DocumentNotFound):
            await handler.handle(command)
