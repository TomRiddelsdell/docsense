"""
Unit tests for ProjectionEventPublisher with retry logic.

Tests the enhanced event publisher including:
- Automatic retry with exponential backoff
- Failure tracking integration
- Success recording
- Isolated projection failures
"""

import pytest
import asyncio
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, call

from src.application.services.event_publisher import ProjectionEventPublisher
from src.infrastructure.projections.base import Projection
from src.infrastructure.projections.failure_tracking import ProjectionFailureTracker
from src.domain.events.document_events import DocumentUploaded


class MockProjection(Projection):
    """Mock projection for testing."""
    
    def __init__(self, name="MockProjection", should_fail=False, fail_count=0):
        self.name = name
        self.should_fail = should_fail
        self.fail_count = fail_count
        self.current_fails = 0
        self.handled_events = []
    
    def handles(self):
        return [DocumentUploaded]
    
    async def handle(self, event):
        if self.should_fail and self.current_fails < self.fail_count:
            self.current_fails += 1
            raise Exception(f"Mock failure #{self.current_fails}")
        self.handled_events.append(event)


@pytest.fixture
def mock_failure_tracker():
    """Create a mock ProjectionFailureTracker."""
    tracker = AsyncMock(spec=ProjectionFailureTracker)
    tracker.record_failure = AsyncMock()
    tracker.record_success = AsyncMock()
    return tracker


@pytest.fixture
def sample_event():
    """Create a sample domain event."""
    event = DocumentUploaded(
        aggregate_id=str(uuid4()),
        filename="test.pdf",
        original_format="pdf",
        file_size=1024,
        uploaded_by="test-user",
        storage_path="/tmp/test.pdf"
    )
    event.event_id = uuid4()
    event.sequence = 1
    return event


class TestSuccessfulProjection:
    """Test successful projection handling."""
    
    @pytest.mark.asyncio
    async def test_successful_projection_no_retry(self, mock_failure_tracker, sample_event):
        """Test that successful projections are executed once without retry."""
        projection = MockProjection()
        publisher = ProjectionEventPublisher(
            projections=[projection],
            failure_tracker=mock_failure_tracker,
            max_retries=3,
            retry_delay_seconds=0
        )
        
        await publisher.publish(sample_event)
        
        # Event should be handled exactly once
        assert len(projection.handled_events) == 1
        assert projection.handled_events[0] == sample_event
        
        # Success should be recorded
        mock_failure_tracker.record_success.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_success_recorded_with_correct_params(self, mock_failure_tracker, sample_event):
        """Test that success is recorded with correct event and projection name."""
        projection = MockProjection(name="TestProjection")
        publisher = ProjectionEventPublisher(
            projections=[projection],
            failure_tracker=mock_failure_tracker,
            max_retries=3,
            retry_delay_seconds=0
        )
        
        await publisher.publish(sample_event)
        
        # Verify record_success called with correct params
        call_args = mock_failure_tracker.record_success.call_args
        assert call_args[0][0] == sample_event
        assert call_args[0][1] == "MockProjection"


class TestTransientFailures:
    """Test handling of transient failures that succeed on retry."""
    
    @pytest.mark.asyncio
    async def test_transient_failure_retries_successfully(self, mock_failure_tracker, sample_event):
        """Test that transient failures are retried and eventually succeed."""
        # Projection fails twice, then succeeds
        projection = MockProjection(should_fail=True, fail_count=2)
        publisher = ProjectionEventPublisher(
            projections=[projection],
            failure_tracker=mock_failure_tracker,
            max_retries=3,
            retry_delay_seconds=0  # No delay for testing
        )
        
        await publisher.publish(sample_event)
        
        # Should succeed after 2 failures
        assert projection.current_fails == 2
        assert len(projection.handled_events) == 1
        
        # Success should be recorded
        mock_failure_tracker.record_success.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_retry_delay_increases_exponentially(self, mock_failure_tracker, sample_event):
        """Test that retry delays follow exponential backoff pattern."""
        projection = MockProjection(should_fail=True, fail_count=2)
        publisher = ProjectionEventPublisher(
            projections=[projection],
            failure_tracker=mock_failure_tracker,
            max_retries=3,
            retry_delay_seconds=1  # Base delay
        )
        
        import time
        start = time.time()
        await publisher.publish(sample_event)
        elapsed = time.time() - start
        
        # Should have delays: 1s (first retry) + 2s (second retry) = 3s minimum
        # With some tolerance for execution time
        assert elapsed >= 2.5  # Allow some tolerance
        assert projection.current_fails == 2


