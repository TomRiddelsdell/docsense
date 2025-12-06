import pytest
from uuid import uuid4

from src.application.commands.analysis_handlers import (
    StartAnalysisHandler,
    CancelAnalysisHandler,
)
from src.application.commands.feedback_handlers import (
    AcceptChangeHandler,
    RejectChangeHandler,
    ModifyChangeHandler,
)
from src.domain.commands import (
    StartAnalysis,
    CancelAnalysis,
    AcceptChange,
    RejectChange,
    ModifyChange,
)
from src.domain.aggregates.document import Document
from src.domain.aggregates.feedback_session import FeedbackSession
from src.domain.aggregates.policy_repository import PolicyRepository
from src.domain.exceptions.document_exceptions import DocumentNotFound
from src.domain.exceptions.policy_exceptions import PolicyRepositoryNotFound
from src.domain.exceptions.feedback_exceptions import FeedbackSessionNotFound
from tests.fixtures.mocks import (
    MockDocumentRepository,
    MockFeedbackRepository,
    MockPolicyRepository,
    MockEventPublisher,
)


class TestStartAnalysisHandler:
    @pytest.fixture
    def mock_doc_repo(self):
        return MockDocumentRepository()

    @pytest.fixture
    def mock_policy_repo(self):
        return MockPolicyRepository()

    @pytest.fixture
    def mock_publisher(self):
        return MockEventPublisher()

    @pytest.fixture
    def handler(self, mock_doc_repo, mock_policy_repo, mock_publisher):
        return StartAnalysisHandler(
            document_repository=mock_doc_repo,
            policy_repository=mock_policy_repo,
            event_publisher=mock_publisher
        )

    @pytest.fixture
    def converted_document(self):
        doc_id = uuid4()
        doc = Document.upload(
            document_id=doc_id,
            filename="test.pdf",
            content=b"content",
            original_format="pdf",
            uploaded_by="user@example.com"
        )
        doc.convert(
            markdown_content="# Test",
            sections=[],
            metadata={}
        )
        doc.clear_pending_events()
        return doc

    @pytest.fixture
    def policy_repository(self):
        repo_id = uuid4()
        repo = PolicyRepository.create(
            repository_id=repo_id,
            name="Test Policy",
            description="Test",
            created_by="user@example.com"
        )
        repo.clear_pending_events()
        return repo

    @pytest.mark.asyncio
    async def test_start_analysis_success(
        self, handler, mock_doc_repo, mock_policy_repo, converted_document, policy_repository
    ):
        mock_doc_repo.add(converted_document)
        mock_policy_repo.add(policy_repository)

        command = StartAnalysis(
            document_id=converted_document.id,
            policy_repository_id=policy_repository.id,
            initiated_by="user@example.com",
            ai_model="gemini-pro"
        )

        result = await handler.handle(command)

        assert result == converted_document.id
        assert len(mock_doc_repo._save_calls) == 1

    @pytest.mark.asyncio
    async def test_start_analysis_document_not_found(self, handler):
        command = StartAnalysis(
            document_id=uuid4(),
            policy_repository_id=uuid4(),
            initiated_by="user@example.com"
        )

        with pytest.raises(DocumentNotFound):
            await handler.handle(command)

    @pytest.mark.asyncio
    async def test_start_analysis_policy_not_found(
        self, handler, mock_doc_repo, converted_document
    ):
        mock_doc_repo.add(converted_document)

        command = StartAnalysis(
            document_id=converted_document.id,
            policy_repository_id=uuid4(),
            initiated_by="user@example.com"
        )

        with pytest.raises(PolicyRepositoryNotFound):
            await handler.handle(command)


class TestCancelAnalysisHandler:
    @pytest.fixture
    def mock_doc_repo(self):
        return MockDocumentRepository()

    @pytest.fixture
    def mock_publisher(self):
        return MockEventPublisher()

    @pytest.fixture
    def handler(self, mock_doc_repo, mock_publisher):
        return CancelAnalysisHandler(
            document_repository=mock_doc_repo,
            event_publisher=mock_publisher
        )

    @pytest.mark.asyncio
    async def test_cancel_analysis_document_not_found(self, handler):
        command = CancelAnalysis(
            document_id=uuid4(),
            cancelled_by="user@example.com",
            reason="No longer needed"
        )

        with pytest.raises(DocumentNotFound):
            await handler.handle(command)


