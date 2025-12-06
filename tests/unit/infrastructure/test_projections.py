import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
from datetime import datetime, timezone

from src.domain.events import (
    DocumentUploaded,
    DocumentConverted,
    AnalysisStarted,
    AnalysisCompleted,
    FeedbackGenerated,
    ChangeAccepted,
    PolicyRepositoryCreated,
    PolicyAdded,
)
from src.infrastructure.projections.base import Projection
from src.infrastructure.projections.document_projector import DocumentProjection
from src.infrastructure.projections.feedback_projector import FeedbackProjection
from src.infrastructure.projections.policy_projector import PolicyProjection


class MockProjection(Projection):
    def __init__(self):
        self.handled_events = []

    def handles(self):
        return [DocumentUploaded, DocumentConverted]

    async def handle(self, event):
        self.handled_events.append(event)


class TestBaseProjection:
    def test_can_handle_returns_true_for_handled_events(self):
        projection = MockProjection()
        
        event = DocumentUploaded(
            event_id=uuid4(),
            aggregate_id=uuid4(),
            occurred_at=datetime.now(timezone.utc),
            version=1,
            filename="test.pdf",
            original_format="pdf",
            file_size_bytes=1024,
            uploaded_by="user@example.com"
        )
        
        assert projection.can_handle(event) is True

    def test_can_handle_returns_false_for_unhandled_events(self):
        projection = MockProjection()
        
        event = AnalysisStarted(
            event_id=uuid4(),
            aggregate_id=uuid4(),
            occurred_at=datetime.now(timezone.utc),
            version=1,
            policy_repository_id=uuid4(),
            ai_model="gemini",
            initiated_by="user"
        )
        
        assert projection.can_handle(event) is False

    @pytest.mark.asyncio
    async def test_handle_stores_event(self):
        projection = MockProjection()
        
        event = DocumentUploaded(
            event_id=uuid4(),
            aggregate_id=uuid4(),
            occurred_at=datetime.now(timezone.utc),
            version=1,
            filename="test.pdf",
            original_format="pdf",
            file_size_bytes=1024,
            uploaded_by="user@example.com"
        )
        
        await projection.handle(event)
        
        assert len(projection.handled_events) == 1
        assert projection.handled_events[0] == event


class TestDocumentProjection:
    @pytest.fixture
    def mock_pool(self):
        pool = MagicMock()
        conn = AsyncMock()
        pool.acquire.return_value.__aenter__ = AsyncMock(return_value=conn)
        pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)
        return pool, conn

    def test_handles_returns_document_events(self):
        projection = DocumentProjection(MagicMock())
        
        handled = projection.handles()
        
        assert DocumentUploaded in handled
        assert DocumentConverted in handled
        assert AnalysisStarted in handled
        assert AnalysisCompleted in handled

    @pytest.mark.asyncio
    async def test_handle_document_uploaded(self, mock_pool):
        pool, conn = mock_pool
        projection = DocumentProjection(pool)
        
        event = DocumentUploaded(
            event_id=uuid4(),
            aggregate_id=uuid4(),
            occurred_at=datetime.now(timezone.utc),
            version=1,
            filename="test.pdf",
            original_format="pdf",
            file_size_bytes=1024,
            uploaded_by="user@example.com"
        )
        
        await projection.handle(event)
        
        conn.execute.assert_called()


class TestFeedbackProjection:
    @pytest.fixture
    def mock_pool(self):
        pool = MagicMock()
        conn = AsyncMock()
        pool.acquire.return_value.__aenter__ = AsyncMock(return_value=conn)
        pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)
        return pool, conn

    def test_handles_returns_feedback_events(self):
        projection = FeedbackProjection(MagicMock())
        
        handled = projection.handles()
        
        assert FeedbackGenerated in handled
        assert ChangeAccepted in handled

    @pytest.mark.asyncio
    async def test_handle_feedback_generated(self, mock_pool):
        pool, conn = mock_pool
        projection = FeedbackProjection(pool)
        
        event = FeedbackGenerated(
            event_id=uuid4(),
            aggregate_id=uuid4(),
            occurred_at=datetime.now(timezone.utc),
            version=1,
            feedback_id=uuid4(),
            issue_description="Missing stop loss",
            suggested_change="Add stop loss",
            confidence_score=0.9,
            policy_reference="SEC-001",
            section_reference="Risk"
        )
        
        await projection.handle(event)
        
        conn.execute.assert_called()


class TestPolicyProjection:
    @pytest.fixture
    def mock_pool(self):
        pool = MagicMock()
        conn = AsyncMock()
        pool.acquire.return_value.__aenter__ = AsyncMock(return_value=conn)
        pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)
        return pool, conn

    def test_handles_returns_policy_events(self):
        projection = PolicyProjection(MagicMock())
        
        handled = projection.handles()
        
        assert PolicyRepositoryCreated in handled
        assert PolicyAdded in handled

    @pytest.mark.asyncio
    async def test_handle_policy_repository_created(self, mock_pool):
        pool, conn = mock_pool
        projection = PolicyProjection(pool)
        
        event = PolicyRepositoryCreated(
            event_id=uuid4(),
            aggregate_id=uuid4(),
            occurred_at=datetime.now(timezone.utc),
            version=1,
            name="SEC Policies",
            description="SEC compliance policies",
            created_by="admin@example.com"
        )
        
        await projection.handle(event)
        
        conn.execute.assert_called()