class TestPermanentFailures:
    """Test handling of permanent failures that never succeed."""
    
    @pytest.mark.asyncio
    async def test_permanent_failure_exhausts_retries(self, mock_failure_tracker, sample_event):
        """Test that permanent failures exhaust all retry attempts."""
        # Projection always fails
        projection = MockProjection(should_fail=True, fail_count=999)
        publisher = ProjectionEventPublisher(
            projections=[projection],
            failure_tracker=mock_failure_tracker,
            max_retries=3,
            retry_delay_seconds=0
        )
        
        await publisher.publish(sample_event)
        
        # Should attempt 3 times
        assert projection.current_fails == 3
        assert len(projection.handled_events) == 0
        
        # Failure should be recorded
        mock_failure_tracker.record_failure.assert_called_once()
        
        # Success should NOT be recorded
        mock_failure_tracker.record_success.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_failure_recorded_with_correct_params(self, mock_failure_tracker, sample_event):
        """Test that failure is recorded with correct parameters."""
        projection = MockProjection(name="TestProjection", should_fail=True, fail_count=999)
        publisher = ProjectionEventPublisher(
            projections=[projection],
            failure_tracker=mock_failure_tracker,
            max_retries=2,
            retry_delay_seconds=0
        )
        
        await publisher.publish(sample_event)
        
        # Verify record_failure called with correct params
        call_args = mock_failure_tracker.record_failure.call_args
        assert call_args[0][0] == sample_event
        assert call_args[0][1] == "MockProjection"
        assert isinstance(call_args[0][2], Exception)


class TestIsolatedFailures:
    """Test that projection failures are isolated from each other."""
    
    @pytest.mark.asyncio
    async def test_one_projection_failure_does_not_affect_others(self, mock_failure_tracker, sample_event):
        """Test that one projection's failure doesn't prevent others from executing."""
        good_projection = MockProjection(name="GoodProjection")
        bad_projection = MockProjection(name="BadProjection", should_fail=True, fail_count=999)
        another_good = MockProjection(name="AnotherGood")
        
        publisher = ProjectionEventPublisher(
            projections=[good_projection, bad_projection, another_good],
            failure_tracker=mock_failure_tracker,
            max_retries=2,
            retry_delay_seconds=0
        )
        
        await publisher.publish(sample_event)
        
        # Good projections should succeed
        assert len(good_projection.handled_events) == 1
        assert len(another_good.handled_events) == 1
        
        # Bad projection should fail
        assert len(bad_projection.handled_events) == 0
        assert bad_projection.current_fails == 2
        
        # Should record 2 successes and 1 failure
        assert mock_failure_tracker.record_success.call_count == 2
        assert mock_failure_tracker.record_failure.call_count == 1
    
    @pytest.mark.asyncio
    async def test_multiple_projection_failures_all_tracked(self, mock_failure_tracker, sample_event):
        """Test that multiple projection failures are all tracked independently."""
        failing1 = MockProjection(name="Failing1", should_fail=True, fail_count=999)
        failing2 = MockProjection(name="Failing2", should_fail=True, fail_count=999)
        
        publisher = ProjectionEventPublisher(
            projections=[failing1, failing2],
            failure_tracker=mock_failure_tracker,
            max_retries=1,
            retry_delay_seconds=0
        )
        
        await publisher.publish(sample_event)
        
        # Both should record failures
        assert mock_failure_tracker.record_failure.call_count == 2
        
        # Verify both projection names were recorded
        failure_calls = mock_failure_tracker.record_failure.call_args_list
        projection_names = {call[0][1] for call in failure_calls}
        assert "Failing1" in projection_names
        assert "Failing2" in projection_names


class TestPublishAll:
    """Test batch event publishing."""
    
    @pytest.mark.asyncio
    async def test_publish_all_processes_all_events(self, mock_failure_tracker):
        """Test that publish_all processes all events in sequence."""
        projection = MockProjection()
        publisher = ProjectionEventPublisher(
            projections=[projection],
            failure_tracker=mock_failure_tracker,
            max_retries=3,
            retry_delay_seconds=0
        )
        
        events = [
            DocumentUploaded(
                aggregate_id=str(uuid4()),
                filename=f"test{i}.pdf",
                original_format="pdf",
                file_size=1024,
                uploaded_by="test-user",
                storage_path=f"/tmp/test{i}.pdf"
            )
            for i in range(3)
        ]
        
        for event in events:
            event.event_id = uuid4()
            event.sequence = i
        
        await publisher.publish_all(events)
        
        # All events should be handled
        assert len(projection.handled_events) == 3
        
        # All successes should be recorded
        assert mock_failure_tracker.record_success.call_count == 3


