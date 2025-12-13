"""
Integration tests for projection failure handling.

Tests Event Sourcing best practices:
- Projection failures are tracked and retried
- Exponential backoff prevents overwhelming the system
- Checkpoints enable replay from last known good state
- Health metrics provide observability
- Compensation logic enables manual recovery
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from uuid import uuid4
from unittest.mock import Mock, AsyncMock, patch

from src.domain.events.document_events import DocumentUploaded
from src.infrastructure.projections.failure_tracking import (
    ProjectionFailureTracker,
    RetryableProjectionPublisher
)
from src.infrastructure.projections.base import Projection
from src.application.services.event_publisher import ProjectionEventPublisher


class MockProjection(Projection):
    """Mock projection for testing."""
    
    def __init__(self, name: str = "MockProjection"):
        self.name = name
        self.handled_events = []
        self.should_fail = False
        self.fail_count = 0
        self.max_fails = 0
    
    def handles(self):
        return [DocumentUploaded]
    
    async def handle(self, event):
        if self.should_fail and self.fail_count < self.max_fails:
            self.fail_count += 1
            raise Exception(f"Mock failure #{self.fail_count}")
        self.handled_events.append(event)


@pytest.fixture
async def mock_pool():
    """Mock asyncpg connection pool."""
    pool = AsyncMock()
    conn = AsyncMock()
    pool.acquire.return_value.__aenter__.return_value = conn
    
    # Mock database responses
    conn.fetchrow.return_value = None
    conn.fetchval.return_value = uuid4()
    conn.fetch.return_value = []
    
    return pool


@pytest.fixture
async def failure_tracker(mock_pool):
    """Create failure tracker with mock pool."""
    return ProjectionFailureTracker(mock_pool)


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


class TestProjectionFailureTracking:
    """Test projection failure tracking and retry logic."""
    
    @pytest.mark.asyncio
    async def test_record_failure_creates_new_record(self, failure_tracker, sample_event):
        """Test that first failure creates a new record with retry schedule."""
        projection_name = "TestProjection"
        error = Exception("Database connection failed")
        
        failure_id = await failure_tracker.record_failure(sample_event, projection_name, error)
        
        assert failure_id is not None
        # Verify database insert was called
        pool = failure_tracker._pool
        conn = pool.acquire.return_value.__aenter__.return_value
        assert conn.fetchval.called
    
    @pytest.mark.asyncio
    async def test_record_failure_increments_retry_count(self, failure_tracker, sample_event):
        """Test that subsequent failures increment retry count."""
        projection_name = "TestProjection"
        error = Exception("Database connection failed")
        
        # Mock existing failure
        pool = failure_tracker._pool
        conn = pool.acquire.return_value.__aenter__.return_value
        conn.fetchrow.return_value = {'id': uuid4(), 'retry_count': 2}
        
        failure_id = await failure_tracker.record_failure(sample_event, projection_name, error)
        
        # Verify update was called
        assert conn.execute.called
    
    @pytest.mark.asyncio
    async def test_exponential_backoff_delays(self, failure_tracker):
        """Test that retry delays follow exponential backoff pattern."""
        expected_delays = [1, 2, 4, 8, 16]
        
        for retry_count, expected_delay in enumerate(expected_delays):
            actual_delay = failure_tracker._get_retry_delay(retry_count)
            assert actual_delay == expected_delay
        
        # Test max delay is capped
        assert failure_tracker._get_retry_delay(10) == 16
    
    @pytest.mark.asyncio
    async def test_record_success_updates_checkpoint(self, failure_tracker, sample_event):
        """Test that successful projection updates checkpoint."""
        projection_name = "TestProjection"
        
        await failure_tracker.record_success(sample_event, projection_name)
        
        # Verify checkpoint insert/update was called
        pool = failure_tracker._pool
        conn = pool.acquire.return_value.__aenter__.return_value
        assert conn.execute.called
    
    @pytest.mark.asyncio
    async def test_record_success_resolves_failures(self, failure_tracker, sample_event):
        """Test that successful projection resolves pending failures."""
        projection_name = "TestProjection"
        
        await failure_tracker.record_success(sample_event, projection_name)
        
        # Verify failure resolution update was called
        pool = failure_tracker._pool
        conn = pool.acquire.return_value.__aenter__.return_value
        # Should have called execute at least twice (checkpoint + resolve)
        assert conn.execute.call_count >= 2


class TestProjectionEventPublisher:
    """Test projection event publisher with retry logic."""
    
    @pytest.mark.asyncio
    async def test_successful_projection_no_retry(self, failure_tracker, sample_event):
        """Test that successful projections don't trigger retries."""
        projection = MockProjection()
        publisher = ProjectionEventPublisher(
            projections=[projection],
            failure_tracker=failure_tracker,
            max_retries=3,
            retry_delay_seconds=0  # No delay for testing
        )
        
        await publisher.publish(sample_event)
        
        # Verify event was handled once
        assert len(projection.handled_events) == 1
        assert projection.handled_events[0] == sample_event
    
    @pytest.mark.asyncio
    async def test_transient_failure_retries_successfully(self, failure_tracker, sample_event):
        """Test that transient failures are retried and eventually succeed."""
        projection = MockProjection()
        projection.should_fail = True
        projection.max_fails = 2  # Fail twice, then succeed
        
        publisher = ProjectionEventPublisher(
            projections=[projection],
            failure_tracker=failure_tracker,
            max_retries=3,
            retry_delay_seconds=0  # No delay for testing
        )
        
        await publisher.publish(sample_event)
        
        # Verify event was eventually handled after retries
        assert len(projection.handled_events) == 1
        assert projection.fail_count == 2
    
    @pytest.mark.asyncio
    async def test_permanent_failure_exhausts_retries(self, failure_tracker, sample_event):
        """Test that permanent failures exhaust retries and are tracked."""
        projection = MockProjection()
        projection.should_fail = True
        projection.max_fails = 999  # Always fail
        
        publisher = ProjectionEventPublisher(
            projections=[projection],
            failure_tracker=failure_tracker,
            max_retries=3,
            retry_delay_seconds=0
        )
        
        await publisher.publish(sample_event)
        
        # Verify retries were attempted
        assert projection.fail_count == 3
        assert len(projection.handled_events) == 0
        
        # Verify failure was recorded
        pool = failure_tracker._pool
        conn = pool.acquire.return_value.__aenter__.return_value
        assert conn.fetchval.called  # record_failure was called
    
    @pytest.mark.asyncio
    async def test_multiple_projections_isolated_failures(self, failure_tracker, sample_event):
        """Test that one projection failure doesn't affect others."""
        good_projection = MockProjection(name="GoodProjection")
        bad_projection = MockProjection(name="BadProjection")
        bad_projection.should_fail = True
        bad_projection.max_fails = 999
        
        publisher = ProjectionEventPublisher(
            projections=[good_projection, bad_projection],
            failure_tracker=failure_tracker,
            max_retries=2,
            retry_delay_seconds=0
        )
        
        await publisher.publish(sample_event)
        
        # Good projection should succeed
        assert len(good_projection.handled_events) == 1
        
        # Bad projection should fail
        assert len(bad_projection.handled_events) == 0
        assert bad_projection.fail_count == 2