class TestAcceptChangeHandler:
    @pytest.fixture
    def mock_feedback_repo(self):
        return MockFeedbackRepository()

    @pytest.fixture
    def mock_publisher(self):
        return MockEventPublisher()

    @pytest.fixture
    def handler(self, mock_feedback_repo, mock_publisher):
        return AcceptChangeHandler(
            feedback_repository=mock_feedback_repo,
            event_publisher=mock_publisher
        )

    @pytest.fixture
    def feedback_session_with_item(self):
        session_id = uuid4()
        doc_id = uuid4()
        feedback_id = uuid4()
        session = FeedbackSession.create_for_document(
            session_id=session_id,
            document_id=doc_id
        )
        session.add_feedback(
            feedback_id=feedback_id,
            issue_description="Test issue",
            suggested_change="Test change",
            confidence_score=0.9,
            policy_reference="POL-001",
            section_reference="Section 1"
        )
        session.clear_pending_events()
        return session, doc_id, feedback_id

    @pytest.mark.asyncio
    async def test_accept_change_success(
        self, handler, mock_feedback_repo, feedback_session_with_item
    ):
        session, doc_id, feedback_id = feedback_session_with_item
        mock_feedback_repo.add(session)

        command = AcceptChange(
            document_id=session.id,
            feedback_id=feedback_id,
            accepted_by="user@example.com"
        )

        result = await handler.handle(command)

        assert result is True
        assert len(mock_feedback_repo._save_calls) == 1

    @pytest.mark.asyncio
    async def test_accept_change_session_not_found(self, handler):
        command = AcceptChange(
            document_id=uuid4(),
            feedback_id=uuid4(),
            accepted_by="user@example.com"
        )

        with pytest.raises(FeedbackSessionNotFound):
            await handler.handle(command)


class TestRejectChangeHandler:
    @pytest.fixture
    def mock_feedback_repo(self):
        return MockFeedbackRepository()

    @pytest.fixture
    def mock_publisher(self):
        return MockEventPublisher()

    @pytest.fixture
    def handler(self, mock_feedback_repo, mock_publisher):
        return RejectChangeHandler(
            feedback_repository=mock_feedback_repo,
            event_publisher=mock_publisher
        )

    @pytest.fixture
    def feedback_session_with_item(self):
        session_id = uuid4()
        doc_id = uuid4()
        feedback_id = uuid4()
        session = FeedbackSession.create_for_document(
            session_id=session_id,
            document_id=doc_id
        )
        session.add_feedback(
            feedback_id=feedback_id,
            issue_description="Test issue",
            suggested_change="Test change",
            confidence_score=0.9,
            policy_reference="POL-001",
            section_reference="Section 1"
        )
        session.clear_pending_events()
        return session, doc_id, feedback_id

    @pytest.mark.asyncio
    async def test_reject_change_success(
        self, handler, mock_feedback_repo, feedback_session_with_item
    ):
        session, doc_id, feedback_id = feedback_session_with_item
        mock_feedback_repo.add(session)

        command = RejectChange(
            document_id=session.id,
            feedback_id=feedback_id,
            rejected_by="user@example.com",
            reason="Not applicable"
        )

        result = await handler.handle(command)

        assert result is True


class TestModifyChangeHandler:
    @pytest.fixture
    def mock_feedback_repo(self):
        return MockFeedbackRepository()

    @pytest.fixture
    def mock_publisher(self):
        return MockEventPublisher()

    @pytest.fixture
    def handler(self, mock_feedback_repo, mock_publisher):
        return ModifyChangeHandler(
            feedback_repository=mock_feedback_repo,
            event_publisher=mock_publisher
        )

    @pytest.fixture
    def feedback_session_with_item(self):
        session_id = uuid4()
        doc_id = uuid4()
        feedback_id = uuid4()
        session = FeedbackSession.create_for_document(
            session_id=session_id,
            document_id=doc_id
        )
        session.add_feedback(
            feedback_id=feedback_id,
            issue_description="Test issue",
            suggested_change="Test change",
            confidence_score=0.9,
            policy_reference="POL-001",
            section_reference="Section 1"
        )
        session.clear_pending_events()
        return session, doc_id, feedback_id

    @pytest.mark.asyncio
    async def test_modify_change_success(
        self, handler, mock_feedback_repo, feedback_session_with_item
    ):
        session, doc_id, feedback_id = feedback_session_with_item
        mock_feedback_repo.add(session)

        command = ModifyChange(
            document_id=session.id,
            feedback_id=feedback_id,
            modified_by="user@example.com",
            modified_content="Modified content here"
        )

        result = await handler.handle(command)

        assert result is True