class TestGeneralHandlers:
    """Test general event handlers (non-projection)."""
    
    @pytest.mark.asyncio
    async def test_general_handlers_executed(self, mock_failure_tracker, sample_event):
        """Test that general handlers are executed for events."""
        handler_called = []
        
        async def test_handler(event):
            handler_called.append(event)
        
        publisher = ProjectionEventPublisher(
            projections=[],
            failure_tracker=mock_failure_tracker,
            max_retries=3,
            retry_delay_seconds=0
        )
        publisher.subscribe(test_handler)
        
        await publisher.publish(sample_event)
        
        # Handler should be called
        assert len(handler_called) == 1
        assert handler_called[0] == sample_event
    
    @pytest.mark.asyncio
    async def test_general_handler_failure_does_not_stop_projections(self, mock_failure_tracker, sample_event):
        """Test that general handler failures don't prevent projection execution."""
        async def failing_handler(event):
            raise Exception("Handler failed")
        
        projection = MockProjection()
        publisher = ProjectionEventPublisher(
            projections=[projection],
            failure_tracker=mock_failure_tracker,
            max_retries=3,
            retry_delay_seconds=0
        )
        publisher.subscribe(failing_handler)
        
        # Should not raise exception
        await publisher.publish(sample_event)
        
        # Projection should still execute
        assert len(projection.handled_events) == 1


class TestTypeSpecificHandlers:
    """Test type-specific event handlers."""
    
    @pytest.mark.asyncio
    async def test_type_specific_handler_only_called_for_matching_type(self, mock_failure_tracker, sample_event):
        """Test that type-specific handlers are only called for matching events."""
        handler_called = []
        
        async def type_handler(event):
            handler_called.append(event)
        
        publisher = ProjectionEventPublisher(
            projections=[],
            failure_tracker=mock_failure_tracker,
            max_retries=3,
            retry_delay_seconds=0
        )
        publisher.subscribe_to_event(DocumentUploaded, type_handler)
        
        await publisher.publish(sample_event)
        
        # Handler should be called for DocumentUploaded event
        assert len(handler_called) == 1


class TestProjectionRegistration:
    """Test projection registration."""
    
    def test_register_projection_adds_to_list(self, mock_failure_tracker):
        """Test that registering a projection adds it to the projections list."""
        publisher = ProjectionEventPublisher(
            projections=[],
            failure_tracker=mock_failure_tracker
        )
        
        projection = MockProjection()
        publisher.register_projection(projection)
        
        assert len(publisher._projections) == 1
        assert publisher._projections[0] == projection
    
    def test_can_register_multiple_projections(self, mock_failure_tracker):
        """Test that multiple projections can be registered."""
        publisher = ProjectionEventPublisher(
            projections=[],
            failure_tracker=mock_failure_tracker
        )
        
        proj1 = MockProjection(name="Projection1")
        proj2 = MockProjection(name="Projection2")
        
        publisher.register_projection(proj1)
        publisher.register_projection(proj2)
        
        assert len(publisher._projections) == 2


class TestWithoutFailureTracker:
    """Test publisher behavior without failure tracker."""
    
    @pytest.mark.asyncio
    async def test_works_without_failure_tracker(self, sample_event):
        """Test that publisher works even without failure tracker."""
        projection = MockProjection()
        publisher = ProjectionEventPublisher(
            projections=[projection],
            failure_tracker=None,  # No tracker
            max_retries=3,
            retry_delay_seconds=0
        )
        
        await publisher.publish(sample_event)
        
        # Should still work
        assert len(projection.handled_events) == 1
    
    @pytest.mark.asyncio
    async def test_retries_still_work_without_tracker(self, sample_event):
        """Test that retry logic still works without failure tracker."""
        projection = MockProjection(should_fail=True, fail_count=1)
        publisher = ProjectionEventPublisher(
            projections=[projection],
            failure_tracker=None,
            max_retries=3,
            retry_delay_seconds=0
        )
        
        await publisher.publish(sample_event)
        
        # Should succeed after retry
        assert len(projection.handled_events) == 1
