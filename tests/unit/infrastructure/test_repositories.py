import pytest
from uuid import uuid4
from datetime import datetime, timezone

from src.infrastructure.persistence.event_store import InMemoryEventStore
from src.infrastructure.persistence.snapshot_store import InMemorySnapshotStore
from src.infrastructure.repositories.document_repository import DocumentRepository
from src.infrastructure.repositories.feedback_repository import FeedbackSessionRepository
from src.infrastructure.repositories.policy_repository import PolicyRepositoryRepository
from src.domain.aggregates.document import Document
from src.domain.aggregates.feedback_session import FeedbackSession
from src.domain.aggregates.policy_repository import PolicyRepository


class TestDocumentRepository:
    @pytest.fixture
    def event_store(self):
        return InMemoryEventStore()

    @pytest.fixture
    def snapshot_store(self):
        return InMemorySnapshotStore()

    @pytest.fixture
    def repository(self, event_store, snapshot_store):
        return DocumentRepository(event_store, snapshot_store, snapshot_threshold=5)

    @pytest.mark.asyncio
    async def test_save_and_get_document(self, repository):
        doc_id = uuid4()
        document = Document.upload(
            document_id=doc_id,
            filename="test.pdf",
            content=b"test content",
            original_format="pdf",
            uploaded_by="user@example.com"
        )
        
        await repository.save(document)
        
        retrieved = await repository.get(doc_id)
        
        assert retrieved is not None
        assert retrieved.id == doc_id
        assert retrieved.filename == "test.pdf"

    @pytest.mark.asyncio
    async def test_get_returns_none_for_unknown_document(self, repository):
        result = await repository.get(uuid4())
        assert result is None

    @pytest.mark.asyncio
    async def test_exists_returns_true_for_existing_document(self, repository):
        doc_id = uuid4()
        document = Document.upload(
            document_id=doc_id,
            filename="test.pdf",
            content=b"content",
            original_format="pdf",
            uploaded_by="user@example.com"
        )
        await repository.save(document)
        
        exists = await repository.exists(doc_id)
        assert exists is True

    @pytest.mark.asyncio
    async def test_exists_returns_false_for_unknown_document(self, repository):
        exists = await repository.exists(uuid4())
        assert exists is False

    @pytest.mark.asyncio
    async def test_save_multiple_events(self, repository):
        doc_id = uuid4()
        document = Document.upload(
            document_id=doc_id,
            filename="test.pdf",
            content=b"content",
            original_format="pdf",
            uploaded_by="user@example.com"
        )
        document.convert(
            markdown_content="# Test",
            sections=[],
            metadata={},
            conversion_warnings=[]
        )
        
        await repository.save(document)
        
        retrieved = await repository.get(doc_id)
        assert retrieved is not None
        assert retrieved.markdown_content == "# Test"

    @pytest.mark.asyncio
    async def test_aggregate_type_name(self, repository):
        assert repository._aggregate_type_name() == "Document"

    @pytest.mark.asyncio
    async def test_serialize_and_deserialize_aggregate(self, repository):
        doc_id = uuid4()
        document = Document.upload(
            document_id=doc_id,
            filename="test.pdf",
            content=b"content",
            original_format="pdf",
            uploaded_by="user@example.com"
        )
        
        state = repository._serialize_aggregate(document)
        
        assert state["id"] == str(doc_id)
        assert state["filename"] == "test.pdf"
        
        restored = repository._deserialize_aggregate(state)
        
        assert restored.id == doc_id
        assert restored.filename == "test.pdf"


class TestFeedbackSessionRepository:
    @pytest.fixture
    def event_store(self):
        return InMemoryEventStore()

    @pytest.fixture
    def repository(self, event_store):
        return FeedbackSessionRepository(event_store)

    @pytest.mark.asyncio
    async def test_save_and_get_feedback_session(self, repository):
        session_id = uuid4()
        document_id = uuid4()
        session = FeedbackSession.create_for_document(
            session_id=session_id,
            document_id=document_id
        )
        
        await repository.save(session)
        
        retrieved = await repository.get(session_id)
        
        assert retrieved is not None
        assert retrieved.id == session_id
        assert retrieved.document_id == document_id

    @pytest.mark.asyncio
    async def test_aggregate_type_name(self, repository):
        assert repository._aggregate_type_name() == "FeedbackSession"


class TestPolicyRepositoryRepository:
    @pytest.fixture
    def event_store(self):
        return InMemoryEventStore()

    @pytest.fixture
    def repository(self, event_store):
        return PolicyRepositoryRepository(event_store)

    @pytest.mark.asyncio
    async def test_save_and_get_policy_repository(self, repository):
        repo_id = uuid4()
        policy_repo = PolicyRepository.create(
            repository_id=repo_id,
            name="SEC Policies",
            description="SEC compliance policies",
            created_by="admin@example.com"
        )
        
        await repository.save(policy_repo)
        
        retrieved = await repository.get(repo_id)
        
        assert retrieved is not None
        assert retrieved.id == repo_id
        assert retrieved.name == "SEC Policies"

    @pytest.mark.asyncio
    async def test_save_with_policies(self, repository):
        repo_id = uuid4()
        policy_repo = PolicyRepository.create(
            repository_id=repo_id,
            name="SEC Policies",
            description="SEC compliance policies",
            created_by="admin@example.com"
        )
        policy_repo.add_policy(
            policy_id=uuid4(),
            policy_name="Risk Disclosure",
            policy_content="All risks must be disclosed",
            requirement_type="MUST",
            added_by="admin@example.com"
        )
        
        await repository.save(policy_repo)
        
        retrieved = await repository.get(repo_id)
        assert len(retrieved.policies) == 1

    @pytest.mark.asyncio
    async def test_aggregate_type_name(self, repository):
        assert repository._aggregate_type_name() == "PolicyRepository"