class TestRetryWorker:
    """Test background retry worker for failed projections."""
    
    @pytest.mark.asyncio
    async def test_retry_worker_processes_due_failures(self, failure_tracker):
        """Test that retry worker processes failures that are due."""
        # Mock failures due for retry
        pool = failure_tracker._pool
        conn = pool.acquire.return_value.__aenter__.return_value
        conn.fetch.return_value = [
            {
                'id': uuid4(),
                'event_id': uuid4(),
                'event_type': 'DocumentUploaded',
                'projection_name': 'TestProjection',
                'retry_count': 1
            }
        ]
        
        publisher = RetryableProjectionPublisher(
            failure_tracker,
            retry_interval_seconds=1
        )
        
        # Start worker
        await publisher.start_retry_worker()
        
        # Give it time to process
        await asyncio.sleep(1.5)
        
        # Stop worker
        await publisher.stop_retry_worker()
        
        # Verify get_failures_for_retry was called
        assert conn.fetch.called
    
    @pytest.mark.asyncio
    async def test_retry_worker_can_be_stopped(self, failure_tracker):
        """Test that retry worker can be gracefully stopped."""
        publisher = RetryableProjectionPublisher(
            failure_tracker,
            retry_interval_seconds=10
        )
        
        await publisher.start_retry_worker()
        assert publisher._running is True
        
        await publisher.stop_retry_worker()
        assert publisher._running is False


class TestHealthMetrics:
    """Test projection health metrics tracking."""
    
    @pytest.mark.asyncio
    async def test_health_metrics_updated_on_success(self, failure_tracker, sample_event):
        """Test that health metrics are updated on successful projection."""
        projection_name = "TestProjection"
        
        await failure_tracker.record_success(sample_event, projection_name)
        
        # Verify health metrics update was called
        pool = failure_tracker._pool
        conn = pool.acquire.return_value.__aenter__.return_value
        # Should update metrics and health status
        assert conn.execute.call_count >= 2
    
    @pytest.mark.asyncio
    async def test_health_metrics_updated_on_failure(self, failure_tracker, sample_event):
        """Test that health metrics are updated on projection failure."""
        projection_name = "TestProjection"
        error = Exception("Test error")
        
        await failure_tracker.record_failure(sample_event, projection_name, error)
        
        # Verify health metrics update was called
        pool = failure_tracker._pool
        conn = pool.acquire.return_value.__aenter__.return_value
        assert conn.execute.called


class TestCheckpointSystem:
    """Test projection checkpoint system."""
    
    @pytest.mark.asyncio
    async def test_checkpoint_tracks_last_processed_event(self, failure_tracker, sample_event):
        """Test that checkpoint tracks the last successfully processed event."""
        projection_name = "TestProjection"
        
        await failure_tracker.record_success(sample_event, projection_name)
        
        checkpoint = await failure_tracker.get_checkpoint(projection_name)
        
        # Verify checkpoint was created
        pool = failure_tracker._pool
        conn = pool.acquire.return_value.__aenter__.return_value
        assert conn.fetchrow.called
    
    @pytest.mark.asyncio
    async def test_checkpoint_enables_replay(self, failure_tracker):
        """Test that checkpoint enables replay from last known good state."""
        projection_name = "TestProjection"
        
        # Mock existing checkpoint
        pool = failure_tracker._pool
        conn = pool.acquire.return_value.__aenter__.return_value
        conn.fetchrow.return_value = {
            'projection_name': projection_name,
            'last_event_id': uuid4(),
            'last_event_type': 'DocumentUploaded',
            'last_event_sequence': 42,
            'events_processed': 100,
            'checkpoint_at': datetime.utcnow()
        }
        
        checkpoint = await failure_tracker.get_checkpoint(projection_name)
        
        assert checkpoint is not None
        assert checkpoint['last_event_sequence'] == 42
        assert checkpoint['events_processed'] == 100
